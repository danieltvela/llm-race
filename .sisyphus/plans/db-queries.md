# DB Queries: list, compare, timeseries

## TL;DR

> **Quick Summary**: Implement three named query functions in `llm_race/db/queries.py` for retrieving benchmark data — listing with filters/sorting/pagination, side-by-side run comparison, and time-series data for charting.
>
> **Deliverables**:
> - `llm_race/db/queries.py` — 3 implemented query functions
> - `tests/test_queries.py` — TDD test suite for all queries
> - `llm_race/db/types.py` — Query result dataclasses
>
> **Estimated Effort**: Short
> **Parallel Execution**: YES - 1 foundation wave + 3 parallel tasks + final verification
> **Critical Path**: Types → Test fixtures → (list_benchmarks ‖ compare_runs ‖ timeseries) → Final QA

---

## Context

### Original Request
Issue #12 — Implement named query functions in `llm_race/db/queries.py`:
- `list_benchmarks(filters)` — list benchmarks with optional filters
- `compare_runs(run_ids)` — fetch detailed metrics for 2-4 runs
- `timeseries(model, provider, metric, date_range)` — performance data over time

### Interview Summary

**Key Discussions**:
- **Return format**: Dataclasses (immutable, typed, easy to serialize)
- **Pagination**: offset + limit, with total_count in response
- **Sorting**: Configurable `sort_by` + `sort_order`, default `started_at DESC`
- **Timeseries level**: Both Benchmark summary AND per-Result data
- **Date parameters**: Python `datetime` objects (UTC)
- **Empty results**: Return empty list/dict (no exceptions)
- **Metrics**: All Benchmark numeric columns
- **Test strategy**: TDD (RED → GREEN → REFACTOR)
- **Session pattern**: Functions accept a `Session` parameter (testability)

**Research Findings**:
- Models fully defined: Model, Machine, Benchmark, Result with SQLAlchemy 2.0 ORM
- Existing test pattern: `db_session` fixture in `conftest.py`-style (in-memory SQLite)
- `queries.py` is a 4-line stub
- No existing query result types

### Metis Review

**Identified Gaps** (self-resolved):
- **Session management**: Functions accept `Session` parameter — standard testable pattern
- **list_benchmarks return shape**: Should JOIN Model+Machine to show readable names (model name, provider, hostname)
- **compare_runs output**: Include Benchmark-level metrics + nested per-Result data
- **Pagination response**: Return `(results, total_count)` tuple or dataclass with total
- **Metrics enum**: Use a `Literal` type or set of accepted column names for `timeseries(metric=...)`

---

## Work Objectives

### Core Objective
Implement 3 query functions in `llm_race/db/queries.py` using SQLAlchemy ORM, returning typed dataclasses.

### Concrete Deliverables
- `llm_race/db/types.py` — Dataclasses: `BenchmarkSummary`, `BenchmarkDetail`, `TimeseriesPoint`, `PaginatedResult`
- `llm_race/db/queries.py` — Functions: `list_benchmarks`, `compare_runs`, `timeseries`
- `tests/test_queries.py` — Full TDD test suite

### Definition of Done
- [ ] `pytest tests/test_queries.py -v` → all tests pass (15+ tests)
- [ ] Each function has agent-executed QA scenarios verified
- [ ] All return types are validated dataclasses
- [ ] No raw SQLAlchemy rows exposed outside queries.py

### Must Have
- [ ] `list_benchmarks(filters, sort_by, sort_order, offset, limit)` → `PaginatedResult[BenchmarkSummary]`
- [ ] `compare_runs(run_ids: list[str])` → `list[BenchmarkDetail]`
- [ ] `timeseries(model, provider, metric, date_start, date_end, level)` → `list[TimeseriesPoint]`
- [ ] Filters on: model name, provider, machine hostname, date range, status
- [ ] Pagination response includes `total_count`
- [ ] Validation: `compare_runs` rejects fewer than 2 or more than 4 run_ids
- [ ] TDD: RED (test fails) → GREEN (impl passes) → REFACTOR for each function

### Must NOT Have (Guardrails)
- **NO caching** — each call queries the database fresh
- **NO CSV export** — that's the web viewer's responsibility
- **NO web endpoints** — these are Python functions only
- **NO eager loading of all Results in list_benchmarks** — avoid N+1 on massive datasets
- **NO raw rows returned** — always wrap in dataclasses

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest, SQLAlchemy, in-memory SQLite fixture)
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Framework**: pytest 8.x
- **TDD**: Each function task writes tests BEFORE implementation

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario}.{ext}`.

- **Test execution**: `pytest tests/test_queries.py -v` for unit tests
- **Integration**: Bash scripts that call query functions with real SQLite, verifying return types and values

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — start immediately):
├── Task 1: Dataclass types (types.py) [quick]
└── Task 2: Shared test fixtures + test skeleton [quick]

Wave 2 (Core implementation — parallel after Wave 1):
├── Task 3: list_benchmarks — TDD (test → impl) [unspecified-high]
├── Task 4: compare_runs — TDD (test → impl) [unspecified-high]
└── Task 5: timeseries — TDD (test → impl) [unspecified-high]

Wave FINAL (After ALL tasks):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
```

### Dependency Matrix
- **1, 2**: — (no deps) — blocks 3, 4, 5
- **3**: 1, 2 — blocked by 1, 2 — nothing blocks
- **4**: 1, 2 — blocked by 1, 2 — nothing blocks
- **5**: 1, 2 — blocked by 1, 2 — nothing blocks
- **F1-F4**: 3, 4, 5 — blocked by all — final wave

---

## TODOs

- [x] 1. Define query result dataclasses (`types.py`)

  **What to do**:
  - Create `llm_race/db/types.py` with these dataclasses:
    - `BenchmarkSummary` — id, run_id, model_name, provider_name, hostname, workload_profile, prompt_size, concurrency, started_at, completed_at, wall_clock_seconds, total_requests, successful_requests, failed_requests, throughput_tps, e2e_mean_ms, status
    - `BenchmarkDetail` — extends BenchmarkSummary with all metric columns + nested results: `results: list[ResultRow]`
    - `ResultRow` — request_id, status, ttft_ms, e2e_latency_ms, prompt_tokens, completion_tokens, total_tokens, tokens_per_second, itl_mean
    - `TimeseriesPoint` — date (datetime), value (float), run_id (str), label (str)
    - `PaginatedResult[T]` — items: list[T], total_count: int, offset: int, limit: int
    - `BenchmarkFilters` — model_name: str | None, provider_name: str | None, machine_hostname: str | None, date_start: datetime | None, date_end: datetime | None, status: str | None, workload_profile: str | None, prompt_size: str | None
  - All dataclasses use `@dataclass(frozen=True)` for immutability
  - All datetime fields typed as `datetime`
  - All optional fields typed as `Optional[...]` or `... | None`
  - Import in `llm_race/db/__init__.py`

  **Must NOT do**:
  - Do NOT add business logic or default values beyond sensible defaults
  - Do NOT couple to SQLAlchemy models

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure type definition file, no logic, straightforward
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: 3, 4, 5
  - **Blocked By**: None (can start immediately)

  **References**:
  - `llm_race/db/models.py` — Existing ORM models to see field names and types
  - `llm_race/config/base.py:StreamResult` — Existing dataclass pattern in the codebase (frozen dataclass, typed fields)

  **Acceptance Criteria**:
  - [ ] `types.py` exists with all 6 dataclasses
  - [ ] `from llm_race.db.types import BenchmarkSummary, BenchmarkDetail, ResultRow, TimeseriesPoint, PaginatedResult, BenchmarkFilters` works
  - [ ] `pytest -c "from llm_race.db.types import BenchmarkSummary; bs = BenchmarkSummary(...); assert bs.run_id"` runs without error

  **QA Scenarios**:
  ```
  Scenario: All dataclasses can be instantiated
    Tool: Bash
    Preconditions: llm_race installed in .venv
    Steps:
      1. Run: python -c "from llm_race.db.types import BenchmarkSummary, BenchmarkDetail, ResultRow, TimeseriesPoint, PaginatedResult, BenchmarkFilters; print('OK')"
      2. Run: python -c "from llm_race.db.types import BenchmarkSummary; b = BenchmarkSummary(id=1, run_id='abc123', model_name='test', provider_name='test', hostname='h', workload_profile='single-user', prompt_size='medium', concurrency=1, started_at=__import__('datetime').datetime.utcnow(), total_requests=10, successful_requests=10, failed_requests=0, status='completed'); assert b.run_id == 'abc123'; assert b.failed_requests == 0; assert b.successful_requests == 10; print('OK')"
    Expected Result: Both commands print "OK"
    Evidence: .sisyphus/evidence/task-1-dataclass-creation.txt

  Scenario: PaginatedResult generic works with type param
    Tool: Bash
    Preconditions: Same
    Steps:
      1. Run: python -c "from llm_race.db.types import PaginatedResult, BenchmarkSummary; p = PaginatedResult(items=[], total_count=0, offset=0, limit=20); assert p.total_count == 0; assert p.offset == 0; assert p.limit == 20; print('OK')"
    Expected Result: Prints "OK"
    Evidence: .sisyphus/evidence/task-1-paginated-result.txt
  ```

  **Commit**: YES
  - Message: `feat(db): add query result dataclasses`
  - Files: `llm_race/db/types.py`, `llm_race/db/__init__.py`

- [x] 2. Add shared test fixtures for queries

  **What to do**:
  - Create `tests/test_queries.py` with TDD skeleton
  - Add helper functions for creating test data (model, machine, benchmark, results)
  - Use the existing `db_session` fixture pattern from `tests/test_models.py`
  - Add pytest fixture `query_session` that populates sample data:
    - 2 models (different providers)
    - 2 machines (different hostnames)
    - 5+ benchmarks across different dates, statuses, workloads
    - 10+ Result rows attached to benchmarks
  - Ensure sample data covers: different statuses, different workload profiles, different prompt sizes, both completed and running benchmarks

  **Must NOT do**:
  - Do NOT implement query functions here (TDD — tests come before impl in Tasks 3-5, but scaffolding here)
  - Do NOT import from queries.py yet — just set up the data

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard test fixture setup, no complex logic
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: 3, 4, 5
  - **Blocked By**: None

  **References**:
  - `tests/test_models.py` — Existing `db_session` fixture pattern, `_create_minimal_*` helpers
  - `llm_race/db/models.py` — Full model definitions for creating test data

  **Acceptance Criteria**:
  - [ ] `tests/test_queries.py` exists with `query_session` fixture
  - [ ] Fixture populates 2 models, 2 machines, 5+ benchmarks, 10+ results
  - [ ] `pytest tests/test_queries.py::test_query_fixture_populates_data -v` passes
  - [ ] Fixture data covers multiple statuses, dates, workloads, providers

  **QA Scenarios**:
  ```
  Scenario: Fixture populates expected data
    Tool: Bash
    Preconditions: .venv active
    Steps:
      1. Run: cd /app && python -m pytest tests/test_queries.py -v --tb=short 2>&1 | head -20
    Expected Result: At least one test passes verifying fixture data
    Evidence: .sisyphus/evidence/task-2-fixture-test.txt

  Scenario: Query fixture has data for all query types
    Tool: Bash
    Preconditions: Same
    Steps:
      1. Run a python script that uses the fixture, queries the session, and asserts: 5+ benchmarks, 2+ models, 2+ machines, 10+ results
    Expected Result: All assertions pass
    Evidence: .sisyphus/evidence/task-2-fixture-data.txt
  ```

  **Commit**: YES (groups with Task 3 or separate)
  - Message: `test(db): add test fixtures and skeleton for query tests`
  - Files: `tests/test_queries.py`

- [x] 3. Implement `list_benchmarks` (TDD)

  **What to do**:
  - **RED**: Write tests in `tests/test_queries.py` in a `TestListBenchmarks` class:
    - `test_list_all` — no filters returns all benchmarks (verify count matches fixture)
    - `test_filter_by_model` — filter by model_name returns only matching benchmarks
    - `test_filter_by_provider` — filter by provider_name
    - `test_filter_by_machine` — filter by machine_hostname
    - `test_filter_by_date_range` — filter by date_start/date_end
    - `test_filter_by_status` — filter by benchmark status
    - `test_multiple_filters` — combine model + provider + date
    - `test_pagination_offset` — offset skips N records
    - `test_pagination_limit` — limit restricts to N records
    - `test_pagination_total_count` — total_count reflects unfiltered count
    - `test_sort_by_default` — results ordered by started_at DESC
    - `test_sort_by_custom_field` — sort_by + sort_order works (e.g., throughput_tps ASC)
    - `test_empty_result` — filter with no match returns empty list
    - `test_invalid_sort_field` — raises ValueError for invalid sort_by
  - **GREEN**: Implement `list_benchmarks` in `queries.py`:
    ```python
    def list_benchmarks(
        session: Session,
        filters: BenchmarkFilters | None = None,
        sort_by: str = "started_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> PaginatedResult[BenchmarkSummary]:
    ```
    - Build query with SQLAlchemy 2.0 `select(Benchmark).join(Model, Machine)`
    - Apply filters dynamically (WHERE clauses)
    - Apply sorting with `asc()`/`desc()` based on valid sort_by whitelist
    - Apply offset/limit
    - Return `PaginatedResult` with `total_count` from a count query
    - Map to `BenchmarkSummary` dataclass
    - Validate sort_by against whitelist of allowed column names
  - **REFACTOR**: Clean up, ensure clean se

  **Must NOT do**:
  - Do NOT load `results` relationship (avoid N+1 in list view)
  - Do NOT accept arbitrary SQLAlchemy column names for sort_by — use a whitelist
  - Do NOT mutate the session

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple concerns — dynamic filtering, pagination, sorting, validation, ORM queries
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5)
  - **Blocks**: F1-F4
  - **Blocked By**: 1, 2

  **References**:
  - `llm_race/db/models.py:Benchmark` — Full field list and relationships
  - `llm_race/db/models.py:Model` — Model.name, Model.provider_name for joins
  - `llm_race/db/models.py:Machine` — Machine.hostname for joins
  - `llm_race/db/types.py` — BenchmarkSummary, PaginatedResult, BenchmarkFilters dataclasses (created in Task 1)
  - `tests/test_models.py:db_session` — Existing fixture pattern for tests
  - SQLAlchemy 2.0 docs: `select()` style, `where()`, `order_by()`, `limit()`, `offset()`, `count()`

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_queries.py::TestListBenchmarks -v` → all tests pass (12+ tests)
  - [ ] `list_benchmarks(session)` returns `PaginatedResult` with all benchmarks
  - [ ] Filter by model_name works (partial match LIKE)
  - [ ] Filter by provider works (exact match)
  - [ ] Filter by date range works
  - [ ] Pagination offset/limit works
  - [ ] total_count includes unfiltered count
  - [ ] Sorting by multiple fields works
  - [ ] Invalid sort_by raises ValueError

  **QA Scenarios**:
  ```
  Scenario: Happy path — list all benchmarks
    Tool: Bash
    Preconditions: .venv active, fixture data loaded
    Steps:
      1. Create and run a Python script that:
         - Gets a session from init_db
         - Inserts 3 benchmarks
         - Calls list_benchmarks(session)
         - Asserts result.total_count == 3
         - Asserts len(result.items) == 3
         - Asserts result.items[0].model_name is not None (joined)
    Expected Result: All assertions pass, output shows "ALL OK"
    Evidence: .sisyphus/evidence/task-3-list-all.txt

  Scenario: Pagination with offset/limit
    Tool: Bash
    Preconditions: Same, 3 benchmarks in DB
    Steps:
      1. Call list_benchmarks(session, limit=2, offset=0)
      2. Assert len(result.items) == 2
      3. Call with offset=2
      4. Assert len(result.items) == 1
    Expected Result: Pagination correctly restricts results
    Evidence: .sisyphus/evidence/task-3-pagination.txt

  Scenario: Empty filter result
    Tool: Bash
    Preconditions: Same
    Steps:
      1. Call list_benchmarks(session, filters=BenchmarkFilters(model_name="nonexistent"))
      2. Assert len(result.items) == 0
      3. Assert result.total_count == 0
    Expected Result: Returns empty PaginatedResult, no exception
    Evidence: .sisyphus/evidence/task-3-empty.txt
  ```

  **Commit**: YES
  - Message: `feat(db): implement list_benchmarks query`
  - Files: `llm_race/db/queries.py`, `tests/test_queries.py`

- [x] 4. Implement `compare_runs` (TDD)

  **What to do**:
  - **RED**: Write tests in `TestCompareRuns` class:
    - `test_compare_two_runs` — pass 2 valid run_ids, verify returns 2 items
    - `test_compare_three_runs` — pass 3 valid run_ids
    - `test_compare_four_runs` — pass 4 valid run_ids
    - `test_compare_includes_result_data` — each BenchmarkDetail includes results list
    - `test_compare_rejects_single_run` — ValueError if < 2 run_ids
    - `test_compare_rejects_five_runs` — ValueError if > 4 run_ids
    - `test_compare_invalid_run_id` — returns detail with empty metrics? or raises?
    - `test_compare_fields_match_benchmark_summary` — verify BenchmarkDetail includes all BenchmarkSummary fields + results
  - **GREEN**: Implement `compare_runs` in `queries.py`:
    ```python
    def compare_runs(
        session: Session,
        run_ids: list[str],
    ) -> list[BenchmarkDetail]:
    ```
    - Validate: 2 <= len(run_ids) <= 4, raise ValueError otherwise
    - Query benchmarks by run_id using `select(Benchmark).where(Benchmark.run_id.in_(run_ids))`
    - Eagerly load .model, .machine, .results relationships
    - Map to `BenchmarkDetail` including nested `ResultRow` list
    - Preserve order matching run_ids input
  - **REFACTOR**: Clean up, extract mapping logic if repeated

  **Must NOT do**:
  - Do NOT return benchmarks for run_ids that don't exist (skip, don't error)
  - Do NOT load extra relationships beyond model, machine, results

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Input validation, eager loading, nested mapping
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 5)
  - **Blocks**: F1-F4
  - **Blocked By**: 1, 2

  **References**:
  - `llm_race/db/models.py:Benchmark` — run_id field, relationships to model/machine/results
  - `llm_race/db/models.py:Result` — per-request data columns
  - `llm_race/db/types.py` — BenchmarkDetail, ResultRow dataclasses
  - `llm_race/db/queries.py` — pattern established by list_benchmarks
  - SQLAlchemy `selectinload()` for eager loading relationships

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_queries.py::TestCompareRuns -v` → all tests pass (6+ tests)
  - [ ] compare_runs with 2 valid run_ids returns 2 items with nested results
  - [ ] compare_runs with 1 run_id raises ValueError
  - [ ] compare_runs with 5 run_ids raises ValueError
  - [ ] Return preserves input order

  **QA Scenarios**:
  ```
  Scenario: Compare 2 runs successfully
    Tool: Bash
    Preconditions: Fixture with benchmarks having known run_ids
    Steps:
      1. Create test script:
         - Insert 2 benchmarks with known run_ids
         - For each benchmark, insert 2 Result rows
         - Call compare_runs(session, ["run-1", "run-2"])
         - Assert len(result) == 2
         - Assert result[0].run_id == "run-1"
         - Assert len(result[0].results) == 2
         - Assert result[0].results[0].request_id is not None
    Expected Result: All assertions pass
    Evidence: .sisyphus/evidence/task-4-compare-two.txt

  Scenario: Validation rejects invalid count
    Tool: Bash
    Preconditions: Same
    Steps:
      1. Call compare_runs(session, ["only-one"])
      2. Catch ValueError
      3. Call compare_runs(session, ["a", "b", "c", "d", "e"])
      4. Catch ValueError
    Expected Result: ValueError raised in both cases
    Evidence: .sisyphus/evidence/task-4-validation.txt
  ```

  **Commit**: YES
  - Message: `feat(db): implement compare_runs query`
  - Files: `llm_race/db/queries.py`, `tests/test_queries.py`

- [x] 5. Implement `timeseries` (TDD)

  **What to do**:
  - **RED**: Write tests in `TestTimeseries` class:
    - `test_timeseries_benchmark_level` — returns points with per-benchmark metrics
    - `test_timeseries_result_level` — returns points with per-Result metrics
    - `test_timeseries_filter_by_model` — only returns benchmarks for model
    - `test_timeseries_filter_by_provider` — only returns for provider
    - `test_timeseries_filter_by_date` — respects date_start/date_end
    - `test_timeseries_metric_throughput_tps` — metric column is selected
    - `test_timeseries_metric_ttft_p99` — metric column is selected
    - `test_timeseries_empty_range` — empty date range returns []
    - `test_timeseries_sort_by_date` — results ordered by date ASC
  - **GREEN**: Implement `timeseries`:
    ```python
    def timeseries(
        session: Session,
        model: str | None = None,
        provider: str | None = None,
        metric: str = "throughput_tps",
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        level: str = "benchmark",  # "benchmark" | "result"
    ) -> list[TimeseriesPoint]:
    ```
    - Build query on Benchmark (level=benchmark) or Result (level=result)
    - Join through Model for model_name/provider_name filtering
    - Filter by model name (LIKE/contains), provider (exact), date range
    - Select the metric column + date column
    - Map to `TimeseriesPoint` dataclass
    - Order by date ASC
    - Validate metric against whitelist of allowed column names
  - **REFACTOR**: Clean up shared filter logic

  **Must NOT do**:
  - Do NOT allow arbitrary column names for metric — use whitelist
  - Do NOT fetch unnecessary columns (select only metric + date)
  - Do NOT do client-side filtering — all filtering in SQL

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Dual-level query, dynamic column selection, cross-model joins
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4)
  - **Blocks**: F1-F4
  - **Blocked By**: 1, 2

  **References**:
  - `llm_race/db/models.py:Benchmark` — Metric columns: throughput_tps, e2e_*_ms, ttft_*_ms, itl_*_ms
  - `llm_race/db/models.py:Result` — Metric columns: ttft_ms, e2e_latency_ms, tokens_per_second, itl_mean
  - `llm_race/db/models.py:Model` — For filtering by model/provider
  - `llm_race/db/types.py` — TimeseriesPoint dataclass
  - SQLAlchemy `getattr(model, column_name)` for dynamic column access

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_queries.py::TestTimeseries -v` → all tests pass (7+ tests)
  - [ ] timeseries with metric="throughput_tps" returns correct values
  - [ ] timeseries with level="result" returns per-Result data points
  - [ ] Date filtering works correctly
  - [ ] Empty date range returns []
  - [ ] Invalid metric raises ValueError

  **QA Scenarios**:
  ```
  Scenario: Timeseries at benchmark level
    Tool: Bash
    Preconditions: Fixture with 3 benchmarks over different dates
    Steps:
      1. Create test script:
         - Insert 3 benchmarks with different started_at dates and throughput_tps values
         - Call timeseries(session, metric="throughput_tps", level="benchmark")
         - Assert len(points) == 3
         - Assert points[0].metric_value == throughput_tps of first benchmark
         - Assert points are ordered by date ASC
    Expected Result: 3 data points, correctly ordered
    Evidence: .sisyphus/evidence/task-5-timeseries-benchmark.txt

  Scenario: Timeseries with date filter
    Tool: Bash
    Preconditions: Benchmarks before and after a cutoff
    Steps:
      1. Call timeseries(session, date_start=some_date, date_end=some_other_date)
      2. Assert all returned points are within the date range
    Expected Result: Only points within range returned
    Evidence: .sisyphus/evidence/task-5-timeseries-dates.txt

  Scenario: Empty date range
    Tool: Bash
    Preconditions: Same
    Steps:
      1. Call timeseries(session, date_start=datetime(2099, 1, 1))
      2. Assert points == []
    Expected Result: Empty list
    Evidence: .sisyphus/evidence/task-5-timeseries-empty.txt

  Scenario: Invalid metric
    Tool: Bash
    Preconditions: Same
    Steps:
      1. Call timeseries(session, metric="not_a_column")
      2. Assert ValueError is raised
    Expected Result: ValueError
    Evidence: .sisyphus/evidence/task-5-timeseries-invalid-metric.txt
  ```

  **Commit**: YES
  - Message: `feat(db): implement timeseries query`
  - Files: `llm_race/db/queries.py`, `tests/test_queries.py`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run pytest). For each "Must NOT Have": search for forbidden patterns (caching, CSV export, web endpoints). Check evidence files exist in .sisyphus/evidence/.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/test_queries.py -v`. Review for: no raw SQLAlchemy rows exposed, proper type hints, dataclass usage, N+1 query prevention. Check AI slop patterns.
  Output: `Tests [N pass/N fail] | Quality [PASS/ISSUES] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task. Test cross-function integration (e.g., use list_benchmarks to get run_ids, then pass to compare_runs). Test edge cases: empty filters, invalid run_ids, no data in date range.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything built, nothing beyond spec. Check "Must NOT do" compliance. Detect cross-task contamination.
  Output: `Tasks [N/N compliant] | VERDICT`

---

## Commit Strategy

- **Task 1**: `feat(db): add query result dataclasses` — `llm_race/db/types.py`, `llm_race/db/__init__.py`
- **Task 2**: `test(db): add test fixtures for queries` — `tests/test_queries.py`
- **Task 3**: `feat(db): implement list_benchmarks query` — `llm_race/db/queries.py`, `tests/test_queries.py`
- **Task 4**: `feat(db): implement compare_runs query` — `llm_race/db/queries.py`, `tests/test_queries.py`
- **Task 5**: `feat(db): implement timeseries query` — `llm_race/db/queries.py`, `tests/test_queries.py`

---

## Success Criteria

### Verification Commands
```bash
cd /app && python -m pytest tests/test_queries.py -v
# Expected: 15+ tests, all PASS
```

### Final Checklist
- [x] All 3 query functions implemented and tested
- [x] All dataclasses defined and importable
- [x] Pagination returns total_count
- [x] compare_runs validates 2-4 run_ids
- [x] timeseries supports both Benchmark and Result levels
- [x] All QA evidence files exist in `.sisyphus/evidence/`
