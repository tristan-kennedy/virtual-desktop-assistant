# Desktop Control Smoke Checklist

Use this checklist for quick manual verification on Windows after changes to desktop capabilities.

## Chat prompts

- Ask Dipsy to search the web for a simple phrase and confirm the default browser opens a search.
- Ask Dipsy to open a normal `https://` URL and confirm the browser opens it.
- Ask Dipsy to open Notepad and confirm it launches or focuses an existing window.
- Ask Dipsy to open Explorer and confirm a File Explorer window launches or focuses.
- Ask Dipsy to open Settings and confirm the Settings app opens.

## Failure checks

- Ask Dipsy to open an unsupported app and confirm the action is rejected rather than turning into a raw command.
- Ask Dipsy to open a non-HTTP URL and confirm the action is rejected.
- Ask Dipsy to open a missing local path and confirm the action is rejected.

## Follow-up behavior

- Confirm Dipsy says what it is doing before the action.
- Confirm the follow-up line reacts to the real result instead of repeating the request.
- Confirm action failures surface as visible, short error lines rather than silent no-ops.
