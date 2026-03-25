from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from .backend import VoiceBackend
from .models import SpeechEvent, SpeechRequest, VoiceOption
from .windows_speech_backend import WindowsSpeechBackend


class VoiceService:
    def __init__(
        self,
        backend: VoiceBackend | None = None,
        *,
        event_callback: Callable[[SpeechEvent], None] | None = None,
    ) -> None:
        self.backend = backend or WindowsSpeechBackend()
        self._event_callback = event_callback
        self._command_queue: queue.Queue[tuple[str, object | None]] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._worker_started = False
        self._worker_lock = threading.Lock()
        self._shutdown = False

    def is_available(self) -> bool:
        return self.backend.is_available()

    @property
    def status_reason(self) -> str:
        return self.backend.status.reason

    def list_voices(self) -> list[VoiceOption]:
        return self.backend.list_voices()

    def speak(self, request: SpeechRequest) -> bool:
        if self._shutdown or not request.text.strip() or not request.settings.enabled:
            return False
        if not self.is_available():
            self._emit(
                SpeechEvent(
                    utterance_id=request.utterance_id,
                    event_type="failed",
                    message=self.status_reason or "Voice backend unavailable",
                )
            )
            return False
        self._ensure_worker_started()
        self.stop(clear_queue=True)
        self._command_queue.put(("speak", request))
        return True

    def stop(self, *, clear_queue: bool = True) -> None:
        if clear_queue:
            while True:
                try:
                    self._command_queue.get_nowait()
                except queue.Empty:
                    break
        self.backend.stop()

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.stop(clear_queue=True)
        if self._worker_started:
            self._command_queue.put(("shutdown", None))
            if self._worker_thread is not None:
                self._worker_thread.join(timeout=2)
        self.backend.shutdown()

    def _ensure_worker_started(self) -> None:
        with self._worker_lock:
            if self._worker_started:
                return
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="dipsy-voice",
                daemon=True,
            )
            self._worker_thread.start()
            self._worker_started = True

    def _worker_loop(self) -> None:
        while True:
            command, payload = self._command_queue.get()
            if command == "shutdown":
                return
            if command != "speak" or not isinstance(payload, SpeechRequest):
                continue
            self.backend.speak(payload, self._emit)

    def _emit(self, event: SpeechEvent) -> None:
        if self._event_callback is None:
            return
        self._event_callback(event)
