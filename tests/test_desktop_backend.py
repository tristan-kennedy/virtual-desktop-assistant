from dipsy_dolphin.desktop.catalog import get_app_catalog_entry
from dipsy_dolphin.desktop.models import DesktopOperationResult
from dipsy_dolphin.desktop.windows_backend import (
    WindowsDesktopBackend,
    WindowSnapshot,
    build_browser_search_url,
)


def test_build_browser_search_url_encodes_query() -> None:
    assert build_browser_search_url("dolphin facts") == (
        "https://www.google.com/search?q=dolphin+facts"
    )


def test_resolve_launch_command_uses_first_available_candidate(monkeypatch) -> None:
    backend = WindowsDesktopBackend()
    entry = get_app_catalog_entry("terminal")
    assert entry is not None

    monkeypatch.setattr(
        backend,
        "_command_is_available",
        lambda executable: executable == "powershell.exe",
    )

    assert backend._resolve_launch_command(entry) == ("powershell.exe",)


def test_focus_or_open_app_prefers_existing_window(monkeypatch) -> None:
    backend = WindowsDesktopBackend()
    window = WindowSnapshot(handle=101, title="notes - Notepad", class_name="Notepad")

    monkeypatch.setattr(backend, "_find_window_for_entry", lambda entry: window)
    monkeypatch.setattr(backend, "_focus_window", lambda handle: handle == 101)
    monkeypatch.setattr(
        backend,
        "_launch_entry",
        lambda entry: (_ for _ in ()).throw(AssertionError("launch should not run")),
    )

    result = backend.focus_or_open_app("notepad")

    assert result.status == "success"
    assert result.focused is True
    assert result.launched is False


def test_focus_or_open_app_falls_back_to_launch_when_window_missing(monkeypatch) -> None:
    backend = WindowsDesktopBackend()

    monkeypatch.setattr(backend, "_find_window_for_entry", lambda entry: None)
    monkeypatch.setattr(
        backend,
        "_launch_entry",
        lambda entry: DesktopOperationResult(
            operation="focus_or_open_app",
            target=entry.app_id,
            resolved_app_id=entry.app_id,
            status="success",
            message="Launched it.",
            launched=True,
        ),
    )

    result = backend.focus_or_open_app("notepad")

    assert result.status == "success"
    assert result.launched is True
    assert result.focused is False
