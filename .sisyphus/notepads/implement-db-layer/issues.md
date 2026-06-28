## Code Quality Review Issues (2026-06-27)

1. **Deprecation warnings**: `datetime.utcnow()` is deprecated in Python 3.12+ and emits warnings under Python 3.14. Used as default in `Model.created_at`, `Machine.created_at`, `Benchmark.created_at`, `Result.created_at`. Should migrate to timezone-aware datetimes (e.g., `datetime.now(UTC)`).

2. **Weak test helper typing**: `_create_minimal_model`, `_create_minimal_machine`, and `_create_minimal_benchmark` in `tests/test_models.py` annotate `session: object` instead of `sqlalchemy.orm.Session`.

3. **Redundant foreign key declarations**: `schema.sql` declares both inline `REFERENCES ... ON DELETE CASCADE` (lines 33-34) and separate `FOREIGN KEY` constraints (lines 68-69) for the same columns in `benchmarks`. SQLite accepts this but it is redundant.

4. **LSP diagnostics unavailable**: `basedpyright` is not installed in the venv, so static type diagnostics could not be run.

## Final Manual QA Issues (2026-06-27)

1. **LSP diagnostics unavailable**: `basedpyright-langserver` not installed; could not run static type checks on changed files. Mitigation: pytest 14/14 PASS provides runtime verification.
2. **Deprecation warnings observed**: `datetime.utcnow()` warnings in scenarios 3, 8, and 9 — same known issue documented in code quality review, does not affect correctness.
