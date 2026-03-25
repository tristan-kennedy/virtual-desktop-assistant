import json
import subprocess

from dipsy_dolphin.voice.models import SpeechRequest, VoiceOption
from dipsy_dolphin.voice.windows_speech_backend import WindowsSpeechBackend


class _FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)

    def read(self) -> str:
        return ""


class _FakeProcess:
    def __init__(self, lines: list[str], return_code: int = 0) -> None:
        self.stdout = _FakeStream(lines)
        self.stderr = _FakeStream([])
        self._return_code = return_code
        self._terminated = False

    def wait(self) -> int:
        return self._return_code

    def poll(self):
        return None if not self._terminated else self._return_code

    def terminate(self) -> None:
        self._terminated = True


def test_windows_speech_backend_lists_installed_voices(monkeypatch) -> None:
    monkeypatch.setattr(
        "dipsy_dolphin.voice.windows_speech_backend._resolve_powershell_executable",
        lambda: "powershell.exe",
    )

    def _fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "voice_id": "Sydney",
                        "name": "Sydney",
                        "culture": "en-US",
                        "gender": "Male",
                        "age": "Adult",
                        "description": "Classic retro voice",
                    }
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    backend = WindowsSpeechBackend()
    voices = backend.list_voices()

    assert voices == [
        VoiceOption(
            voice_id="Sydney",
            name="Sydney",
            culture="en-US",
            gender="Male",
            age="Adult",
            description="Classic retro voice",
        )
    ]


def test_windows_speech_backend_emits_voice_selection_and_progress(monkeypatch) -> None:
    monkeypatch.setattr(
        "dipsy_dolphin.voice.windows_speech_backend._resolve_powershell_executable",
        lambda: "powershell.exe",
    )
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda *args, **kwargs: _FakeProcess(
            [
                json.dumps({"utterance_id": "voice-1", "event_type": "started"}) + "\n",
                json.dumps(
                    {
                        "utterance_id": "voice-1",
                        "event_type": "word",
                        "word": "Hello",
                        "char_index": 0,
                        "char_length": 5,
                    }
                )
                + "\n",
                json.dumps({"utterance_id": "voice-1", "event_type": "finished", "completed": True})
                + "\n",
            ]
        ),
    )

    backend = WindowsSpeechBackend()
    backend._voices_cache = [VoiceOption(voice_id="Sydney", name="Sydney", gender="Male")]
    events = []

    backend.speak(SpeechRequest(utterance_id="voice-1", text="Hello there"), events.append)

    assert events[0].event_type == "voice_selected"
    assert events[0].voice_name == "Sydney"
    assert [event.event_type for event in events[1:]] == ["started", "word", "finished"]
