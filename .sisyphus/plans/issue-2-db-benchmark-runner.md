# Issue #2 — Integrate DB Saving into Benchmark Runner

## TL;DR

> **Quick Summary**: Persist benchmark results (aggregated ScenarioResult + per-request RequestMetrics) to the SQLite database automatically after each benchmark run. Add `--no-db` to skip and `--force-detect` to re-collect machine info.
>
> **Deliverables**:
> - New `llm_race/db/saver.py` module with `save_benchmark_run()` function
> - Modified `llm_race/bench/runner.py` to preserve per-request metrics and call the saver
> - Modified `llm_race/bench/cli.py` with `--no-db` and `--force-detect` flags
> - Unit tests for the saver using in-memory SQLite
>
> **Estimated Effort**: Short (3-4 tasks)
> **Parallel Execution**: NO — sequential dependencies (saver → runner → CLI → test)
> **Critical Path**: T1 → T2 → T3 → T4

---

## Context

### Original Request
Integrate DB persistence into the benchmark runner — collect machine info, generate unique run IDs, and save ScenarioResult + per-request metrics to SQLite so that the web viewer can display historical data.

### Interview Summary
**Key Decisions**:
- Save BOTH aggregated (Benchmark row) AND per-request (Result rows) data
- DB save by default; `--no-db` flag to opt out
- Tests using in-memory SQLite (`sqlite:///:memory:`), tests-after
- CSV/JSON export must continue to work exactly as before
- `prompt_size` stored as string of integer (e.g., `"4096"`)
- Latency fields stored in milliseconds (DB model convention)
- `provider_type` passed through from CLI string (e.g., `"vllm"`), not derived from class name

### Metis Review
**Identified Gaps** (addressed / auto-resolved):
- **Provider name source**: Pass `provider_type: str` through `run_benchmarks()` explicitly — don't derive from class name
- **Model version/quantisation**: Store as None in DB (optional fields)
- **started_at per scenario**: Capture `datetime.utcnow()` in the runner loop
- **Session management**: Saver accepts a `Session`, lifecycle managed by caller (`run_benchmarks()`)
- **Error handling**: Log DB errors as warnings and continue — benchmarks must never fail because of DB

---

## Work Objectives

### Core Objective
Persist benchmark results to the SQLite database so the web viewer can display historical performance data.

### Concrete Deliverables
- `llm_race/db/saver.py` — new module
- Modified `llm_race/bench/runner.py` — preserve metrics, call saver
- Modified `llm_race/bench/cli.py` — `--no-db`, `--force-detect` flags
- `tests/test_db_saver.py` — saver unit tests

### Definition of Done
- [x] `python -m pytest tests/test_db_saver.py -v` — 6/6 tests pass
- [x] `python -m pytest` — 148 tests pass (no regressions)
- [x] `python -m llm_race run --help` shows `--no-db` and `--force-detect` flags

### Must Have
- DB save happens automatically after each benchmark run
- Both aggregated (Benchmark) and per-request (Result) rows are saved
- `--no-db` flag skips DB save
- `--force-detect` re-collects machine info
- Machine info collected once, cached, reused across scenarios
- CSV/JSON export unchanged

### Must NOT Have (Guardrails)
- No web viewer changes
- No schema migrations or Alembic
- No new provider implementations
- No changes to `run_scenario()` core measurement logic
- DB failure must NOT crash the benchmark

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after with in-memory SQLite
- **Framework**: pytest
- **Coverage target**: saver module + runner integration

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

---

## Execution Strategy

### Task Dependencies

```
T1 (db/saver.py) ──→ T2 (runner.py changes) ──→ T3 (cli.py changes)
     │                                              │
     └──→ T4 (tests/test_db_saver.py)               │
                                                    └──→ Final Verification
```

- **T1**: Create `db/saver.py` — can be tested in isolation
- **T2**: Modify `runner.py` — depends on T1 (needs the saver function)
- **T3**: Modify `cli.py` — depends on T2 (needs new runner signature)
- **T4**: Tests — depends on T1, can start after T1 is done

---

## TODOs

- [x] 1. Create `llm_race/db/saver.py` — `save_benchmark_run()` function

  **What to do**:
  - Create new file `llm_race/db/saver.py`
  - Implement `save_benchmark_run()` with this signature:

    ```python
    def save_benchmark_run(
        session: Session,
        *,
        run_id: str,
        provider_type: str,
        model_name: str,
        workload_profile: str | None,
        system_info: dict[str, Any],
        max_tokens: int,
        temperature: float,
        top_p: float,
        scenarios: list[tuple[ScenarioResult, list[RequestMetrics]]],
    ) -> list[int]:
    ```

    Where `scenarios` is a list of `(ScenarioResult, list[RequestMetrics])` pairs — one element per (concurrency, prompt_length) combination.

  - **Step 1 — Find or create Model record**:
    ```python
    model_record = session.execute(
        select(Model).where(
            Model.name == model_name,
            Model.version.is_(None),
            Model.quantisation.is_(None),
            Model.provider_name == provider_type,
        )
    ).scalar_one_or_none()
    if model_record is None:
        model_record = Model(
            name=model_name,
            provider_name=provider_type,
        )
        session.add(model_record)
        session.flush()
    ```

  - **Step 2 — Find or create Machine record**:
    ```python
    machine_record = session.execute(
        select(Machine).where(Machine.hostname == system_info["hostname"])
    ).scalar_one_or_none()
    if machine_record is None:
        machine_record = Machine(**{k: system_info.get(k) for k in
            ["hostname", "cpu", "gpu", "gpu_count", "ram_gb", "os", "os_version", "driver_version", "python_version"]})
        session.add(machine_record)
        session.flush()
    ```

  - **Step 3 — For each (ScenarioResult, RequestMetrics) pair, create one Benchmark row**:
    ```python
    benchmark = Benchmark(
        run_id=run_id,
        model_id=model_record.id,
        machine_id=machine_record.id,
        workload_profile=workload_profile or "",
        prompt_size=str(scenario.prompt_length),
        prompt_token_count=scenario.prompt_length,
        concurrency=scenario.concurrency,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        started_at=datetime.utcnow(),  # approximate; will be refined in T2
        wall_clock_seconds=scenario.wall_clock_seconds,
        total_requests=scenario.total_requests,
        successful_requests=scenario.successful_requests,
        failed_requests=scenario.failed_requests,
        throughput_rps=scenario.throughput_rps,
        throughput_tps=scenario.throughput_tps,
        e2e_mean_ms=_to_ms(scenario.e2e_mean),
        e2e_p50_ms=_to_ms(scenario.e2e_p50),
        e2e_p95_ms=_to_ms(scenario.e2e_p95),
        e2e_p99_ms=_to_ms(scenario.e2e_p99),
        e2e_max_ms=_to_ms(scenario.e2e_max),
        ttft_mean_ms=_to_ms(scenario.ttft_mean),
        ttft_p50_ms=_to_ms(scenario.ttft_p50),
        ttft_p95_ms=_to_ms(scenario.ttft_p95),
        ttft_p99_ms=_to_ms(scenario.ttft_p99),
        itl_mean_ms=_to_ms(scenario.itl_mean),
        itl_p50_ms=_to_ms(scenario.itl_p50),
        itl_p95_ms=_to_ms(scenario.itl_p95),
        status="success" if scenario.failed_requests == 0 else ("partial" if scenario.successful_requests > 0 else "error"),
    )
    session.add(benchmark)
    session.flush()
    ```

  - **Step 4 — For each request metrics list, create Result rows**:
    ```python
    for metrics in per_request_metrics:
        itl_mean = statistics.mean(metrics.inter_token_latencies) if metrics.inter_token_latencies else None
        result = Result(
            benchmark_id=benchmark.id,
            request_id=metrics.request_id,
            status=metrics.status,
            error_message=metrics.error_message,
            ttft_ms=_to_ms(metrics.ttft),
            e2e_latency_ms=_to_ms(metrics.e2e_latency),
            prompt_tokens=metrics.prompt_tokens,
            completion_tokens=metrics.completion_tokens,
            total_tokens=metrics.total_tokens,
            tokens_per_second=metrics.tokens_per_second,
            itl_mean=_to_ms(itl_mean),
        )
        session.add(result)
    ```

  - **Step 5 — Commit and return**:
    ```python
    try:
        session.commit()
        logger.info("Saved %d benchmark rows to DB", len(scenarios))
    except Exception:
        session.rollback()
        logger.warning("Failed to save benchmark results to DB", exc_info=True)
    ```

  - Helper function: `def _to_ms(seconds: float | None) -> float | None` — returns `round(seconds * 1000, 2)` if not None, else None
  - Import `statistics` for mean computation
  - Use `from sqlalchemy import select` for queries
  - Handle `nvidia-smi` failures gracefully — the `Machine` model has nullable fields for GPU info

  **Must NOT do**:
  - Do NOT modify run_scenario() or the dataclass definitions
  - Do NOT add a new dependency — sqlalchemy, statistics are already available
  - Do NOT make DB failure crash the benchmark (catch and log)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single new file, well-defined mapping logic, no complex algorithms
  - **Skills**: none required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (starts chain)
  - **Parallel Group**: Wave 1
  - **Blocks**: T2, T4
  - **Blocked By**: None

  **References**:
  - `llm_race/db/models.py:189-202` — `init_db()` returns engine + session factory
  - `llm_race/db/models.py:34-78` — `Model` class with unique constraint on `(name, version, quantisation, provider_name)`
  - `llm_race/db/models.py:86-104` — `Machine` class with unique constraint on `(hostname,)`
  - `llm_race/db/models.py:118-152` — `Benchmark` class with all field names and types
  - `llm_race/db/models.py:153-186` — `Result` class with per-request fields
  - `llm_race/bench/runner.py:27-42` — `RequestMetrics` dataclass (source data for Result rows)
  - `llm_race/bench/runner.py:45-68` — `ScenarioResult` dataclass (source data for Benchmark rows)
  - `llm_race/utils/system.py:53-67` — `SystemInfo.to_dict()` returns dict with Machine-model-mapped keys
  - `llm_race/db/queries.py:33-55` — existing query pattern showing session usage with `with session_factory() as session:`

  **Acceptance Criteria**:
  - [ ] `db/saver.py` exists with `save_benchmark_run()` function
  - [ ] Function accepts expected parameters
  - [ ] Function handles empty scenarios list gracefully (no rows created, no crash)

  **QA Scenarios**:
  ```
  Scenario: In-memory DB round-trip with valid data
    Tool: Bash (bun test / python -m pytest via unit test)
    Preconditions: In-memory SQLite database (sqlite:///:memory:) with all tables created
    Steps:
      1. Create an in-memory session via init_db()
      2. Call save_benchmark_run() with a single ScenarioResult + 2 RequestMetrics
      3. Query Benchmark table — assert 1 row with correct run_id, concurrency, prompt_length
      4. Query Result table — assert 2 rows with correct request_ids
    Expected Result: saver creates correct rows with mapped field values
    Evidence: .sisyphus/evidence/task-1-roundtrip.log

  Scenario: DB failure does not raise exception
    Tool: Bash (python -c)
    Preconditions: saver module imported, mock session that raises on commit
    Steps:
      1. Mock session.commit() to raise OperationalError
      2. Call save_benchmark_run()
      3. Assert no exception propagates (logged only)
    Expected Result: Function returns gracefully (logged warning)
    Evidence: .sisyphus/evidence/task-1-db-failure.log
  ```

  **Commit**: YES
  - Message: `feat(db): add save_benchmark_run() function`
  - Files: `llm_race/db/saver.py`
  - Pre-commit: `python -c "from llm_race.db.saver import save_benchmark_run; print('OK')"`


- [x] 2. Modify `llm_race/bench/runner.py` — preserve per-request metrics and call DB saver

  **What to do**:
  - Add new keyword parameters to `run_benchmarks()`:
    ```python
    async def run_benchmarks(
        ...
        *,
        run_id: str | None = None,
        system_info: dict[str, Any] | None = None,
        provider_type: str | None = None,
    ) -> list[ScenarioResult]:
    ```

  - Inside the main loop, capture per-request metrics alongside ScenarioResult:
    ```python
    all_results: list[ScenarioResult] = []
    all_scenario_metrics: list[list[RequestMetrics]] = []  # NEW
    all_started_at: list[datetime] = []  # NEW
    for prompt_len in prompt_lengths:
        for conc in concurrency:
            started_at = datetime.utcnow()  # NEW
            wall_start = time.monotonic()
            metrics = await run_scenario(...)
            wall_elapsed = time.monotonic() - wall_start
            scenario = _build_scenario_result(metrics, conc, prompt_len, wall_elapsed)
            all_results.append(scenario)
            all_scenario_metrics.append(metrics)  # NEW
            all_started_at.append(started_at)  # NEW
    ```

  - After CSV/JSON saving (existing code unchanged), add DB saving:
    ```python
    if run_id is not None and system_info is not None and provider_type is not None:
        try:
            from llm_race.db.models import init_db
            from llm_race.db.saver import save_benchmark_run

            engine, session_factory = init_db()
            with session_factory() as session:
                save_benchmark_run(
                    session=session,
                    run_id=run_id,
                    provider_type=provider_type,
                    model_name=model,
                    workload_profile=workload_profile,
                    system_info=system_info,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    scenarios=list(zip(all_results, all_scenario_metrics)),
                )
        except Exception:
            logger.warning("Failed to save benchmark results to DB", exc_info=True)
    ```

  - **Important**: `started_at` per scenario — pass `all_started_at` to the saver. Modify `save_benchmark_run()` to accept it:
    - Actually, simpler: pass `scenarios` as `list[tuple[ScenarioResult, list[RequestMetrics], datetime]]` — a 3-tuple that includes the started_at timestamp
    - Update the `save_benchmark_run()` signature in `db/saver.py` accordingly

  - Update the `_build_scenario_result` — no changes needed (it already works)

  - Keep CSV/JSON saving code exactly as-is (save_csv, save_json)

  - Update the function docstring to document the new parameters

  **Must NOT do**:
  - Do NOT modify `run_scenario()` — not needed
  - Do NOT change existing CSV/JSON export behavior
  - Do NOT change the return type of `run_benchmarks()`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Well-scoped modifications to one existing function
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1)
  - **Blocks**: T3
  - **Blocked By**: T1

  **References**:
  - `llm_race/bench/runner.py:264-339` — full `run_benchmarks()` function — lines to modify
  - `llm_race/bench/runner.py:310-328` — main loop that creates ScenarioResult — insert metrics preservation here
  - `llm_race/bench/runner.py:330-337` — output section — add DB save after existing output code
  - `llm_race/db/saver.py` (T1) — the saver function to call

  **Acceptance Criteria**:
  - [ ] `run_benchmarks()` accepts `run_id`, `system_info`, `provider_type` as optional keyword args
  - [ ] DB save happens automatically when these args are provided
  - [ ] DB failure logged as warning, does not crash benchmark
  - [ ] CSV/JSON export still works when DB args are not provided (backward compat)

  **QA Scenarios**:
  ```
  Scenario: Backward compatibility without DB args
    Tool: Bash (python -c)
    Preconditions: Provider object, normal arguments, no run_id/system_info
    Steps:
      1. Mock providers and run_scenario to return known data
      2. Call run_benchmarks() WITHOUT run_id/system_info/provider_type
      3. Assert it returns list[ScenarioResult] as before
      4. Assert CSV/JSON files are created (existing behavior)
    Expected Result: Old callers still work with no DB involvement
    Evidence: .sisyphus/evidence/task-2-backward-compat.log

  Scenario: DB save triggered when args provided
    Tool: Bash (python -c)
    Preconditions: Mock provider, in-memory DB session accessible
    Steps:
      1. Call run_benchmarks() WITH run_id, system_info, provider_type
      2. Assert no exceptions
    Expected Result: Function completes, save_benchmark_run is called
    Evidence: .sisyphus/evidence/task-2-db-trigger.log
  ```

  **Commit**: YES (groups with T3)
  - Message: `feat(bench): wire DB saving into run_benchmarks()`
  - Files: `llm_race/bench/runner.py`, `llm_race/db/saver.py`
  - Pre-commit: `python -c "from llm_race.bench.runner import run_benchmarks; print('OK')"`


- [x] 3. Modify `llm_race/bench/cli.py` — add `--no-db` and `--force-detect` flags

  **What to do**:
  - Add two new CLI arguments to the `run` subparser:
    ```python
    run_parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip saving results to the database",
    )
    run_parser.add_argument(
        "--force-detect",
        action="store_true",
        help="Re-collect machine info even if cached (not yet cached)",
    )
    ```

  - In the `main()` function, before calling `run_benchmarks()`, collect system info and generate run_id:
    ```python
    import uuid
    from llm_race.utils.system import collect_system_info

    run_id = str(uuid.uuid4())
    system_info = collect_system_info().to_dict() if not args.no_db else None
    provider_type = args.provider
    ```

  - Pass the new args to `run_benchmarks()`:
    ```python
    asyncio.run(
        run_benchmarks(
            ...
            run_id=run_id if not args.no_db else None,
            system_info=system_info,
            provider_type=provider_type if not args.no_db else None,
        )
    )
    ```
    (When `--no-db` is set, all three are None, so the saver code path is skipped)

  - Handle `--force-detect`: pass to `collect_system_info()` or note that caching is already handled — `system.py` collects fresh info every call (no caching yet), so `--force-detect` is a no-op for now but document the intent. Add a comment: `# force_detect is a no-op currently; caching will be implemented when needed`

  **Must NOT do**:
  - Do NOT change how existing CLI args work
  - Do NOT introduce provider-specific logic in CLI
  - Do NOT break `--workload` profile resolution (still takes precedence for concurrency/prompt_lengths)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small, well-scoped CLI changes
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T2)
  - **Blocks**: Nothing (last implementation task)
  - **Blocked By**: T2

  **References**:
  - `llm_race/bench/cli.py:1-106` — full CLI file
  - `llm_race/bench/cli.py:29-65` — argument definitions — add new flags here
  - `llm_race/bench/cli.py:67-102` — main() body — add system info and run_id here
  - `llm_race/utils/system.py:33-67` — SystemInfo dataclass and to_dict()
  - `llm_race/config/__init__.py:18` — `DEFAULT_PROVIDER` constant for `provider_type` default

  **Acceptance Criteria**:
  - [ ] `python -m llm_race run --help` shows `--no-db` and `--force-detect` flags
  - [ ] `python -m llm_race run --no-db --model gpt-3.5-turbo --concurrency 1 --prompt-lengths 64 --measured-iterations 1` runs without attempting DB save
  - [ ] `python -m llm_race run --model gpt-3.5-turbo --concurrency 1 --prompt-lengths 64 --measured-iterations 1` passes run_id/system_info to run_benchmarks

  **QA Scenarios**:
  ```
  Scenario: --no-db flag prevents DB access
    Tool: Bash (python -m)
    Preconditions: Project root, no DB file
    Steps:
      1. python -m llm_race run --no-db --model gpt-3.5-turbo --concurrency 1 --prompt-lengths 64 --measured-iterations 1 --output /tmp/test-no-db.csv
      2. Check exit code is 0
      3. Check CSV file exists
      4. Check DB file does NOT exist (or exists but has no new rows)
    Expected Result: Benchmark runs, CLI output shows no DB errors
    Evidence: .sisyphus/evidence/task-3-no-db.log
  ```

  **Commit**: YES (groups with T2)
  - Message: `feat(cli): add --no-db and --force-detect flags`
  - Files: `llm_race/bench/cli.py`
  - Pre-commit: `python -m llm_race run --help | grep no-db`


- [x] 4. Write unit tests for `db/saver.py`

  **What to do**:
  - Create `tests/test_db_saver.py`
  - Use in-memory SQLite for all tests
  - Test cases:

    **test_save_single_scenario**: Create a `ScenarioResult` + 2 `RequestMetrics`, call `save_benchmark_run()`, query Benchmark + Result tables, verify all fields are correctly mapped

    **test_save_multiple_scenarios**: 2 scenario results with different concurrency/prompt_length, verify 2 Benchmark rows created with correct values

    **test_find_or_create_model**: Call twice with same model_name/provider_type, verify only 1 Model row created (unique constraint)

    **test_find_or_create_machine**: Call twice with same hostname, verify only 1 Machine row created

    **test_empty_scenarios**: Call with empty list, verify no rows created, no exceptions

    **test_db_failure_handling**: Mock `session.commit()` to raise, verify exception is caught and logged, no crash

  - Fixture for in-memory DB:
    ```python
    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from llm_race.db.models import Base

    @pytest.fixture
    def session():
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        with session_factory() as s:
            yield s
    ```

  - Use the existing `collect_system_info().to_dict()` for realistic test data, or provide a minimal dict

  **Must NOT do**:
  - Do NOT test CLI or runner integration (that's for QA/manual)
  - Do NOT test against the real benchmarks.db file
  - Do NOT add external dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard unit tests with clear test cases
  - **Skills**: none required

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1, ideally after T1 is done)
  - **Blocks**: Nothing
  - **Blocked By**: T1

  **References**:
  - `llm_race/db/saver.py` (T1) — the module being tested
  - `llm_race/db/models.py` — creates tables via `Base.metadata.create_all(engine)`
  - `tests/test_providers.py` — existing test patterns in the project (conftest, etc.)

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/test_db_saver.py -v` — 6 tests, all pass
  - [ ] All tests pass `python -m pytest` (no regressions)

  **QA Scenarios**:
  ```
  Scenario: All tests pass
    Tool: Bash (python -m pytest)
    Preconditions: saver module exists
    Steps:
      1. python -m pytest tests/test_db_saver.py -v
    Expected Result: 6/6 tests pass
    Evidence: .sisyphus/evidence/task-4-all-tests.log
  ```

  **Commit**: YES
  - Message: `test(db): add unit tests for save_benchmark_run()`
  - Files: `tests/test_db_saver.py`
  - Pre-commit: `python -m pytest tests/test_db_saver.py -v`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in `.sisyphus/evidence/`.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `mypy llm_race/db/saver.py` + `python -m pytest`. Review all changed files for: bare `except:`, type errors, missing error handling, unused imports.
  Output: `Type check [PASS/FAIL] | Tests [N pass/N fail] | Issues [N] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute every QA scenario from every task. Test real integration: run a minimal benchmark against a mock provider, verify DB file has rows.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1. Check "Must NOT do" compliance. Detect cross-task contamination.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(db): add save_benchmark_run() function` — `llm_race/db/saver.py`
- **T2+T3**: `feat(bench): wire DB saving into runner and CLI` — `llm_race/bench/runner.py`, `llm_race/bench/cli.py`, `llm_race/db/saver.py` (updated for started_at)
- **T4**: `test(db): add unit tests for save_benchmark_run()` — `tests/test_db_saver.py`

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/test_db_saver.py -v
# Expected: 6 passed

python -m pytest
# Expected: 120+ passed (no regressions)

python -m llm_race run --help
# Expected: shows --no-db and --force-detect flags
```

### Final Checklist
- [x] `save_benchmark_run()` creates Model, Machine, Benchmark, Result rows
- [x] `--no-db` flag disables DB save completely
- [x] `--force-detect` flag accepted (even if no-op)
- [x] CSV/JSON export unchanged
- [x] DB errors don't crash the benchmark
- [x] All pre-existing tests still pass
