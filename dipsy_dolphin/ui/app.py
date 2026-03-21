import math
import random
import sys
from typing import Optional

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QInputDialog,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from ..core.brain import AssistantBrain
from ..core.models import SessionState
from ..storage.profile_store import ProfileStore
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
        self.label.setFixedWidth(280)
        self.label.setStyleSheet("color: #102226;")
        self.label.setFont(QFont("Segoe UI", 10))
        frame_layout.addWidget(self.label)

        layout.addWidget(frame)

    def show_text(self, text: str) -> None:
        self.label.setText(text)
        self.label.adjustSize()
        self.adjustSize()


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
        self.wandering_enabled = True
        self.walk_target_x = 100
        self.walk_target_y = 100
        self.onboarding_active = False

        self.brain = AssistantBrain()
        self.profile_store = profile_store or ProfileStore()
        self.session = SessionState(profile=self.profile_store.load_profile())

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

        self._apply_presentation()
        self._position_initially()
        self._choose_new_target()
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

        self.toggle_wandering_action = QAction("Pause Walking", self)
        self.toggle_wandering_action.triggered.connect(self._toggle_wandering)
        self.menu.addAction(self.toggle_wandering_action)

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

    def _seed_intro(self) -> None:
        style = "status" if self.session.onboarding_complete else "onboarding"
        self._speak(self.brain.startup_line(self.session), duration_ms=7000, style=style)

    def _persist_profile(self) -> None:
        self.profile_store.save_profile(self.session.profile)

    def _apply_presentation(self) -> None:
        self.character_widget.set_presentation(self.presentation_controller.resolve())

    def _start_onboarding(self) -> None:
        if self.session.onboarding_complete or self.onboarding_active:
            return

        self.onboarding_active = True
        name_prompt = self.brain.onboarding_name_prompt()
        self._speak(name_prompt, duration_ms=5000, style="onboarding")
        self.presentation_controller.set_thinking()
        self._apply_presentation()
        user_name, accepted = QInputDialog.getText(self, "Dipsy Dolphin", name_prompt)
        if accepted and user_name:
            self.session.user_name = user_name.strip() or "friend"

        interest_prompt = self.brain.onboarding_interest_prompt(self.session.user_name)
        self._speak(interest_prompt, duration_ms=6500, style="onboarding")
        self.presentation_controller.set_thinking()
        self._apply_presentation()
        interests_text, accepted = QInputDialog.getText(self, "Dipsy Dolphin", interest_prompt)
        if accepted and interests_text:
            parsed = self.brain.parse_interests(interests_text)
            if parsed:
                self.session.interests = parsed

        self.session.profile.has_met_user = True
        self.session.onboarding_complete = True
        self._persist_profile()
        self.onboarding_active = False
        self._speak(self.brain.finish_onboarding(self.session), duration_ms=9000, style="normal")

    def _chat_prompt(self) -> None:
        if self.onboarding_active:
            return

        self.presentation_controller.set_thinking()
        self._apply_presentation()
        user_text, accepted = QInputDialog.getText(self, "Talk to Dipsy Dolphin", "Say something:")
        if not accepted or not user_text:
            self._sync_presentation_to_motion()
            return

        profile_before = (self.session.user_name, tuple(self.session.interests))
        reply = self.brain.handle_user_message(user_text, self.session)
        profile_after = (self.session.user_name, tuple(self.session.interests))

        if profile_after != profile_before:
            self.session.profile.has_met_user = True
            self.session.onboarding_complete = self.session.profile.is_configured()
            self._persist_profile()

        self._speak(
            reply, duration_ms=7000, style=self._speech_style_for_topic(self.session.last_topic)
        )
        self._schedule_idle_chatter(cooldown_ms=15000)

    def _tell_joke(self) -> None:
        self._speak(self.brain.tell_joke(self.session), duration_ms=6500, style="joke")

    def _random_bit(self) -> None:
        line = self.brain.random_autonomous_line(self.session)
        self._speak(
            line, duration_ms=7000, style=self._speech_style_for_topic(self.session.last_topic)
        )

    def _show_status(self) -> None:
        self._speak(self.brain.status_line(self.session), duration_ms=7000, style="status")

    def _reset_session(self) -> None:
        self.brain.reset_state(self.session)
        self.profile_store.delete_profile()
        self._speak(
            "Session reset. Let us do the dramatic intro again.", duration_ms=5000, style="alert"
        )
        QTimer.singleShot(700, self._start_onboarding)

    def _toggle_wandering(self) -> None:
        self.wandering_enabled = not self.wandering_enabled
        self.toggle_wandering_action.setText(
            "Pause Walking" if self.wandering_enabled else "Resume Walking"
        )

        if self.wandering_enabled:
            self._choose_new_target()
            self._speak("Swim mode back on. I am roaming again.", duration_ms=4000, style="normal")
        else:
            self._sync_presentation_to_motion()
            self._speak("Floating in place. Drag me anywhere.", duration_ms=3500, style="normal")

    def _schedule_idle_chatter(self, cooldown_ms: Optional[int] = None) -> None:
        interval = cooldown_ms if cooldown_ms is not None else random.randint(7000, 13000)
        self.idle_chatter_timer.start(interval)

    def _wander_tick(self) -> None:
        if not self.wandering_enabled or self.dragging:
            return

        current_x = self.x()
        current_y = self.y()
        delta_x = self.walk_target_x - current_x
        delta_y = self.walk_target_y - current_y
        distance = math.hypot(delta_x, delta_y)

        if distance < 8:
            self._choose_new_target()
            self.presentation_controller.set_idle(delta_x)
            self._apply_presentation()
            if self.session.onboarding_complete and random.random() < 0.1:
                line = self.brain.random_autonomous_line(self.session)
                self._speak(
                    line,
                    duration_ms=5200,
                    style=self._speech_style_for_topic(self.session.last_topic),
                )
            return

        step = min(7, distance)
        move_x = int(current_x + (delta_x / distance) * step)
        move_y = int(current_y + (delta_y / distance) * step)
        self.move(move_x, move_y)
        self.presentation_controller.set_walking(delta_x)
        self._apply_presentation()
        self._position_bubble()

    def _idle_chatter_tick(self) -> None:
        if self.session.onboarding_complete and not self.dragging and random.random() < 0.28:
            line = self.brain.random_autonomous_line(self.session)
            self._speak(
                line, duration_ms=5200, style=self._speech_style_for_topic(self.session.last_topic)
            )
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
        self.walk_target_x = random.randint(min_x, max_x)
        self.walk_target_y = random.randint(min_y, max_y)

    def _speech_style_for_topic(self, topic: str) -> str:
        if topic == "joke":
            return "joke"
        if topic == "question":
            return "question"
        if topic == "doodle":
            return "spark"
        return "normal"

    def _sync_presentation_to_motion(self) -> None:
        current_x = self.x()
        current_y = self.y()
        delta_x = self.walk_target_x - current_x
        delta_y = self.walk_target_y - current_y
        distance = math.hypot(delta_x, delta_y)

        if not self.wandering_enabled or self.dragging or distance < 8:
            self.presentation_controller.set_idle(delta_x)
        else:
            self.presentation_controller.set_walking(delta_x)
        self._apply_presentation()

    def _on_bubble_timeout(self) -> None:
        self.bubble_window.hide()
        self.presentation_controller.stop_speech()
        self._sync_presentation_to_motion()

    def _speak(self, text: str, duration_ms: int = 5200, style: str = "normal") -> None:
        self.presentation_controller.start_speech(style)
        self._apply_presentation()
        self.bubble_window.show_text(text)
        self._position_bubble()
        self.bubble_window.show()
        self.bubble_window.raise_()
        self.bubble_hide_timer.start(duration_ms)

    def _position_bubble(self) -> None:
        self.bubble_window.adjustSize()
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
        if self.session.onboarding_complete:
            self._persist_profile()

        self.bubble_hide_timer.stop()
        self.wander_timer.stop()
        self.idle_chatter_timer.stop()
        self.keep_on_top_timer.stop()
        self.bubble_window.close()
        self.close()

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
            self.presentation_controller.set_idle(delta_x)
            self._apply_presentation()
            self._position_bubble()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            if self.wandering_enabled:
                self._choose_new_target()
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
        if self.session.onboarding_complete:
            self._persist_profile()
        self.bubble_window.close()
        super().closeEvent(event)


def run() -> None:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    window = AssistantApp()
    window.show()

    if owns_app:
        app.exec()
