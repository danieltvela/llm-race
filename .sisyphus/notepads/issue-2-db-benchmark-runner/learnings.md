
## T3: save_benchmark_run() — Implementation Notes

- **Field name spelling**: Model uses `quantization` (American), not `quantisation` (British). LSP caught this.
- **NULL in UNIQUE constraints**: SQLite allows multiple rows with NULL in UNIQUE constraint columns, so `is_(None)` filters work correctly for finding existing Model records.
- **Machine find-or-create**: Unique constraint on `(hostname,)` means `.where(Machine.hostname == ...)` is sufficient.
- **Time conversion**: ScenarioResult stores times in seconds; Benchmark stores latency in ms (fields with `_ms` suffix). The `_to_ms()` helper handles `None` gracefully.
- **Status mapping**: "success" when no failures, "partial" when some succeeded, "error" when all failed.
- **Empty scenarios**: Returns `[]` without committing or erroring.
- **DB failure safety**: Catch `Exception` (not bare `except`), rollback, log warning, return `[]`.

## T2: Per-request metrics + DB saving in runner.py

- **Keyword-only params**: Using `*` before `run_id`, `system_info`, `provider_type` makes them keyword-only, preserving backward compatibility with existing callers like `cli.py`.
- **Inline imports**: DB imports (`init_db`, `save_benchmark_run`) are done inline inside the `try` block to avoid adding module-level imports to runner.py.
- **3-tuple signature**: `save_benchmark_run()` now accepts `list[tuple[ScenarioResult, list[RequestMetrics], datetime]]` — the 3rd element is `started_at` captured at scenario start.
- **started_at capture**: `datetime.utcnow()` is called at the TOP of each scenario iteration (before `time.monotonic()`), ensuring the timestamp reflects when the scenario began.
- **DB failure isolation**: DB save is wrapped in `try/except Exception` with `logger.warning` — never crashes the benchmark. CSV/JSON export runs unconditionally.
- **Backward compatibility**: When `run_id`, `system_info`, `provider_type` are all `None`, the DB save block is skipped entirely (all 3 must be non-None).
- **No new module imports**: `RequestMetrics` is defined in the same file, `datetime` already imported, `Any` already imported. Only inline imports added.

## T3: CLI flags --no-db and --force-detect

### Changes made to `llm_race/bench/cli.py`
- Added `import uuid` and `from llm_race.utils.system import collect_system_info`
- Added `--no-db` (store_true) and `--force-detect` (store_true) to the `run` subparser
- After `create_provider()`: generates `run_id = str(uuid.uuid4())`, then branches:
  - `--no-db`: sets `system_info=None`, `provider_type=None`, `effective_run_id=None`
  - otherwise: calls `collect_system_info().to_dict()`, sets `provider_type=args.provider`, `effective_run_id=run_id`
- Passes `run_id=effective_run_id`, `system_info=system_info`, `provider_type=provider_type` to `run_benchmarks()`
- `--force-detect` is a no-op currently; comment documents future caching work

### Verification
- `python -m llm_race run --help` shows both flags
- Module loads cleanly: `from llm_race.bench.cli import main` → OK
- No existing CLI args changed; workload profile resolution untouched

## test_db_saver.py — 6 unit tests for save_benchmark_run()

### Bugs found in saver.py during test creation:
1. **p95 → p90 mismatch**: saver passed `e2e_p95_ms`, `ttft_p95_ms`, `itl_p95_ms` but Benchmark model only has `e2e_p90_ms`, `ttft_p90_ms`, `itl_p90_ms`. Fixed by mapping p95 values to p90 columns.
2. **e2e_max_ms doesn't exist**: Benchmark model has no `e2e_max_ms` column. Removed from saver.

### Saver.py fixes applied:
- `e2e_p95_ms` → `e2e_p90_ms` (mapped from scenario.e2e_p95)
- `ttft_p95_ms` → `ttft_p90_ms` (mapped from scenario.ttft_p95)
- `itl_p95_ms` → `itl_p90_ms` (mapped from scenario.itl_p95)
- Removed `e2e_max_ms` entirely (no model column)

### Test patterns:
- In-memory SQLite with `Base.metadata.create_all(engine)` — no `init_db()` needed
- `sessionmaker` + context manager pattern for session fixture
- `select(Model).scalars().all()` for querying
- `patch.object(session, "commit", side_effect=...)` for failure testing
