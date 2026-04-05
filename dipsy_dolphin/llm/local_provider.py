from __future__ import annotations

import atexit
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import ResolvedModelBundle
from .response_parser import extract_json_object
from .runtime_catalog import select_runtime_bundle


@dataclass
class LocalProviderStatus:
    available: bool
    reason: str = ""


@dataclass(frozen=True)
class GenerationSettings:
    temperature: float = 0.35
    top_p: float = 0.85
    max_tokens: int = 360


class LocalLlamaProvider:
    def __init__(self, resolved_bundle: ResolvedModelBundle | None) -> None:
        self.resolved_bundle = resolved_bundle
        self.runtime_bundle = select_runtime_bundle()
        self._server_process: subprocess.Popen[str] | None = None
        self._server_port: int | None = None
        self._server_executable: Path | None = None
        self._status = self._detect_status()
        atexit.register(self.shutdown)

    def is_available(self) -> bool:
        return self._status.available

    @property
    def status(self) -> LocalProviderStatus:
        return self._status

    def _debug_log(self, message: str) -> None:
        print(f"[LLM] {message}")

    def shutdown(self) -> None:
        if self._server_process is None:
            self._server_port = None
            return
        if self._server_process.poll() is None:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
        self._server_process = None
        self._server_port = None

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        if not self.is_available():
            raise RuntimeError(self._status.reason or "Local model is unavailable")

        self._ensure_server_running()
        event_name, user_preview = _prompt_details(user_prompt)
        self._debug_log(f"prompt event={event_name} user={user_preview}")

        attempts = [
            (
                system_prompt,
                user_prompt,
                GenerationSettings(temperature=0.35, top_p=0.85, max_tokens=360),
            ),
            (
                system_prompt
                + "\n\nReturn one valid JSON object only. Do not use markdown, commentary, or <think> tags. Ensure required fields are present.",
                user_prompt,
                GenerationSettings(temperature=0.2, top_p=0.75, max_tokens=420),
            ),
        ]

        last_error: Exception | None = None
        for attempt_number, (attempt_system_prompt, attempt_user_prompt, settings) in enumerate(
            attempts, start=1
        ):
            try:
                return self._generate_once(
                    event_name=event_name,
                    attempt_number=attempt_number,
                    system_prompt=attempt_system_prompt,
                    user_prompt=attempt_user_prompt,
                    settings=settings,
                )
            except Exception as exc:
                self._debug_log(f"response event={event_name} attempt={attempt_number} error={exc}")
                last_error = exc

        if last_error is not None:
            raise RuntimeError(
                f"Local model could not produce valid structured output: {last_error}"
            )
        raise RuntimeError("Local model could not produce valid structured output")

    def _generate_once(
        self,
        *,
        event_name: str,
        attempt_number: int,
        system_prompt: str,
        user_prompt: str,
        settings: GenerationSettings,
    ) -> dict[str, object]:
        if self._server_port is None:
            raise RuntimeError("Local llama.cpp server is not running")

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_object"},
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "max_tokens": settings.max_tokens,
            "seed": 7,
        }
        request = urllib.request.Request(
            url=f"http://127.0.0.1:{self._server_port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Local llama.cpp server request failed: {exc}") from exc

        raw_message = body["choices"][0]["message"]
        self._debug_log(
            f"response event={event_name} attempt={attempt_number} body={raw_message!r}"
        )

        content = raw_message["content"]
        if isinstance(content, str):
            return extract_json_object(content)
        if isinstance(content, dict):
            return content
        raise RuntimeError("Local model returned an unexpected payload")

    def _detect_status(self) -> LocalProviderStatus:
        if self.resolved_bundle is None:
            return LocalProviderStatus(False, "No bundled local model was found")

        if not self.resolved_bundle.model_path.exists():
            return LocalProviderStatus(False, "Configured local model file does not exist")

        server_executable = self._discover_server_executable()
        if server_executable is None:
            return LocalProviderStatus(
                False,
                "The bundled llama.cpp runtime was not found. Run `uv run python -m scripts.windows_build model-bundle` to download both the model and runtime.",
            )

        self._server_executable = server_executable
        return LocalProviderStatus(True)

    def _ensure_server_running(self) -> None:
        if self._server_process is not None and self._server_process.poll() is None:
            return

        bundle = self.resolved_bundle
        server_executable = self._server_executable
        if bundle is None or server_executable is None:
            raise RuntimeError("Local runtime is not configured")

        port = _free_local_port()
        runtime_root = server_executable.parent
        env = os.environ.copy()
        env["PATH"] = (
            os.pathsep.join(_runtime_dll_dirs(runtime_root)) + os.pathsep + env.get("PATH", "")
        )
        creationflags = 0
        if os.name == "nt":
            creationflags |= subprocess.CREATE_NO_WINDOW
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        command = [
            str(server_executable),
            "-m",
            str(bundle.model_path),
            "-c",
            str(bundle.bundle.n_ctx),
            "-ngl",
            str(bundle.bundle.n_gpu_layers),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--jinja",
            "--no-webui",
        ]
        self._server_process = subprocess.Popen(
            command,
            cwd=runtime_root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            close_fds=True,
            creationflags=creationflags,
        )
        self._server_port = port
        self._wait_for_server_ready(port)

    def _wait_for_server_ready(self, port: int) -> None:
        deadline = time.time() + 120
        while time.time() < deadline:
            if self._server_process is None:
                break
            if self._server_process.poll() is not None:
                raise RuntimeError("Bundled llama.cpp server exited during startup")
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=2
                ) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("Bundled llama.cpp server did not become ready in time")

    def _discover_server_executable(self) -> Path | None:
        direct_path = os.environ.get("DIPSY_LLAMA_SERVER_EXE", "").strip()
        if direct_path:
            candidate = Path(direct_path).resolve(strict=False)
            if candidate.exists():
                return candidate

        for root in _candidate_runtime_roots():
            for candidate in root.rglob(self.runtime_bundle.server_executable):
                if candidate.exists():
                    return candidate
        return None


def _candidate_runtime_roots() -> list[Path]:
    roots: list[Path] = []
    runtime_bundle = select_runtime_bundle()

    env_dir = os.environ.get("DIPSY_RUNTIME_DIR", "").strip()
    if env_dir:
        roots.append(Path(env_dir))

    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent / "runtime" / runtime_bundle.runtime_id)
        roots.append(Path(sys.executable).resolve().parent / "runtime")

    package_root = Path(__file__).resolve().parents[2]
    roots.append(package_root / ".artifacts" / "windows" / "llama-runtime" / runtime_bundle.runtime_id)
    roots.append(package_root / ".artifacts" / "windows" / "llama-runtime")
    roots.append(package_root / "runtime")

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved_root = root.resolve(strict=False)
        if resolved_root in seen:
            continue
        seen.add(resolved_root)
        unique_roots.append(resolved_root)
    return unique_roots


def _runtime_dll_dirs(runtime_root: Path) -> list[str]:
    directories: list[str] = []
    seen: set[Path] = set()
    for dll_path in runtime_root.rglob("*.dll"):
        parent = dll_path.parent.resolve(strict=False)
        if parent in seen:
            continue
        seen.add(parent)
        directories.append(str(parent))
    directories.insert(0, str(runtime_root))
    return directories


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _prompt_details(user_prompt: str) -> tuple[str, str]:
    try:
        payload = json.loads(user_prompt)
    except json.JSONDecodeError:
        return ("unknown", "")

    event_name = str(payload.get("event", "unknown"))
    user_text = str(payload.get("user_text", "")).strip().replace("\n", " ")
    if len(user_text) > 120:
        user_text = user_text[:117] + "..."
    return (event_name, user_text)
