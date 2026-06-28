# Issues — Web Viewer

## F4 Scope Fidelity Check (2026-06-28)

- `lsp_diagnostics` could not run because the configured LSP server (`basedpyright`) is not installed in the environment. Verification relied on the passing pytest suite instead.
- The working tree contains several untracked files outside the committed web-viewer scope (`llm_race/utils/system.py`, `tests/test_system.py`, `tests/test_models.py`, etc.). These were not part of the `main~7..main` commit range and are not evaluated by this fidelity check.
