from __future__ import annotations

import base64
import json
import shutil
import subprocess
import threading
from typing import Callable

from .backend import VoiceBackendStatus
from .models import SpeechEvent, SpeechRequest, VoiceOption
from .retro import build_retro_ssml, choose_voice


LIST_VOICES_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = foreach ($installedVoice in $speaker.GetInstalledVoices()) {
    $voice = $installedVoice.VoiceInfo
    [pscustomobject]@{
        voice_id = [string]$voice.Name
        name = [string]$voice.Name
        culture = [string]$voice.Culture.Name
        gender = [string]$voice.Gender
        age = [string]$voice.Age
        description = [string]$voice.Description
    }
}
$voices | ConvertTo-Json -Compress
"""

SPEAK_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PayloadBase64))
$payload = $json | ConvertFrom-Json
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ([string]$payload.voice_id) {
    $speaker.SelectVoice([string]$payload.voice_id)
}
$speaker.Rate = [int]$payload.rate
$speaker.Volume = [int]$payload.volume
$utteranceId = [string]$payload.utterance_id
$voiceName = [string]$speaker.Voice.Name
function Emit-Event([string]$Type, [string]$Word = '', [int]$Index = 0, [int]$Length = 0, [bool]$Completed = $false, [string]$Message = '') {
    $event = [pscustomobject]@{
        utterance_id = $utteranceId
        event_type = $Type
        word = $Word
        char_index = $Index
        char_length = $Length
        completed = $Completed
        message = $Message
        voice_id = $voiceName
        voice_name = $voiceName
    }
    [Console]::Out.WriteLine(($event | ConvertTo-Json -Compress))
    [Console]::Out.Flush()
}
$speaker.add_SpeakStarted({ param($sender, $eventArgs) Emit-Event 'started' })
$speaker.add_SpeakProgress({ param($sender, $eventArgs) Emit-Event 'word' ([string]$eventArgs.Text) ([int]$eventArgs.CharacterPosition) ([int]$eventArgs.CharacterCount) })
$speaker.add_SpeakCompleted({ param($sender, $eventArgs) Emit-Event 'finished' '' 0 0 (-not [bool]$eventArgs.Cancelled) })
try {
    $speaker.SpeakSsml([string]$payload.ssml)
}
catch {
    Emit-Event 'failed' '' 0 0 $false $_.Exception.Message
    exit 1
}
"""


class WindowsSpeechBackend:
    def __init__(self) -> None:
        self._powershell = _resolve_powershell_executable()
        self._status = self._detect_status()
        self._voices_cache: list[VoiceOption] | None = None
        self._current_process: subprocess.Popen[str] | None = None
        self._process_lock = threading.Lock()
        self._stop_requested = threading.Event()

    @property
    def status(self) -> VoiceBackendStatus:
        return self._status

    def is_available(self) -> bool:
        return self._status.available

    def list_voices(self) -> list[VoiceOption]:
        if not self.is_available():
            return []
        if self._voices_cache is not None:
            return list(self._voices_cache)
        command = self._powershell_command(LIST_VOICES_SCRIPT)
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                creationflags=_creation_flags(),
                timeout=20,
            )
        except Exception:
            return []
        payload = completed.stdout.strip()
        if not payload:
            return []
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if isinstance(loaded, dict):
            items = [loaded]
        elif isinstance(loaded, list):
            items = loaded
        else:
            items = []
        voices: list[VoiceOption] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            voice_id = str(item.get("voice_id", "")).strip()
            name = str(item.get("name", voice_id)).strip()
            if not voice_id or not name:
                continue
            voices.append(
                VoiceOption(
                    voice_id=voice_id,
                    name=name,
                    culture=str(item.get("culture", "")).strip(),
                    gender=str(item.get("gender", "")).strip(),
                    age=str(item.get("age", "")).strip(),
                    description=str(item.get("description", "")).strip(),
                )
            )
        self._voices_cache = voices
        return list(voices)

    def speak(self, request: SpeechRequest, emit: Callable[[SpeechEvent], None]) -> None:
        if not self.is_available():
            emit(
                SpeechEvent(
                    utterance_id=request.utterance_id,
                    event_type="failed",
                    message=self.status.reason or "Windows speech backend unavailable",
                )
            )
            return

        self._stop_requested.clear()
        selection = choose_voice(
            self.list_voices(),
            requested_id=request.settings.voice_id,
            profile=request.settings.profile,
        )
        if selection.option is None:
            emit(
                SpeechEvent(
                    utterance_id=request.utterance_id,
                    event_type="failed",
                    message="No Windows speech voices were found",
                )
            )
            return

        emit(
            SpeechEvent(
                utterance_id=request.utterance_id,
                event_type="voice_selected",
                message=selection.reason,
                voice_id=selection.option.voice_id,
                voice_name=selection.option.name,
                used_fallback=selection.used_fallback,
            )
        )

        payload = {
            "utterance_id": request.utterance_id,
            "voice_id": selection.option.voice_id,
            "rate": request.settings.bounded().rate,
            "volume": request.settings.bounded().volume,
            "ssml": build_retro_ssml(
                request.text,
                category=request.category,
                settings=request.settings,
            ),
        }
        command = self._powershell_command(
            _speak_script(_encode_payload(payload)),
        )

        saw_terminal_event = False
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=_creation_flags(),
        )
        with self._process_lock:
            self._current_process = process
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    event = _parse_event_line(line, selection.option, selection.used_fallback)
                    if event is None:
                        continue
                    if event.event_type in {"finished", "cancelled", "failed"}:
                        saw_terminal_event = True
                    emit(event)

            return_code = process.wait()
            stderr_output = ""
            if process.stderr is not None:
                stderr_output = process.stderr.read().strip()
            if self._stop_requested.is_set() and not saw_terminal_event:
                emit(
                    SpeechEvent(
                        utterance_id=request.utterance_id,
                        event_type="cancelled",
                        voice_id=selection.option.voice_id,
                        voice_name=selection.option.name,
                        used_fallback=selection.used_fallback,
                    )
                )
            elif return_code != 0 and not saw_terminal_event:
                emit(
                    SpeechEvent(
                        utterance_id=request.utterance_id,
                        event_type="failed",
                        message=stderr_output or "Windows speech process failed",
                        voice_id=selection.option.voice_id,
                        voice_name=selection.option.name,
                        used_fallback=selection.used_fallback,
                    )
                )
            elif not saw_terminal_event:
                emit(
                    SpeechEvent(
                        utterance_id=request.utterance_id,
                        event_type="finished",
                        completed=True,
                        voice_id=selection.option.voice_id,
                        voice_name=selection.option.name,
                        used_fallback=selection.used_fallback,
                    )
                )
        finally:
            with self._process_lock:
                self._current_process = None
            self._stop_requested.clear()

    def stop(self) -> None:
        self._stop_requested.set()
        with self._process_lock:
            process = self._current_process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()

    def shutdown(self) -> None:
        self.stop()

    def _detect_status(self) -> VoiceBackendStatus:
        if self._powershell is None:
            return VoiceBackendStatus(False, "Windows PowerShell was not found")
        return VoiceBackendStatus(True)

    def _powershell_command(self, script: str) -> list[str]:
        if self._powershell is None:
            raise RuntimeError("Windows PowerShell is unavailable")
        return [
            self._powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            _encode_script(script),
        ]


def _resolve_powershell_executable() -> str | None:
    for candidate in ("powershell.exe", "powershell"):
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved
    return None


def _encode_script(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _encode_payload(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _speak_script(payload_base64: str) -> str:
    return f"$PayloadBase64 = '{payload_base64}'\n{SPEAK_SCRIPT}"


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _parse_event_line(
    line: str,
    option: VoiceOption,
    used_fallback: bool,
) -> SpeechEvent | None:
    cleaned = line.strip()
    if not cleaned:
        return None
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return SpeechEvent(
        utterance_id=str(payload.get("utterance_id", "")).strip(),
        event_type=str(payload.get("event_type", "")).strip().lower(),
        word=str(payload.get("word", "")).strip(),
        char_index=_coerce_int(payload.get("char_index", 0)),
        char_length=_coerce_int(payload.get("char_length", 0)),
        completed=bool(payload.get("completed", False)),
        message=str(payload.get("message", "")).strip(),
        voice_id=option.voice_id,
        voice_name=option.name,
        used_fallback=used_fallback,
    )


def _coerce_int(value: object) -> int:
    if not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
