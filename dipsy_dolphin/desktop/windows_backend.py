from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import shutil
import subprocess
import webbrowser
from urllib.parse import quote_plus

from .backend import DesktopBackendProtocol
from .catalog import AppCatalogEntry, get_app_catalog_entry
from .models import DesktopOperationResult


SEARCH_URL_TEMPLATE = "https://www.google.com/search?q={query}"
SW_RESTORE = 9


def build_browser_search_url(query: str) -> str:
    return SEARCH_URL_TEMPLATE.format(query=quote_plus(query))


@dataclass(frozen=True)
class WindowSnapshot:
    handle: int
    title: str
    class_name: str


class WindowsDesktopBackend(DesktopBackendProtocol):
    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        self._enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def focus_or_open_app(self, app_id: str) -> DesktopOperationResult:
        entry = get_app_catalog_entry(app_id)
        if entry is None:
            message = f"That app id is not on Dipsy's approved list: {app_id}."
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=app_id,
                resolved_app_id=app_id,
                status="failed",
                message=message,
                failure_reason=message,
            )

        window = self._find_window_for_entry(entry)
        if window is not None and self._focus_window(window.handle):
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=window.title or entry.app_id,
                resolved_app_id=entry.app_id,
                status="success",
                message=f"Focused {entry.description}",
                focused=True,
            )

        launch_result = self._launch_entry(entry)
        if launch_result.status == "success":
            return launch_result
        if window is not None:
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=entry.app_id,
                resolved_app_id=entry.app_id,
                status="failed",
                message=launch_result.message,
                failure_reason=launch_result.failure_reason
                or f"Could not focus or launch {entry.description}",
            )
        return launch_result

    def browser_search(self, query: str) -> DesktopOperationResult:
        url = build_browser_search_url(query)
        opened = self._open_in_browser(url)
        if not opened:
            message = f"Browser search failed for {query!r}."
            return DesktopOperationResult(
                operation="browser_search",
                target=query,
                resolved_app_id="browser",
                status="failed",
                message=message,
                failure_reason=message,
            )

        return DesktopOperationResult(
            operation="browser_search",
            target=query,
            resolved_app_id="browser",
            status="success",
            message=f"Opened a browser search for {query}.",
            opened=True,
            launched=True,
        )

    def open_url(self, url: str) -> DesktopOperationResult:
        opened = self._open_in_browser(url)
        if not opened:
            message = f"Opening {url} in the browser failed."
            return DesktopOperationResult(
                operation="open_url",
                target=url,
                resolved_app_id="browser",
                status="failed",
                message=message,
                failure_reason=message,
            )

        return DesktopOperationResult(
            operation="open_url",
            target=url,
            resolved_app_id="browser",
            status="success",
            message=f"Opened {url}.",
            opened=True,
            launched=True,
        )

    def open_path(self, path: str) -> DesktopOperationResult:
        try:
            os.startfile(path)
        except OSError as exc:
            message = f"Opening {path} failed: {exc}"
            return DesktopOperationResult(
                operation="open_path",
                target=path,
                status="failed",
                message=message,
                failure_reason=str(exc),
            )

        return DesktopOperationResult(
            operation="open_path",
            target=path,
            resolved_app_id="explorer",
            status="success",
            message=f"Opened {path}.",
            opened=True,
            launched=True,
        )

    def _launch_entry(self, entry: AppCatalogEntry) -> DesktopOperationResult:
        if entry.launch_via_webbrowser:
            opened = self._open_in_browser("about:blank")
            if opened:
                return DesktopOperationResult(
                    operation="focus_or_open_app",
                    target=entry.app_id,
                    resolved_app_id=entry.app_id,
                    status="success",
                    message=f"Opened {entry.description}",
                    launched=True,
                    opened=True,
                )
            message = f"Opening {entry.description} failed."
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=entry.app_id,
                resolved_app_id=entry.app_id,
                status="failed",
                message=message,
                failure_reason=message,
            )

        if entry.launch_uri:
            try:
                os.startfile(entry.launch_uri)
            except OSError as exc:
                message = f"Opening {entry.description} failed: {exc}"
                return DesktopOperationResult(
                    operation="focus_or_open_app",
                    target=entry.app_id,
                    resolved_app_id=entry.app_id,
                    status="failed",
                    message=message,
                    failure_reason=str(exc),
                )
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=entry.app_id,
                resolved_app_id=entry.app_id,
                status="success",
                message=f"Opened {entry.description}",
                launched=True,
                opened=True,
            )

        command = self._resolve_launch_command(entry)
        if command is None:
            message = f"No launch command is available for {entry.description}"
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=entry.app_id,
                resolved_app_id=entry.app_id,
                status="failed",
                message=message,
                failure_reason=message,
            )

        try:
            self._spawn_command(command)
        except OSError as exc:
            message = f"Launching {entry.description} failed: {exc}"
            return DesktopOperationResult(
                operation="focus_or_open_app",
                target=entry.app_id,
                resolved_app_id=entry.app_id,
                status="failed",
                message=message,
                failure_reason=str(exc),
            )

        return DesktopOperationResult(
            operation="focus_or_open_app",
            target=entry.app_id,
            resolved_app_id=entry.app_id,
            status="success",
            message=f"Launched {entry.description}",
            launched=True,
        )

    def _open_in_browser(self, url: str) -> bool:
        return bool(webbrowser.open(url))

    def _spawn_command(self, command: tuple[str, ...]) -> subprocess.Popen[str]:
        return subprocess.Popen(command)

    def _resolve_launch_command(self, entry: AppCatalogEntry) -> tuple[str, ...] | None:
        for command in entry.launch_commands:
            if self._command_is_available(command[0]):
                return command
        return None

    def _command_is_available(self, executable: str) -> bool:
        return shutil.which(executable) is not None

    def _find_window_for_entry(self, entry: AppCatalogEntry) -> WindowSnapshot | None:
        class_names = {value.casefold() for value in entry.focus_class_names}
        title_keywords = tuple(value.casefold() for value in entry.focus_title_keywords)

        class_match: WindowSnapshot | None = None
        title_match: WindowSnapshot | None = None
        for window in self._enumerate_windows():
            class_name = window.class_name.casefold()
            title = window.title.casefold()
            if class_names and class_name in class_names:
                class_match = class_match or window
            if title_keywords and any(keyword in title for keyword in title_keywords):
                title_match = title_match or window
        return class_match or title_match

    def _enumerate_windows(self) -> list[WindowSnapshot]:
        windows: list[WindowSnapshot] = []

        @self._enum_windows_proc
        def _callback(hwnd: wintypes.HWND, _lparam: wintypes.LPARAM) -> bool:
            if not self._user32.IsWindowVisible(hwnd):
                return True
            title = self._window_text(hwnd)
            class_name = self._class_name(hwnd)
            if not title and not class_name:
                return True
            windows.append(WindowSnapshot(handle=int(hwnd), title=title, class_name=class_name))
            return True

        self._user32.EnumWindows(_callback, 0)
        return windows

    def _window_text(self, hwnd: wintypes.HWND) -> str:
        length = self._user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def _class_name(self, hwnd: wintypes.HWND) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        self._user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def _focus_window(self, handle: int) -> bool:
        hwnd = wintypes.HWND(handle)
        self._user32.ShowWindow(hwnd, SW_RESTORE)
        return bool(self._user32.SetForegroundWindow(hwnd))
