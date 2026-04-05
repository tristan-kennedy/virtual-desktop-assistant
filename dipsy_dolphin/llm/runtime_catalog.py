from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeArchive:
    url: str
    archive_size: int
    archive_sha256: str
    extracted_size: int


@dataclass(frozen=True)
class RuntimeBundle:
    runtime_id: str
    display_name: str
    server_executable: str
    primary_archive: RuntimeArchive
    support_archive: RuntimeArchive | None = None


WINDOWS_RUNTIME_BUNDLES = {
    "cuda": RuntimeBundle(
        runtime_id="cuda",
        display_name="llama.cpp Windows CUDA 13.1",
        server_executable="llama-server.exe",
        primary_archive=RuntimeArchive(
            url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/llama-b8468-bin-win-cuda-13.1-x64.zip",
            archive_size=155_365_158,
            archive_sha256="60236c85e003cdd91f46052bb0cabfae1b2ea3a8c54e2ebd8cd9cdba799e94c9",
            extracted_size=237_263_928,
        ),
        support_archive=RuntimeArchive(
            url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/cudart-llama-bin-win-cuda-13.1-x64.zip",
            archive_size=402_582_216,
            archive_sha256="f96935e7e385e3b2d0189239077c10fe8fd7e95690fea4afec455b1b6c7e3f18",
            extracted_size=532_803_920,
        ),
    ),
    "vulkan": RuntimeBundle(
        runtime_id="vulkan",
        display_name="llama.cpp Windows Vulkan",
        server_executable="llama-server.exe",
        primary_archive=RuntimeArchive(
            url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/llama-b8468-bin-win-vulkan-x64.zip",
            archive_size=101_305_118,
            archive_sha256="",
            extracted_size=149_946_368,
        ),
    ),
}

DEFAULT_RUNTIME_BACKEND = "auto"


def select_runtime_bundle(preferred_backend: str | None = None) -> RuntimeBundle:
    backend = normalize_runtime_backend(preferred_backend or os.environ.get("DIPSY_RUNTIME_BACKEND"))
    if backend == "auto":
        backend = _auto_backend()
    return WINDOWS_RUNTIME_BUNDLES[backend]


def normalize_runtime_backend(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in {"auto", "cuda", "vulkan"}:
        return cleaned
    return DEFAULT_RUNTIME_BACKEND


def _auto_backend() -> str:
    if os.name == "nt" and _has_cuda_driver():
        return "cuda"
    return "vulkan"


def _has_cuda_driver() -> bool:
    if os.name != "nt":
        return False
    try:
        ctypes.WinDLL("nvcuda.dll")
    except OSError:
        return False
    return True
