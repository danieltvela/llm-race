# Learnings: warmup-iterations tests

## runner.py internals
- `run_scenario()` does an early return `[]` when `measured_iterations == 0` (line 114-116). This means warmup is **not** executed when there are no measured iterations. The test `test_measured_zero` reflects this actual behaviour.
- Request IDs are reset per batch inside `_run_batch` (via `enumerate`), but then overwritten in `_run_all` during measured iterations with `m.request_id = len(all_metrics) + j`, making them globally sequential.
- FakeProvider must implement both `stream_complete()` and `complete()` if inheriting from `Provider` (abstract base), otherwise LSP/type-checker complains.

## pytest-asyncio setup
- `conftest.py` already registers `pytest_plugins = ["pytest_asyncio"]`, so `@pytest.mark.asyncio` works without extra config.

## Test count discrepancy
- Plan expected 8 tests, but detailed spec lists 9 individual test methods (3 + 2 + 2 + 2). All 9 pass.
