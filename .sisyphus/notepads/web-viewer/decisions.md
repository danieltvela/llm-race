# Decisions — Web Viewer

## F4 Scope Fidelity Check (2026-06-28)

- DB models/schema implementation is treated as a necessary prerequisite rather than scope creep because the web viewer cannot query a non-existent DB layer. The original plan's research finding that "DB layer fully implemented" was inaccurate based on the actual repository state.
- `psutil` added to `requirements.txt` is flagged as minor scope creep because it is not used by the web viewer; it supports the untracked `llm_race/utils/system.py` module.
- Verdict: APPROVE with documented contamination notes, because every web-viewer spec requirement is implemented and the out-of-scope changes are either prerequisites or minor.
