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
from uuid import uuid4

if sys.platform == "win32":
    import ctypes

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..core.autonomy import schedule_autonomy
from ..core.controller import AssistantController
from ..core.controller_models import AssistantTurn, ControllerResult
from ..core.memory import (
    DEFAULT_USER_NAME,
    MEMORY_SECTIONS,
    AssistantMemory,
    clear_identity_memory,
    clear_memory_section,
    migrate_legacy_profile_identity,
)
from ..core.models import SessionState
from ..storage.memory_store import MemoryStore
from ..storage.profile_store import ProfileStore
from ..voice.models import SpeechEvent, SpeechRequest
from ..voice.retro import estimate_retro_speech_duration_ms, estimate_retro_talk_pulse_ms
from ..voice.service import VoiceService
from .animation_state_machine import AnimationStateMachine
from .bubble_layout import compute_bubble_placement
from .character_widget import CharacterWidget
from .dialogue_presenter import DialoguePresenter
from .execution import apply_execution_result
from .presentation_controller import PresentationController
from .presentation_models import BubbleStyle, ResolvedTurnPresentation
from .presentation_policy import (
    resolve_busy_note_presentation,
    resolve_loading_presentation,
    resolve_turn_presentation,
    resolve_waiting_presentation,
)


class BubbleWindow(QWidget):
    _tail_height = 16
    _tail_half_width = 12

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
        layout.setContentsMargins(14, 10, 14, 22)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(220)
        self.label.setMaximumWidth(420)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.label)
        self._active_style = BubbleStyle()
        self._tail_tip_x = 0
        self.apply_style(BubbleStyle())

    def apply_style(self, style: BubbleStyle) -> None:
        self._active_style = style
        self.label.setStyleSheet(f"color: {style.text_color};")
        self.update()

    def set_tail_tip_x(self, tip_x: int) -> None:
        self._tail_tip_x = tip_x
        self.update()

    def show_text(self, text: str, style: BubbleStyle | None = None) -> None:
        if style is not None:
            self.apply_style(style)
        self.ensurePolished()
        label_width = self._target_label_width(text)
        self.label.setFixedWidth(label_width)
        self.label.setText(text)
        self.label.setFixedHeight(self._target_label_height(text, label_width))
        self.updateGeometry()
        self.adjustSize()
        target_size = self.sizeHint()
        self.setFixedSize(target_size)
        self.update()

    def _target_label_width(self, text: str) -> int:
        min_width = self._active_style.min_width
        max_width = self._active_style.max_width
        length = len(text.strip())
        if length <= 50:
            return min_width
        if length <= 110:
            return min(max_width, min_width + 60)
        if length <= 180:
            return min(max_width, min_width + 120)
        return max_width

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

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        border_color = QColor(self._active_style.border_color)
        background_color = QColor(self._active_style.background_color)
        border_pen = QPen(border_color, 2)
        painter.setPen(border_pen)
        painter.setBrush(background_color)

        body_rect = self.rect().adjusted(1, 1, -1, -self._tail_height - 1)

        tail_base_center = max(
            18 + self._tail_half_width,
            min(self.width() - 18 - self._tail_half_width, self._tail_tip_x or self.width() // 2),
        )
        body_bottom = body_rect.bottom()
        tail_left = tail_base_center - self._tail_half_width
        tail_right = tail_base_center + self._tail_half_width
        tail_tip_y = self.height() - 1

        body_path = QPainterPath()
        body_path.addRoundedRect(body_rect, 12, 12)

        tail_path = QPainterPath()
        tail_path.moveTo(tail_left, body_bottom)
        tail_path.lineTo(tail_base_center, tail_tip_y)
        tail_path.lineTo(tail_right, body_bottom)
        tail_path.closeSubpath()

        painter.drawPath(body_path.united(tail_path))


class ControllerTaskBridge(QObject):
    completed = Signal(object)
    failed = Signal(str)


class VoiceEventBridge(QObject):
    received = Signal(object)


@dataclass
class PendingControllerRequest:
    name: str
    on_result: Callable[[ControllerResult], None]
    progress_mode: str


PENDING_PROGRESS_NONE = "none"
PENDING_PROGRESS_LLM_WAIT = "llm_wait"
PENDING_PROGRESS_STARTUP_LOAD = "startup_load"


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
        self.current_dialogue_category: Optional[str] = None
        self._active_interactions: set[str] = set()
        self._quit_after_dialogue = False
        self._active_voice_utterances: set[str] = set()
        self._last_voice_selection_note = ""
        self._pending_voice_requests: dict[str, SpeechRequest] = {}
        self._started_voice_requests: set[str] = set()
        self.dialogue_presenter = DialoguePresenter()

        self.controller = AssistantController()
        self.profile_store = profile_store or ProfileStore()
        self.memory_store = MemoryStore(app_data_dir=self.profile_store.app_data_dir)
        self.session = self._load_session_state()

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
        self.dialogue_reveal_timer = QTimer(self)
        self.dialogue_reveal_timer.setSingleShot(True)
        self.dialogue_reveal_timer.timeout.connect(self._on_dialogue_reveal_timeout)
        self._controller_task_bridge = ControllerTaskBridge(self)
        self._controller_task_bridge.completed.connect(self._on_controller_task_completed)
        self._controller_task_bridge.failed.connect(self._on_controller_task_failed)
        self._voice_event_bridge = VoiceEventBridge(self)
        self._voice_event_bridge.received.connect(self._on_voice_event)
        self._controller_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="dipsy-llm"
        )
        self.voice_service = VoiceService(event_callback=self._voice_event_bridge.received.emit)

        self.wander_timer = QTimer(self)
        self.wander_timer.timeout.connect(self._wander_tick)

        self.autonomy_timer = QTimer(self)
        self.autonomy_timer.setSingleShot(True)
        self.autonomy_timer.timeout.connect(self._autonomy_timer_tick)

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
        self._arm_autonomy_timer()
        self.keep_on_top_timer.start(2400)

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
            progress_mode=PENDING_PROGRESS_STARTUP_LOAD,
        )

    def _load_session_state(self) -> SessionState:
        profile = self.profile_store.load_profile()
        memory = self.memory_store.load_memory()
        migrated_memory, migrated = migrate_legacy_profile_identity(
            memory,
            user_name=profile.user_name,
            interests=profile.interests,
            has_met_user=profile.has_met_user,
        )
        session = SessionState(profile=profile, memory=migrated_memory)
        if migrated:
            self.memory_store.save_memory(session.memory)
            self.profile_store.save_profile(session.profile)
        return session

    def _persist_profile(self) -> None:
        self.profile_store.save_profile(self.session.profile)

    def _persist_memory(self) -> None:
        if self.session.memory.has_entries():
            self.memory_store.save_memory(self.session.memory)
            return
        self.memory_store.delete_memory()

    def _toggle_voice_enabled(self) -> None:
        voice = self.session.profile.voice.bounded()
        self.session.profile.voice = voice.__class__(
            enabled=not voice.enabled,
            profile=voice.profile,
            voice_id=voice.voice_id,
            rate=voice.rate,
            volume=voice.volume,
            pitch=voice.pitch,
        )
        self._persist_profile()
        if not self.session.profile.voice.enabled:
            self.voice_service.stop(clear_queue=True)

    def _select_voice(self) -> None:
        voices = self.voice_service.list_voices()
        if not voices:
            self._show_message_with_interaction(
                "information",
                "Voice Selection",
                self.voice_service.status_reason or "No Windows speech voices were found.",
            )
            return

        choices = ["Automatic retro voice"] + [voice.name for voice in voices]
        current_id = self.session.profile.voice.voice_id
        current_index = 0
        for index, voice in enumerate(voices, start=1):
            if voice.voice_id == current_id:
                current_index = index
                break

        choice, accepted = self._get_item_with_interaction(
            "Select Retro Voice",
            "Pick a Windows voice. Automatic keeps the best retro match.",
            choices,
            current=current_index,
        )
        if not accepted:
            return

        selected_voice_id = ""
        for voice in voices:
            if voice.name == choice:
                selected_voice_id = voice.voice_id
                break
        voice_settings = self.session.profile.voice.bounded()
        self.session.profile.voice = voice_settings.__class__(
            enabled=voice_settings.enabled,
            profile=voice_settings.profile,
            voice_id=selected_voice_id,
            rate=voice_settings.rate,
            volume=voice_settings.volume,
            pitch=voice_settings.pitch,
        )
        self._persist_profile()

    def _set_voice_rate(self) -> None:
        voice_settings = self.session.profile.voice.bounded()
        rate, accepted = self._get_int_with_interaction(
            "Voice Rate",
            "Set retro speech rate (-10 to 10):",
            voice_settings.rate,
            -10,
            10,
        )
        if not accepted:
            return
        self.session.profile.voice = voice_settings.__class__(
            enabled=voice_settings.enabled,
            profile=voice_settings.profile,
            voice_id=voice_settings.voice_id,
            rate=rate,
            volume=voice_settings.volume,
            pitch=voice_settings.pitch,
        )
        self._persist_profile()

    def _set_voice_volume(self) -> None:
        voice_settings = self.session.profile.voice.bounded()
        volume, accepted = self._get_int_with_interaction(
            "Voice Volume",
            "Set retro speech volume (0 to 100):",
            voice_settings.volume,
            0,
            100,
        )
        if not accepted:
            return
        self.session.profile.voice = voice_settings.__class__(
            enabled=voice_settings.enabled,
            profile=voice_settings.profile,
            voice_id=voice_settings.voice_id,
            rate=voice_settings.rate,
            volume=volume,
            pitch=voice_settings.pitch,
        )
        self._persist_profile()

    def _set_voice_pitch(self) -> None:
        voice_settings = self.session.profile.voice.bounded()
        pitch, accepted = self._get_int_with_interaction(
            "Voice Pitch",
            "Set retro speech pitch (-10 to 10):",
            voice_settings.pitch,
            -10,
            10,
        )
        if not accepted:
            return
        self.session.profile.voice = voice_settings.__class__(
            enabled=voice_settings.enabled,
            profile=voice_settings.profile,
            voice_id=voice_settings.voice_id,
            rate=voice_settings.rate,
            volume=voice_settings.volume,
            pitch=pitch,
        )
        self._persist_profile()

    def _preview_voice(self) -> None:
        preview_voice = self.session.profile.voice.bounded()
        preview_request = SpeechRequest(
            utterance_id=f"preview-{uuid4().hex}",
            text="Observe this tiny burst of retro dolphin theater.",
            category="status",
            settings=preview_voice.__class__(
                enabled=True,
                profile=preview_voice.profile,
                voice_id=preview_voice.voice_id,
                rate=preview_voice.rate,
                volume=preview_voice.volume,
                pitch=preview_voice.pitch,
            ),
        )
        self.voice_service.speak(preview_request)

    def _memory_sections_for_display(self, memory: AssistantMemory) -> list[tuple[str, list[str]]]:
        labels = {
            "long_term_facts": "Long-Term Facts",
            "preferences": "Preferences",
            "execution_history": "Execution History",
            "tool_context": "Tool Context",
        }
        sections: list[tuple[str, list[str]]] = []
        identity_lines: list[str] = []
        if memory.identity.user_name != DEFAULT_USER_NAME:
            identity_lines.append(f"Name: {memory.identity.user_name}")
        if memory.identity.interests:
            identity_lines.append("Interests: " + ", ".join(memory.identity.interest_values()))
        if identity_lines:
            sections.append(("Onboarding", identity_lines))
        for section in MEMORY_SECTIONS:
            values = memory.values_for(section)
            if values:
                sections.append((labels[section], values))
        return sections

    def _apply_presentation(self) -> None:
        self.presentation_controller.set_animation_state(
            self.animation_state_machine.current_state(self._now_ms())
        )
        self.presentation_controller.set_facing(self.animation_state_machine.facing)
        self.presentation_controller.set_dialogue_category(self.current_dialogue_category)
        self.presentation_controller.set_emotion(self.session.emotion)
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
        self._perform_turn(
            result.turn,
            execution_results=self._execution_results_for_result(result),
            schedule_idle=schedule_idle,
        )

    def _debug_log(self, message: str) -> None:
        print(f"[Dipsy] {message}")

    def _apply_session_state(self, next_state: SessionState | None) -> None:
        if next_state is None:
            return
        self.session = next_state

    def _begin_interaction(self, reason: str, *, user_driven: bool = False) -> None:
        self._active_interactions.add(reason)
        self.autonomy_timer.stop()
        if user_driven:
            self._note_user_interaction()

    def _end_interaction(self, reason: str) -> None:
        self._active_interactions.discard(reason)
        if not self._active_interactions:
            self._arm_autonomy_timer()

    def _interaction_active(self) -> bool:
        return bool(self._active_interactions)

    def _assistant_output_active(self) -> bool:
        return (
            self.dialogue_presenter.active_item is not None
            or self.bubble_window.isVisible()
            or bool(self._active_voice_utterances)
            or self.dialogue_reveal_timer.isActive()
            or self.bubble_hide_timer.isActive()
        )

    def _get_text_with_interaction(self, title: str, label: str) -> tuple[str, bool]:
        reason = f"dialog:text:{title}"
        self._begin_interaction(reason, user_driven=True)
        try:
            return QInputDialog.getText(self, title, label)
        finally:
            self._end_interaction(reason)

    def _get_item_with_interaction(
        self,
        title: str,
        label: str,
        items: list[str],
        current: int = 0,
    ) -> tuple[str, bool]:
        reason = f"dialog:item:{title}"
        self._begin_interaction(reason, user_driven=True)
        try:
            return QInputDialog.getItem(self, title, label, items, current, False)
        finally:
            self._end_interaction(reason)

    def _get_int_with_interaction(
        self,
        title: str,
        label: str,
        value: int,
        minimum: int,
        maximum: int,
    ) -> tuple[int, bool]:
        reason = f"dialog:int:{title}"
        self._begin_interaction(reason, user_driven=True)
        try:
            return QInputDialog.getInt(self, title, label, value, minimum, maximum)
        finally:
            self._end_interaction(reason)

    def _show_message_with_interaction(
        self,
        level: str,
        title: str,
        text: str,
        *,
        parent: QWidget | None = None,
        user_driven: bool = True,
    ) -> None:
        reason = f"dialog:message:{title}"
        self._begin_interaction(reason, user_driven=user_driven)
        try:
            if level == "critical":
                QMessageBox.critical(parent or self, title, text)
                return
            QMessageBox.information(parent or self, title, text)
        finally:
            self._end_interaction(reason)

    def _submit_controller_task(
        self,
        label: str,
        task: Callable[[], ControllerResult],
        on_result: Callable[[ControllerResult], None],
        *,
        progress_mode: str = PENDING_PROGRESS_LLM_WAIT,
    ) -> bool:
        if self._closing or self._pending_request is not None:
            return False

        self._request_counter += 1
        self._pending_request = PendingControllerRequest(
            name=label,
            on_result=on_result,
            progress_mode=progress_mode,
        )
        self._begin_interaction("controller_request")
        self._clear_dialogue_state(stop_voice=True)
        self._clear_animation_overlay()
        if progress_mode == PENDING_PROGRESS_LLM_WAIT:
            waiting_cue = resolve_waiting_presentation(emotion=self.session.emotion)
            self._request_animation(waiting_cue.animation_state, duration_ms=1600, force=True)
        elif progress_mode == PENDING_PROGRESS_STARTUP_LOAD:
            loading_cue = resolve_loading_presentation(emotion=self.session.emotion)
            self._request_animation(loading_cue.animation_state, duration_ms=1600, force=True)
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
        self._end_interaction("controller_request")
        self._clear_dialogue_state()
        if pending_request.name == "inactive tick" and result.session_state is not None:
            behavior = result.turn.behavior or result.session_state.last_autonomous_behavior
            result.session_state.record_autonomous_timing(behavior, self._now_ms())
        self._apply_session_state(result.session_state)
        self._debug_log(
            "completed: "
            f"{pending_request.name} -> "
            f"say={bool(result.turn.say)} "
            f"action={getattr(result.turn.action, 'action_id', None)} "
            f"animation={result.turn.animation} "
            f"loop_steps={len(result.loop_steps)} "
            f"loop_stop={result.loop_stop_reason}"
        )

        pending_request.on_result(result)

    def _on_controller_task_failed(self, message: str) -> None:
        if self._closing:
            return

        request_name = (
            self._pending_request.name if self._pending_request is not None else "request"
        )
        self._pending_request = None
        self._end_interaction("controller_request")
        self._clear_dialogue_state(stop_voice=True)
        if request_name.startswith("onboarding"):
            self.onboarding_active = False
        self._debug_log(f"failed: {request_name} -> {message}")
        self._clear_animation_overlay()
        self._sync_presentation_to_motion()
        self._arm_autonomy_timer()
        self._show_message_with_interaction(
            "critical",
            "Dipsy Dolphin",
            f"The local brain failed during {request_name}.\n\n{message}",
            user_driven=False,
        )

    def _show_busy_note(self) -> None:
        busy_cue = resolve_busy_note_presentation(emotion=self.session.emotion)
        self._speak(
            "One thought at a time. I am still working on the last one.",
            cue=busy_cue,
            hold_ms=2600,
        )

    def _perform_turn(
        self,
        turn: AssistantTurn,
        *,
        execution_results=(),
        schedule_idle: bool = False,
    ) -> None:
        cue = resolve_turn_presentation(turn, emotion=self.session.emotion)
        execution_results = tuple(result for result in execution_results if result is not None)
        last_execution_result = execution_results[-1] if execution_results else None
        directive_kinds = [
            result.directive.kind
            for result in execution_results
            if result.directive is not None and result.status == "success"
        ]
        self._debug_log(
            "apply turn: "
            f"say={turn.say!r} "
            f"animation={turn.animation} "
            f"action={getattr(turn.action, 'action_id', None)} "
            f"execution_status={getattr(last_execution_result, 'status', None)} "
            f"directives={directive_kinds or [None]} "
            f"cooldown={turn.cooldown_ms}"
        )
        for execution_result in execution_results:
            apply_execution_result(
                execution_result,
                start_walk=self._start_walk_action,
                request_quit=lambda say=bool(turn.say): self._request_quit_from_execution(
                    defer=say
                ),
            )

        if turn.say:
            self._speak(turn.say, cue=cue)
        elif cue.animation_state not in {"idle", "walk"}:
            self._request_animation(cue.animation_state, duration_ms=1800, force=True)
        else:
            self._sync_presentation_to_motion()

        if schedule_idle:
            self._arm_autonomy_timer()

    def _execution_results_for_result(self, result: ControllerResult):
        loop_execution_results = tuple(
            step.execution_result
            for step in result.loop_steps
            if step.execution_result is not None
        )
        if loop_execution_results:
            return loop_execution_results
        if result.execution_result is not None:
            return (result.execution_result,)
        return ()

    def _on_voice_event(self, event: SpeechEvent) -> None:
        if event.event_type == "voice_selected":
            if event.message:
                self._last_voice_selection_note = event.message
            if event.used_fallback:
                self._debug_log(
                    f"voice fallback: {event.voice_name or event.voice_id} ({event.message or 'closest retro match'})"
                )
            return

        if event.event_type == "started":
            self._active_voice_utterances.add(event.utterance_id)
            self._sync_voice_animation(event.utterance_id, pulse_kind="started")
            return

        if event.event_type == "word":
            self._sync_voice_animation(event.utterance_id, pulse_kind="word")
            return

        if event.event_type in {"finished", "cancelled", "failed"}:
            self._active_voice_utterances.discard(event.utterance_id)
            self._pending_voice_requests.pop(event.utterance_id, None)
            self._started_voice_requests.discard(event.utterance_id)
            if event.event_type == "failed" and event.message:
                self._debug_log(f"voice failed: {event.message}")
            active_item = self.dialogue_presenter.active_item
            if (
                active_item is not None
                and active_item.utterance_id == event.utterance_id
                and not self.dialogue_presenter.has_more_reveal()
                and not self.bubble_hide_timer.isActive()
            ):
                self.bubble_hide_timer.start(250)

    def _sync_voice_animation(self, utterance_id: str, *, pulse_kind: str) -> None:
        active_item = self.dialogue_presenter.active_item
        if active_item is None or active_item.utterance_id != utterance_id:
            return
        duration_ms = estimate_retro_talk_pulse_ms(
            category=active_item.cue.dialogue_category,
            settings=self.session.profile.voice,
            pulse_kind=pulse_kind,
        )
        self._request_animation("talk", duration_ms=duration_ms, force=True)

    def _ensure_active_voice(self) -> None:
        active_item = self.dialogue_presenter.active_item
        if active_item is None or not active_item.utterance_id:
            return
        if active_item.utterance_id in self._started_voice_requests:
            return
        request = self._pending_voice_requests.get(active_item.utterance_id)
        if request is None:
            return
        started = self.voice_service.speak(request)
        if started:
            self._started_voice_requests.add(active_item.utterance_id)

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
        user_name, accepted = self._get_text_with_interaction("Dipsy Dolphin", result.turn.say)
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
        interests_text, accepted = self._get_text_with_interaction("Dipsy Dolphin", result.turn.say)
        if accepted and interests_text:
            parsed = self.controller.parse_interests(interests_text)
            if parsed:
                self.session.interests = parsed

        self.session.mark_profile_configured()
        self._persist_memory()
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

        user_text, accepted = self._get_text_with_interaction(
            "Talk to Dipsy Dolphin", "Say something:"
        )
        if not accepted or not user_text:
            self._sync_presentation_to_motion()
            return

        self._note_user_interaction()
        profile_before = (self.session.user_name, tuple(self.session.interests))
        memory_before = copy.deepcopy(self.session.memory)
        submitted = self._submit_controller_task(
            "chat reply",
            lambda session=copy.deepcopy(self.session): self.controller.handle_user_message(
                user_text, session
            ),
            lambda result: self._handle_chat_result(result, profile_before, memory_before),
        )
        if not submitted:
            self._show_busy_note()

    def _handle_chat_result(
        self,
        result: ControllerResult,
        profile_before: tuple[str, tuple[str, ...]],
        memory_before: AssistantMemory,
    ) -> None:
        profile_after = (self.session.user_name, tuple(self.session.interests))

        if profile_after != profile_before:
            self.session.mark_profile_configured()
            self._persist_memory()

        if self.session.memory != memory_before:
            self._persist_memory()

        self._perform_controller_result(result, schedule_idle=True)

    def _tell_joke(self) -> None:
        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "joke",
            lambda session=copy.deepcopy(self.session): self.controller.handle_user_message(
                "Tell me a joke.", session
            ),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
        )
        if not submitted:
            self._show_busy_note()

    def _random_bit(self) -> None:
        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "do something",
            lambda session=copy.deepcopy(self.session): self.controller.handle_user_message(
                "Do something playful and visible.", session
            ),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
        )
        if not submitted:
            self._show_busy_note()

    def _show_status(self) -> None:
        self._note_user_interaction()
        submitted = self._submit_controller_task(
            "status",
            lambda session=copy.deepcopy(self.session): self.controller.handle_user_message(
                "What's our current status?", session
            ),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
        )
        if not submitted:
            self._show_busy_note()

    def _show_memory(self) -> None:
        sections = self._memory_sections_for_display(self.session.memory)
        if not sections:
            self._show_message_with_interaction(
                "information",
                "Dipsy Memory",
                "Dipsy is not holding onto any saved memory yet.",
            )
            return

        lines: list[str] = []
        for title, values in sections:
            lines.append(f"{title}:")
            lines.extend(f"- {value}" for value in values)
            lines.append("")
        self._show_message_with_interaction("information", "Dipsy Memory", "\n".join(lines).strip())

    def _forget_memory(self) -> None:
        choice, accepted = self._get_item_with_interaction(
            "Forget Memory",
            "What should Dipsy forget?",
            ["All Memory", "Onboarding", "Long-Term Facts", "Preferences"],
            current=0,
        )
        if not accepted:
            return

        if choice == "All Memory":
            self.session.memory = AssistantMemory()
        elif choice == "Onboarding":
            self.session.memory = clear_identity_memory(self.session.memory)
        elif choice == "Long-Term Facts":
            self.session.memory = clear_memory_section(self.session.memory, "long_term_facts")
        elif choice == "Preferences":
            self.session.memory = clear_memory_section(self.session.memory, "preferences")
        self.session.onboarding_complete = self.session.memory.identity.is_configured()
        self._persist_memory()

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
        self.memory_store.delete_memory()
        self._perform_controller_result(result)
        QTimer.singleShot(700, self._start_onboarding)

    def _start_walk_action(self) -> bool:
        if self.dragging or self.onboarding_active:
            return False

        self.walk_active = True
        self._choose_new_target()
        self._sync_presentation_to_motion()
        return True

    def _arm_autonomy_timer(self, delay_ms: Optional[int] = None) -> None:
        if self._closing:
            return
        if self._interaction_active() or self._assistant_output_active():
            self.autonomy_timer.stop()
            return
        interval = delay_ms if delay_ms is not None else self._next_autonomy_delay_ms()
        self.autonomy_timer.start(max(1000, interval))

    def _next_autonomy_delay_ms(self) -> int:
        if not self.session.onboarding_complete or self.onboarding_active:
            return 1500
        decision = schedule_autonomy(self.session, self._now_ms())
        return decision.next_delay_ms

    def _autonomy_blocked(self) -> bool:
        return (
            not self.session.onboarding_complete
            or self.onboarding_active
            or self._interaction_active()
            or self._assistant_output_active()
        )

    def _note_user_interaction(self) -> None:
        self.session.mark_user_interaction(self._now_ms())
        self._arm_autonomy_timer()

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

    def _autonomy_timer_tick(self) -> None:
        if self._autonomy_blocked():
            self._arm_autonomy_timer(1500)
            return

        now_ms = self._now_ms()
        decision = schedule_autonomy(self.session, now_ms)
        if not decision.should_run:
            self._arm_autonomy_timer(decision.next_delay_ms)
            return

        submitted = self._submit_controller_task(
            "inactive tick",
            lambda session=copy.deepcopy(self.session): (
                self.controller.inactivity_turn(
                    session,
                    seconds_since_user_interaction=decision.seconds_since_user_interaction,
                    cooldown_remaining_ms=decision.cooldown_remaining_ms,
                )
            ),
            lambda result: self._perform_controller_result(result, schedule_idle=True),
            progress_mode=PENDING_PROGRESS_NONE,
        )
        if not submitted:
            self._arm_autonomy_timer(1500)

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

    def _clear_dialogue_state(self, *, stop_voice: bool = False) -> None:
        self.dialogue_reveal_timer.stop()
        self.bubble_hide_timer.stop()
        self.dialogue_presenter.clear()
        self._pending_voice_requests.clear()
        self._started_voice_requests.clear()
        self._active_voice_utterances.clear()
        if stop_voice:
            self.voice_service.stop(clear_queue=True)
        self.bubble_window.hide()
        self.current_dialogue_category = None

    def _show_active_dialogue(self) -> None:
        active_item = self.dialogue_presenter.active_item
        if active_item is None:
            self.bubble_window.hide()
            self.current_dialogue_category = None
            self._clear_animation_overlay()
            self._sync_presentation_to_motion()
            return

        cue = active_item.cue
        self.current_dialogue_category = cue.dialogue_category
        active_animation = cue.animation_state
        if active_animation in {"idle", "walk"}:
            active_animation = "talk"
        self._request_animation(
            active_animation,
            duration_ms=self.dialogue_presenter.active_remaining_duration_ms(),
            force=True,
        )
        self.bubble_window.show_text(self.dialogue_presenter.active_text(), cue.bubble_style)
        self.bubble_window.show()
        self.bubble_window.raise_()
        QApplication.processEvents()
        self._position_bubble()
        self._ensure_active_voice()

        if self.dialogue_presenter.has_more_reveal():
            self.dialogue_reveal_timer.start(self.dialogue_presenter.active_chunk_pause_ms())
            self.bubble_hide_timer.stop()
        else:
            self.dialogue_reveal_timer.stop()
            self.bubble_hide_timer.start(self.dialogue_presenter.active_hold_ms())

    def _on_dialogue_reveal_timeout(self) -> None:
        if not self.dialogue_presenter.advance_reveal():
            return
        self._show_active_dialogue()

    def _on_bubble_timeout(self) -> None:
        active_item = self.dialogue_presenter.active_item
        if (
            active_item is not None
            and active_item.utterance_id
            and active_item.utterance_id in self._active_voice_utterances
        ):
            self._request_animation("talk", duration_ms=320, force=True)
            self.bubble_hide_timer.start(250)
            return
        if self.dialogue_presenter.finish_active():
            self._show_active_dialogue()
            return
        self._clear_dialogue_state()
        if self._quit_after_dialogue:
            self._quit_after_dialogue = False
            self._quit()
            return
        self._clear_animation_overlay()
        self._sync_presentation_to_motion()
        self._arm_autonomy_timer()

    def _request_quit_from_execution(self, *, defer: bool) -> bool:
        if defer:
            self._quit_after_dialogue = True
            return True
        self._quit()
        return True

    def _speak(
        self,
        text: str,
        cue: ResolvedTurnPresentation | None = None,
        hold_ms: int | None = None,
    ) -> None:
        if cue is None:
            raise ValueError("Presentation cue is required for speech")
        utterance_id = f"speech-{uuid4().hex}"
        voice_settings = self.session.profile.voice.bounded()
        estimated_voice_hold_ms = (
            estimate_retro_speech_duration_ms(
                text,
                category=cue.dialogue_category,
                settings=voice_settings,
            )
            if voice_settings.enabled and self.voice_service.is_available()
            else 0
        )
        resolved_hold_ms = max(hold_ms or 0, estimated_voice_hold_ms) or None
        self._pending_voice_requests[utterance_id] = SpeechRequest(
            utterance_id=utterance_id,
            text=text,
            category=cue.dialogue_category,
            settings=voice_settings,
        )
        action = self.dialogue_presenter.enqueue(
            text,
            cue,
            hold_override_ms=resolved_hold_ms,
            utterance_id=utterance_id,
        )
        if action == "drop":
            self._pending_voice_requests.pop(utterance_id, None)
            return
        if action in {"start", "replace"}:
            self._show_active_dialogue()

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
        character_center_global_x = self.x() + (self.width() // 2)
        screen_left = screen_geometry.x()
        screen_top = screen_geometry.y()
        screen_right = screen_left + screen_geometry.width()
        screen_bottom = screen_top + screen_geometry.height()
        placement = compute_bubble_placement(
            anchor_global_x=anchor_global_x,
            anchor_global_y=anchor_global_y,
            bubble_width=bubble_width,
            bubble_height=bubble_height,
            screen_left=screen_left,
            screen_top=screen_top,
            screen_right=screen_right,
            screen_bottom=screen_bottom,
            preferred_center_global_x=character_center_global_x,
        )
        self.bubble_window.set_tail_tip_x(placement.tail_tip_x)
        self.bubble_window.move(placement.bubble_x, placement.bubble_y)

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
        self._persist_memory()

        self.dialogue_reveal_timer.stop()
        self.bubble_hide_timer.stop()
        self.wander_timer.stop()
        self.autonomy_timer.stop()
        self.keep_on_top_timer.stop()
        self._pending_request = None
        self.dialogue_presenter.clear()
        self.voice_service.shutdown()
        self.controller.shutdown()
        self._controller_executor.shutdown(wait=False, cancel_futures=True)
        self.bubble_window.close()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self._begin_interaction("drag", user_driven=True)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragging:
            self._note_user_interaction()
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
            self._note_user_interaction()
            self._end_interaction("drag")
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
