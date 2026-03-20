# Tests

No automated tests exist yet.

Recommended first test targets:

- `AssistantBrain.parse_interests`
- `AssistantBrain.status_line`
- `AssistantBrain.random_autonomous_line`
- `AssistantBrain.reset_state`
- `AssistantBrain.handle_user_message`
- `ProfileStore.load_profile`
- `ProfileStore.save_profile`

Suggested layout:

- `tests/test_brain.py`
- `tests/test_models.py`
- `tests/test_storage.py`

For now, manual verification is:

```bash
python main.py
```

For install verification on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\install-local.ps1 -Build -DesktopShortcut
```

Then verify:

- the pet appears and moves
- the onboarding prompts ask for name and interests
- chat responses render in the bubble
- Dipsy blurts out random lines while idling
- the status menu reflects the remembered session details
- relaunching the app keeps the stored name and interests
