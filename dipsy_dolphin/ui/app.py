from concurrent.futures import Future, ThreadPoolExecutor
import copy
import os
from dataclasses import dataclass
import math
import random
import signal
import sys
import time
from typing import Callable, Optional

if sys.platform == "win32":
    import ctypes

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QFont, QFontMetrics, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..core.autonomy import choose_autonomy_plan, seconds_since_user_interaction
from ..core.controller import AssistantController
from ..core.controller_models import AssistantTurn, ControllerResult
from ..core.models import SessionState
from ..storage.profile_store import ProfileStore
from .animation_state_machine import AnimationStateMachine
from .character_widget import CharacterWidget
from .presentation_controller import PresentationController


class BubbleWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        frame = QFrame()
        frame.setObjectName("bubbleFrame")
        frame.setStyleSheet(
            "QFrame#bubbleFrame {"
            "background: #FFF7E6;"
            "border: 2px solid #1B263B;"
            "border-radius: 12px;"
            "}"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 8, 10, 8)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(220)
        self.label.setMaximumWidth(420)
        self.label.setStyleSheet("color: #102226;")
        self.label.setFont(QFont("Segoe UI", 10))
        frame_layout.addWidget(self.label)

        layout.addWidget(frame)

    def show_text(self, text: str) -> None:
        self.ensurePolished()
        label_width = self._target_label_width(text)
        self.label.setFixedWidth(label_width)
        self.label.setText(text)
        self.label.setFixedHeight(self._target_label_height(text, label_width))
        self.updateGeometry()
        self.adjustSize()
        target_size = self.sizeHint()
        self.setFixedSize(target_size)

    def _target_label_width(self, text: str) -> int:
        length = len(text.strip())
        if length <= 50:
            return 240
        if length <= 110:
            return 300
        if length <= 180:
            return 360
        return 420

    def _target_label_height(self, text: str, width: int) -> int:
        metrics = QFontMetrics(self.label.font())
        rect = metrics.boundingRect(
            0,
            0,
            width,
            2000,
            int(Qt.TextFlag.TextWordWrap),
            text or " ",
        )
        return max(metrics.lineSpacing(), rect.height())


class ControllerTaskBridge(QObject):
    completed = Signal(object)
    failed = Signal(str)


@dataclass
class PendingControllerRequest:
    name: str
    on_result: Callable[[ControllerResult], None]
    show_progress: bool


class AssistantApp(QWidget):
    def __init__(self, profile_store: Optional[ProfileStore] = None) -> None:
        super().__init__()
        self.setWindowTitle("Dipsy Dolphin")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.dragging = False
        self.drag_offset = QPoint()
        self.walk_active = False
        self.walk_target_x = 100
        self.walk_target_y = 100
        self.onboarding_active = False
        self._closing = False
        self._runtime_shutdown = False
        self._pending_request: PendingControllerRequest | None = None
        self._request_counter = 0
        self.current_speech_style: Optional[str] = None

        self.controller = AssistantController()
        self.profile_store = profile_store or ProfileStore()
        self.session = SessionState(profile=self.profile_store.load_profile())

        self.animation_state_machine = AnimationStateMachine()
        self.presentation_controller = PresentationController()
        self.character_widget = CharacterWidget(self)
        bounds = self.character_widget.character_bounds()
        self.setFixedSize(bounds.width, bounds.height)
        self.character_widget.setGeometry(0, 0, bounds.width, bounds.height)
        self.character_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.bubble_window = BubbleWindow()
        self.bubble_hide_timer = QTimer(self)
        self.bubble_hide_timer.setSingleShot(True)
        self.bubble_hide_timer.timeout.connect(self._on_bubble_timeout)
        self._llm_progress_timer = QTimer(self)
        self._llm_progress_timer.setSingleShot(True)
        self._llm_progress_timer.timeout.connect(self._on_llm_progress_timeout)
        self._controller_task_bridge = ControllerTaskBridge(self)
        self._controller_task_bridge.completed.connect(self._on_controller_task_completed)
        self._controller_task_bridge.failed.connect(self._on_controller_task_failed)
        self._controller_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="dipsy-llm"
        )

        self.menu = QMenu(self)
        self.menu.setStyleSheet(
            "QMenu { background: #102226; color: #F1FAEE; border: 1px solid #1B263B; }"
            "QMenu::item:selected { background: #F4A261; color: #111111; }"
        )
        self._build_context_menu()

        self.wander_timer = QTimer(self)
        self.wander_timer.timeout.connect(self._wander_tick)

        self.idle_chatter_timer = QTimer(self)
        self.idle_chatter_timer.setSingleShot(True)
        self.idle_chatter_timer.timeout.connect(self._idle_chatter_tick)

        self.keep_on_top_timer = QTimer(self)
        self.keep_on_top_timer.timeout.connect(self._keep_on_top_tick)

        self._position_initially()
        self.walk_target_x = self.x()
        self.walk_target_y = self.y()
        self._apply_presentation()
        self._seed_intro()

        if not self.session.onboarding_complete:
            QTimer.singleShot(900, self._start_onboarding)

        self.wander_timer.start(70)
        self._schedule_idle_chatter()
        self.keep_on_top_timer.start(2400)

    def _build_context_menu(self) -> None:
        talk_action = QAction("Talk to Dipsy", self)
        talk_action.triggered.connect(self._chat_prompt)
        self.menu.addAction(talk_action)

        joke_action = QAction("Tell a Joke", self)
        joke_action.triggered.connect(self._tell_joke)
        self.menu.addAction(joke_action)

        do_something_action = QAction("Do Something", self)
        do_something_action.triggered.connect(self._random_bit)
        self.menu.addAction(do_something_action)

        status_action = QAction("Show Status", self)
        status_action.triggered.connect(self._show_status)
        self.menu.addAction(status_action)

        reset_action = QAction("Reset Session", self)
        reset_action.triggered.connect(self._reset_session)
        self.menu.addAction(reset_action)

        self.menu.addSeparator()

        roam_action = QAction("Roam Somewhere", self)
        roam_action.triggered.connect(self._start_walk_action)
        self.menu.addAction(roam_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        self.menu.addAction(quit_action)

    def _screen_geometry(self):
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _position_initially(self) -> None:
        screen_geometry = self._screen_geometry()
        if screen_geometry is None:
            self.move(100, 100)
            return

        screen_left = screen_geometry.x()
        screen_top = screen_geometry.y()
        screen_right = screen_left + screen_geometry.width()
        screen_bottom = screen_top + screen_geometry.height()
        start_x = max(screen_left + 16, screen_right - self.width() - 64)
        start_y = max(screen_top + 16, screen_bottom - self.height() - 96)
        self.move(start_x, start_y)

    def _now_ms(self) -> int:
        return time.monotonic_ns() // 1_000_000

    def _seed_intro(self) -> None:
        self._submit_controller_task(
            "startup",
            lambda session=copy.deepcopy(self.session): self.controller.startup_turn(session),
            lambda result: self._perform_controller_result(result),
        )

    def _persist_profile(self) -> None:
        self.profile_store.save_profile(self.session.profile)

    def _apply_presentation(self) -> None:
        self.presentation_controller.set_animation_state(
            self.animation_state_machine.current_state(self._now_ms())
        )
        self.presentation_controller.set_facing(self.animation_state_machine.facing)
        self.presentation_controller.set_speech_style(self.current_speech_style)
        self.character_widget.set_presentation(self.presentation_controller.resolve())

    def _request_animation(
        self, state: str, duration_ms: Optional[int] = None, force: bool = False
    ) -> None:
        now_ms = self._now_ms()
        accepted = self.animation_state_machine.request_state(
            state,
            now_ms,
            duration_ms=duration_ms,
            force=force,
        )
        if not accepted and state != "talk":
            self.animation_state_machine.request_state(
                "talk",
                now_ms,
                duration_ms=duration_ms,
                force=True,
            )
        self._apply_presentation()

    def _clear_animation_overlay(self) -> None:
        self.animation_state_machine.clear_active_state(self._now_ms(), force=True)

    def _perform_controller_result(
        self, result: ControllerResult, schedule_idle: bool = False
    ) -> None:
        self._perform_turn(result.turn, schedule_idle=schedule_idle)

    def _debug_log(self, message: str) -> None:
        print(f"[Dipsy] {message}")

    def _apply_session_state(self, next_state: SessionState | None) -> None:
        if next_state is None:
            return
        self.session = next_state

    def _submit_controller_task(
        self,
        label: str,
        task: Callable[[], ControllerResult],
        on_result: Callable[[ControllerResult], None],
        *,
        show_thinking: bool = True,
    ) -> bool:
        if self._closing or self._pending_request is not None:
            return False

        self._request_counter += 1
        self._pending_request = PendingControllerRequest(
            name=label,
            on_result=on_result,
            show_progress=show_thinking,
        )
        self.bubble_hide_timer.stop()
        self._llm_progress_timer.stop()
        self.bubble_window.hide()
        self.current_speech_style = None
        self._clear_animation_overlay()
        if show_thinking:
            self._request_animation("think", duration_ms=1600, force=True)
            self._llm_progress_timer.start(2500)
        self._debug_log(f"request#{self._request_counter} submitted: {label}")

        future = self._controller_executor.submit(task)
        future.add_done_callback(self._forward_controller_future)
        return True

    def _forward_controller_future(self, future: Future[ControllerResult]) -> None:
        try:
            result = future.result()
        except Exception as exc:
            self._controller_task_bridge.failed.emit(str(exc))
            return

        self._controller_task_bridge.completed.emit(result)

    def _on_controller_task_completed(self, result: ControllerResult) -> None:
        if self._closing:
            return

        pending_request = self._pending_request
        if pending_request is None:
            return

        self._pending_request = None
        self._llm_progress_timer.stop()
        self._apply_session_state(result.session_state)
        self._debug_log(
            f"completed: {pending_request.name} -> say={bool(result.turn.say)} action={getattr(result.turn.action, 'action_id', None)} animation={result.turn.animation}"
        )

        pending_request.on_result(result)

    def _on_controller_task_failed(self, message: str) -> None:
        if self._closing:
            return

        request_name = (
            self._pending_request.name if self._pending_request is not None else "request"
        )
        self._pending_request = None
        self._llm_progress_timer.stop()
        self.current_speech_style = None
        if request_name.startswith("onboarding"):
            self.onboarding_active = False
        self._debug_log(f"failed: {request_name} -> {message}")
        self._clear_animation_overlay()
        self._sync_presentation_to_motion()
        QMessageBox.critical(
            self,
            "Dipsy Dolphin",
            f"The local brain failed during {request_name}.\n\n{message}",
        )

    def _on_llm_progress_timeout(self) -> None:
        if self._pending_request is None or not self._pending_request.show_progress:
            return
        self.bubble_window.show_text("Thinking...")
        self._position_bubble()
        self.bubble_window.show()
        self.bubble_window.raise_()

    def _show_busy_note(self) -> None:
        self._speak(
            "One thought at a time. I am still working on the last one.",
            duration_ms=2600,
            style="alert",
        )

    def _perform_turn(self, turn: AssistantTurn, schedule_idle: bool = False) -> None:
        self._debug_log(
            f"apply turn: say={turn.say!r} animation={turn.animation} action={getattr(turn.action, 'action_id', None)} cooldown={turn.cooldown_ms}"
        )
        if turn.action and turn.action.action_id == "roam_somewhere":
            self._start_walk_action()

        if turn.say:
            self._speak(
                turn.say,
                duration_ms=self._duration_for_line(turn.say, turn.speech_style),
                style=turn.speech_style,
            )
        elif turn.animation not in {"idle", "walk"}:
            self._request_animation(turn.animation, duration_ms=1800, force=True)
        else:
            self._sync_presentation_to_motion()

        if schedule_idle:
            self._schedule_idle_chatter(turn.cooldown_ms)

    def _duration_for_line(self, text: str, style: str) -> int:
        words = max(1, len(text.split()))
        base = 3200 + words * 360
        base += min(9000, len(text) * 16)
        if style in {"status", "onboarding"}:
            base += 1200
        return max(3800, min(40000, base))

    def _speech_animation_state(self, style: str) -> str:
        if style == "joke":
            return "laugh"
        if style == "spark":
            return "excited"
        if style in {"question", "onboarding", "alert"}:
            return "surprised"
        return "talk"

    def _start_onboarding(self) -> None:
        if self.session.onboarding_complete or self.onboarding_active:
            return

        if self._pending_request is not None:
            QTimer.singleShot(350, self._start_onboarding)
            return

        self.onboarding_active = True
        submitted = self._submit_controller_task(
            "onboarding name prompt",
            lambda session=copy.deepcopy(self.session): self.controller.onboarding_name_prompt(
                session
            ),
            self._handle_onboarding_name_prompt,
        )
        if not submitted:
            self.onboarding_active = False

    def _handle_onboarding_name_prompt(self, result: ControllerResult) -> None:
        self._perform_controller_result(result)
        user_name, accepted = QInputDialog.getText(self, "Dipsy Dolphin", result.turn.say)
        if accepted and user_name:
            self.session.user_name = user_name.strip() or "friend"

        self._submit_controller_task(
            "onboarding interests prompt",
            lambda session=copy.deepcopy(self.session): self.controller.onboarding_interest_prompt(
                session
            ),
            self._handle_onboarding_interest_prompt,
        )

    def _handle_onboarding_interest_prompt(self, result: ControllerResult) -> None:
        self._perform_controller_result(result)
        interests_text, accepted = QInputDialog.getText(self, "Dipsy Dolphin", result.turn.say)
        if accepted and interests_text:
            parsed = self.controller.parse_interests(interests_text)
            if parsed:
                self.session.interests = parsed

        self.session.mark_profile_configured()
        self._persist_profile()
        self.onboarding_active = False
        self._submit_controller_task(
            "onboarding finish",
            lambda session=copy.deepcopy(self.session): self.controller.finish_onboarding(session),
            lambda finish_result: self._perform_controller_result(
                finish_result, schedule_idle=True
            ),
        )

    def _chat_prompt(self) -> None:
        if self.onboarding_active:
            return
        if self._pending_request is not None:
            self._show_busy_note()
            return

        user_text, accepted = QInputDialog.getText(self, "Talk to Dipsy Dolphin", "Say something:")
        if not accepted or not user_text:
            self._sync_presentation_to_motion()
            return

        self._note_user_interaction()
        profile_before = (self.session.user_name, tuple(self.session.interests))
        submitted = self._submit_controller_task(
            "chat reply",
            lambda session=copy.deepcopy(self.session): self.controller.handle_user_message(
                user_text, session
            ),
            lambda result: self._handle_chat_result(result, profile_before),
        )
        if not submitted:
            self._show_busy_note()

    def _handle_chat_result(
        self, result: ControllerResult, profile_before: tuple[str, tuple[str, ...]]
    ) -> None:
        profile_after = (self.session.user_name, tuple(self.session.interests))

        if profile_after != profile_before:
            self.session.mark_profile_configured()
            self._persist_profile()

        self._perform_controller_result(result, schedule_idle=True)

    def _tell_joke(self) -> None:
        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "joke",
            lambda session=copy.deepcopy(self.session): self.controller.joke_turn(session),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
        )
        if not submitted:
            self._show_busy_note()

    def _random_bit(self) -> None:
        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "do something",
            lambda session=copy.deepcopy(self.session): self.controller.do_something_turn(session),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
        )
        if not submitted:
            self._show_busy_note()

    def _show_status(self) -> None:
        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "status",
            lambda session=copy.deepcopy(self.session): self.controller.status_turn(session),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
        )
        if not submitted:
            self._show_busy_note()

    def _reset_session(self) -> None:
        if self._pending_request is not None:
            return

        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "reset",
            lambda session=copy.deepcopy(self.session): self.controller.reset_turn(session),
            self._handle_reset_result,
        )
        if not submitted:
            self._show_busy_note()

    def _handle_reset_result(self, result: ControllerResult) -> None:
        self.profile_store.delete_profile()
        self._perform_controller_result(result)
        QTimer.singleShot(700, self._start_onboarding)

    def _start_walk_action(self) -> bool:
        if self.dragging or self.onboarding_active:
            return False

        self.walk_active = True
        self._choose_new_target()
        self._sync_presentation_to_motion()
        return True

    def _schedule_idle_chatter(self, cooldown_ms: Optional[int] = None) -> None:
        interval = (
            cooldown_ms if cooldown_ms is not None else max(7000, self.session.autonomy_cooldown_ms)
        )
        self.idle_chatter_timer.start(interval)

    def _note_user_interaction(self) -> None:
        self.session.mark_user_interaction(self._now_ms())

    def _wander_tick(self) -> None:
        if not self.walk_active or self.dragging:
            return

        current_x = self.x()
        current_y = self.y()
        delta_x = self.walk_target_x - current_x
        delta_y = self.walk_target_y - current_y
        distance = math.hypot(delta_x, delta_y)

        if distance < 8:
            self.walk_active = False
            self.walk_target_x = self.x()
            self.walk_target_y = self.y()
            self._sync_presentation_to_motion()
            return

        step = min(7, distance)
        move_x = int(current_x + (delta_x / distance) * step)
        move_y = int(current_y + (delta_y / distance) * step)
        self.move(move_x, move_y)
        self.animation_state_machine.set_base_state("walk", self._now_ms(), delta_x)
        self._apply_presentation()
        self._position_bubble()

    def _idle_chatter_tick(self) -> None:
        if (
            self.session.onboarding_complete
            and not self.dragging
            and not self.walk_active
            and not self.bubble_window.isVisible()
            and self._pending_request is None
        ):
            now_ms = self._now_ms()
            autonomy_plan = choose_autonomy_plan(self.session, now_ms)
            since_user = seconds_since_user_interaction(self.session, now_ms)
            self._submit_controller_task(
                f"autonomous {autonomy_plan.mode}",
                lambda session=copy.deepcopy(self.session), plan=autonomy_plan: (
                    self.controller.autonomous_turn(
                        session,
                        plan=plan,
                        seconds_since_user_interaction=since_user,
                    )
                ),
                lambda result: self._perform_controller_result(result, schedule_idle=True),
                show_thinking=False,
            )
            return
        self._schedule_idle_chatter()

    def _keep_on_top_tick(self) -> None:
        self.raise_()
        if self.bubble_window.isVisible():
            self.bubble_window.raise_()

    def _choose_new_target(self) -> None:
        screen_geometry = self._screen_geometry()
        if screen_geometry is None:
            self.walk_target_x = self.x()
            self.walk_target_y = self.y()
            return

        margin = 12
        min_x = screen_geometry.x() + margin
        min_y = screen_geometry.y() + margin
        max_x = max(min_x, screen_geometry.x() + screen_geometry.width() - self.width() - margin)
        max_y = max(min_y, screen_geometry.y() + screen_geometry.height() - self.height() - 64)
        current_x = self.x()
        current_y = self.y()

        for _ in range(6):
            target_x = random.randint(min_x, max_x)
            target_y = random.randint(min_y, max_y)
            if math.hypot(target_x - current_x, target_y - current_y) >= 120:
                self.walk_target_x = target_x
                self.walk_target_y = target_y
                return

        self.walk_target_x = current_x
        self.walk_target_y = current_y

    def _sync_presentation_to_motion(self) -> None:
        current_x = self.x()
        delta_x = self.walk_target_x - current_x

        if not self.walk_active or self.dragging:
            self.animation_state_machine.set_base_state("idle", self._now_ms(), delta_x)
        else:
            self.animation_state_machine.set_base_state("walk", self._now_ms(), delta_x)
        self._apply_presentation()

    def _on_bubble_timeout(self) -> None:
        self.bubble_window.hide()
        self.current_speech_style = None
        self._clear_animation_overlay()
        self._sync_presentation_to_motion()

    def _speak(self, text: str, duration_ms: int = 5200, style: str = "normal") -> None:
        self.current_speech_style = style
        self._request_animation(
            self._speech_animation_state(style), duration_ms=duration_ms, force=True
        )
        self.bubble_window.show_text(text)
        self.bubble_window.show()
        self.bubble_window.raise_()
        QApplication.processEvents()
        self._position_bubble()
        self.bubble_hide_timer.start(duration_ms)

    def _position_bubble(self) -> None:
        self.bubble_window.ensurePolished()
        self.bubble_window.updateGeometry()
        self.bubble_window.adjustSize()
        self.bubble_window.resize(self.bubble_window.sizeHint())
        bubble_width = self.bubble_window.width()
        bubble_height = self.bubble_window.height()

        screen_geometry = self._screen_geometry()
        if screen_geometry is None:
            return

        anchor_x, anchor_y = self.character_widget.bubble_anchor()
        anchor_global_x = self.x() + anchor_x
        anchor_global_y = self.y() + anchor_y
        screen_left = screen_geometry.x()
        screen_top = screen_geometry.y()
        screen_right = screen_left + screen_geometry.width()
        screen_bottom = screen_top + screen_geometry.height()

        right_x = anchor_global_x + 12
        left_x = anchor_global_x - bubble_width - 12
        if right_x + bubble_width <= screen_right - 8:
            bubble_x = right_x
        else:
            bubble_x = max(screen_left + 8, left_x)

        bubble_y = anchor_global_y - 8
        if bubble_y + bubble_height > screen_bottom - 8:
            bubble_y = max(screen_top + 8, screen_bottom - bubble_height - 8)
        else:
            bubble_y = max(screen_top + 8, bubble_y)

        self.bubble_window.move(bubble_x, bubble_y)

    def _quit(self) -> None:
        self._closing = True
        self._shutdown_runtime()
        self.close()

    def _shutdown_runtime(self) -> None:
        if self._runtime_shutdown:
            return

        self._runtime_shutdown = True
        if self.session.onboarding_complete:
            self._persist_profile()

        self.bubble_hide_timer.stop()
        self._llm_progress_timer.stop()
        self.wander_timer.stop()
        self.idle_chatter_timer.stop()
        self.keep_on_top_timer.stop()
        self._pending_request = None
        self.controller.shutdown()
        self._controller_executor.shutdown(wait=False, cancel_futures=True)
        self.bubble_window.close()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.menu.exec(event.globalPosition().toPoint())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragging:
            current_x = self.x()
            next_position = event.globalPosition().toPoint() - self.drag_offset
            delta_x = next_position.x() - current_x
            self.move(next_position)
            self.animation_state_machine.set_base_state("idle", self._now_ms(), delta_x)
            self._apply_presentation()
            self._position_bubble()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.walk_active = False
            self.walk_target_x = self.x()
            self.walk_target_y = self.y()
            self._sync_presentation_to_motion()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._chat_prompt()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._quit()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._closing = True
        self._shutdown_runtime()
        super().closeEvent(event)


def run() -> None:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    try:
        window = AssistantApp()
    except RuntimeError as exc:
        QMessageBox.critical(None, "Dipsy Dolphin", str(exc))
        return

    window.show()

    if owns_app:
        interrupt_count = 0
        previous_sigint_handler = signal.getsignal(signal.SIGINT)
        console_handler_cleanup: Callable[[], None] | None = None

        def _handle_sigint(_signum, _frame) -> None:
            nonlocal interrupt_count
            interrupt_count += 1

        signal.signal(signal.SIGINT, _handle_sigint)

        if sys.platform == "win32":
            handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
            ctrl_c_events = {0, 1}

            @handler_type
            def _console_ctrl_handler(ctrl_type: int) -> bool:
                nonlocal interrupt_count
                if ctrl_type in ctrl_c_events:
                    interrupt_count += 1
                    return True
                return False

            def _remove_console_ctrl_handler() -> None:
                ctypes.windll.kernel32.SetConsoleCtrlHandler(_console_ctrl_handler, False)

            if ctypes.windll.kernel32.SetConsoleCtrlHandler(_console_ctrl_handler, True):
                console_handler_cleanup = _remove_console_ctrl_handler

        sigint_timer = QTimer()
        sigint_timer.setInterval(100)

        def _poll_for_interrupt() -> None:
            if interrupt_count <= 0:
                return
            if interrupt_count >= 2:
                os._exit(130)
            if not window._closing:
                window._quit()
                app.quit()

        sigint_timer.timeout.connect(_poll_for_interrupt)
        sigint_timer.start()

        try:
            app.exec()
        finally:
            sigint_timer.stop()
            if console_handler_cleanup is not None:
                console_handler_cleanup()
            signal.signal(signal.SIGINT, previous_sigint_handler)
