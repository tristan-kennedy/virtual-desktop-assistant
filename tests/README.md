# Tests

No automated tests exist yet.

Recommended first test targets:

- `AssistantBrain.permissions_status_line`
- `AssistantBrain.apply_permission_decision`
- `AssistantBrain.reset_state`
- `AssistantBrain.handle_user_message`

Suggested layout:

- `tests/test_brain.py`
- `tests/test_models.py`

For now, manual verification is:

```bash
python main.py
```

Then verify:

- the pet appears and moves
- chat responses render in the bubble
- permission prompts open and resolve
- the loss dialog appears only for the defined risky combination
