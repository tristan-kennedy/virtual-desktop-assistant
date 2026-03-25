import threading

from dipsy_dolphin.voice.backend import VoiceBackendStatus
from dipsy_dolphin.voice.models import SpeechEvent, SpeechRequest, VoiceOption
from dipsy_dolphin.voice.service import VoiceService


class ImmediateBackend:
    status = VoiceBackendStatus(True)

    def __init__(self) -> None:
        self.finished = threading.Event()
        self.stop_calls = 0

    def is_available(self) -> bool:
        return True

    def list_voices(self) -> list[VoiceOption]:
        return [VoiceOption(voice_id="Sydney", name="Sydney")]

    def speak(self, request: SpeechRequest, emit) -> None:
        emit(SpeechEvent(utterance_id=request.utterance_id, event_type="started"))
        emit(SpeechEvent(utterance_id=request.utterance_id, event_type="finished", completed=True))
        self.finished.set()

    def stop(self) -> None:
        self.stop_calls += 1

    def shutdown(self) -> None:
        return None


class UnavailableBackend:
    status = VoiceBackendStatus(False, "No retro Windows voice runtime")

    def is_available(self) -> bool:
        return False

    def list_voices(self) -> list[VoiceOption]:
        return []

    def speak(self, request: SpeechRequest, emit) -> None:
        raise AssertionError("speak should not be called when unavailable")

    def stop(self) -> None:
        return None

    def shutdown(self) -> None:
        return None


def test_voice_service_dispatches_events_from_backend() -> None:
    backend = ImmediateBackend()
    events: list[SpeechEvent] = []
    service = VoiceService(backend=backend, event_callback=events.append)

    started = service.speak(SpeechRequest(utterance_id="voice-1", text="Hello there"))

    assert started is True
    assert backend.finished.wait(1)
    assert [event.event_type for event in events] == ["started", "finished"]

    service.shutdown()


def test_voice_service_emits_failure_when_backend_unavailable() -> None:
    events: list[SpeechEvent] = []
    service = VoiceService(backend=UnavailableBackend(), event_callback=events.append)

    started = service.speak(SpeechRequest(utterance_id="voice-2", text="Hello there"))

    assert started is False
    assert len(events) == 1
    assert events[0].event_type == "failed"
    assert "retro Windows voice runtime" in events[0].message
