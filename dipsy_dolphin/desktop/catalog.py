from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppCatalogEntry:
    app_id: str
    description: str
    focus_title_keywords: tuple[str, ...] = ()
    focus_class_names: tuple[str, ...] = ()
    launch_commands: tuple[tuple[str, ...], ...] = ()
    launch_uri: str = ""
    launch_via_webbrowser: bool = False


APP_CATALOG = {
    "browser": AppCatalogEntry(
        app_id="browser",
        description="Default web browser.",
        focus_title_keywords=(
            "Google Chrome",
            "Mozilla Firefox",
            "Microsoft Edge",
            "Brave",
            "Opera",
            "Vivaldi",
        ),
        launch_via_webbrowser=True,
    ),
    "terminal": AppCatalogEntry(
        app_id="terminal",
        description="Windows terminal or PowerShell window.",
        focus_title_keywords=("Windows Terminal", "PowerShell", "Command Prompt"),
        launch_commands=(("wt.exe",), ("powershell.exe",)),
    ),
    "explorer": AppCatalogEntry(
        app_id="explorer",
        description="Windows File Explorer.",
        focus_class_names=("CabinetWClass", "ExploreWClass"),
        launch_commands=(("explorer.exe",),),
    ),
    "notepad": AppCatalogEntry(
        app_id="notepad",
        description="Windows Notepad.",
        focus_title_keywords=("Notepad",),
        launch_commands=(("notepad.exe",),),
    ),
    "settings": AppCatalogEntry(
        app_id="settings",
        description="Windows Settings.",
        focus_title_keywords=("Settings",),
        launch_uri="ms-settings:",
    ),
}


def allowed_app_ids() -> tuple[str, ...]:
    return tuple(APP_CATALOG)


def get_app_catalog_entry(app_id: str) -> AppCatalogEntry | None:
    return APP_CATALOG.get(app_id)


def app_catalog_prompt_payload() -> list[dict[str, object]]:
    return [
        {
            "app_id": entry.app_id,
            "description": entry.description,
        }
        for entry in APP_CATALOG.values()
    ]
