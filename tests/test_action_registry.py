from dipsy_dolphin.actions.registry import (
    action_prompt_payload,
    sanitize_action_request,
    validate_action_request,
)


def test_action_prompt_payload_includes_desktop_actions_and_arg_specs() -> None:
    payload = action_prompt_payload()
    actions = {item["action_id"]: item for item in payload}

    assert "focus_or_open_app" in actions
    assert "browser_search" in actions
    assert actions["focus_or_open_app"]["args"]["app_id"]["choices"] == [
        "browser",
        "terminal",
        "explorer",
        "notepad",
        "settings",
    ]


def test_validate_action_request_accepts_supported_app_id() -> None:
    validation = validate_action_request("focus_or_open_app", {"app_id": "Notepad"})

    assert validation.is_valid is True
    assert validation.args == {"app_id": "notepad"}


def test_sanitize_action_request_rejects_invalid_url() -> None:
    request = sanitize_action_request("open_url", {"url": "ftp://example.com"})

    assert request is None


def test_sanitize_action_request_resolves_existing_path(tmp_path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("hello", encoding="utf-8")

    request = sanitize_action_request("open_path", {"path": str(sample)})

    assert request is not None
    assert request.args["path"] == str(sample.resolve())
