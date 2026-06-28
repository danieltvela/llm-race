# learnings — db-queries test scaffolding

## Patterns observed
- `test_models.py` uses `tempfile.mktemp(suffix=".db")` for per-test SQLite files — clean isolation
- All models use `datetime.utcnow()` as default; but tests should use `datetime(..., tzinfo=timezone.utc)` for timezone-aware datetimes
- SQLAlchemy 2.0 ORM with `mapped_column()` syntax
- Factories use `session.add()` + `session.commit()` (not `session.flush()` then commit)
- `Result.request_id` is auto-incremented by the DB, but we also set it manually — the `create_result` helper handles this by checking `benchmark.results[-1].request_id + 1`

## Gotchas
- No `pyproject.toml` — project is not pip-installable, so `uv pip install -e .` fails
- LSP (basedpyright) not installed in environment, so `lsp_diagnostics` returns errors for all `.py` files
- pytest is installed globally (`pip list`) but not in `.venv` — need to install it: `uv pip install pytest`