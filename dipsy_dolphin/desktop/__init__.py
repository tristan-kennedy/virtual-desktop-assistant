from __future__ import annotations

import sys

from .backend import DesktopBackendProtocol, UnavailableDesktopBackend


def create_default_desktop_backend() -> DesktopBackendProtocol:
    if sys.platform == "win32":
        from .windows_backend import WindowsDesktopBackend

        return WindowsDesktopBackend()
    return UnavailableDesktopBackend()
