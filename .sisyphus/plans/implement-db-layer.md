# Implement DB Layer: SQLAlchemy Models + Schema + Tests

## TL;DR

> **Quick Summary**: Implement the 4 SQLAlchemy ORM models (Model, Machine, Benchmark, Result) with relationships, matching raw SQL schema, database initialization function, and unit tests — completing the stub database layer for the llm-race benchmarking tool.
>
> **Deliverables**:
> - `llm_race/db/models.py` — Full SQLAlchemy 2.0 ORM models with relationships
> - `llm_race/db/schema.sql` — Raw SQLite schema mirroring the models
> - `tests/test_models.py` — Unit tests for model creation, relationships, constraints
> - Updated `llm_race/db/__init__.py` — Re-exports for convenience
>
> **Estimated Effort**: Quick (2-4 files, well-scoped)
> **Parallel Execution**: NO — sequential (tasks depend on each other)
> **Critical Path**: models.py → schema.sql → tests

---

## Context

### Original Request
[GitHub Issue #1](https://github.com/danieltvela/llm-race/issues/1): Implement the DB layer with SQLAlchemy ORM models and raw SQL schema for the llm-race benchmarking tool.

### Interview Summary
**Key Discussions**:
- **Tests**: YES — include unit tests with pytest
- **Migrations**: NO — only `schema.sql` as reference, no Alembic
- **init_db() location**: Inside `models.py` for discoverability
- SQLAlchemy >= 2.0 already in `requirements.txt` — no changes needed

**Research Findings**:
- `config/__init__.py` already defines `DB_PATH = DATA_DIR / "benchmarks.db"`
- Runner (`runner.py`) has `RequestMetrics` and `ScenarioResult` dataclasses that closely map to what the Result model needs
- Existing code uses Python 3.11+ modern typing (`float | None`), numpy for stats, logging over print
- No existing tests — first test file in the project

### Metis Review
**Identified Gaps** (addressed):
- **Result model structure**: Stored as per-request metrics (matching `RequestMetrics`), not aggregated — gives maximum query flexibility
- **Machine identification**: `hostname` as unique natural key with unique constraint
- **Cost per token**: Stored as nullable `float` — provider-reported when available
- **Percentile fields**: Issue asks for p50/p90/p99 (not p95 as the runner currently computes) — Result model uses p90 per issue spec
- **Benchmark aggregated stats**: Included directly in Benchmark model (total/successful/failed requests, throughput, wall clock) for query convenience

---

## Work Objectives

### Core Objective
Create the database layer so the benchmark runner can persist results to SQLite instead of CSV/JSON files, and the web viewer can query historical data.

### Concrete Deliverables
- [ ] `llm_race/db/models.py` — 4 SQLAlchemy models with relationships + init_db()
- [ ] `llm_race/db/schema.sql` — Raw SQLite DDL matching the models
- [ ] `tests/test_models.py` — Unit tests
- [ ] `llm_race/db/__init__.py` — Updated with model exports

### Definition of Done
- [ ] `python -c "from llm_race.db.models import Model, Machine, Benchmark, Result, init_db; print('OK')"` succeeds
- [ ] `pytest tests/test_models.py -v` passes (all tests green)
- [ ] `schema.sql` is valid SQLite DDL that creates 4 tables with FKs and constraints

### Must Have
- 4 models with proper SQLAlchemy relationships (Model → Benchmark, Machine → Benchmark, Benchmark → Result)
- `init_db()` creates tables and returns engine + session factory
- All timestamps in UTC (`datetime.utcnow()` default)
- Type hints everywhere (modern `float | None` style)
- Logging via `logging.getLogger(__name__)` — no print statements
- UUID4 `run_id` on Benchmark model
- Unique constraints: Model(name, version, quantization, provider), Machine(hostname)

### Must NOT Have (Guardrails)
- Do NOT modify `queries.py` — that's for a separate issue
- Do NOT touch runner.py, cli.py, or web/ files — out of scope
- Do NOT add Alembic or migration tooling
- Do NOT add seed data or fixtures
- Do NOT modify `requirements.txt` (sqlalchemy already present)
- Do NOT store raw prompt/response text — only hashes and sizes

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES — pytest in requirements.txt
- **Automated tests**: YES (TDD-lite — tests verify after implementation)
- **Framework**: pytest
- **Test location**: `tests/test_models.py`

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Python module/library**: Use Bash — import modules, call functions, inspect objects
- **SQL schema**: Use Bash — validate via `sqlite3` CLI
- **Tests**: Run `pytest tests/test_models.py -v`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Sequential — each builds on previous):
├── Task 1: models.py — SQLAlchemy models [quick]
├── Task 2: schema.sql — Raw SQLite DDL [quick]
└── Task 3: tests/test_models.py — Unit tests [quick]
```

**No parallelism possible** — each task depends on the previous one (tests need models, schema needs to match models).

---

## TODOs

- [x] 1. Implement SQLAlchemy models in `llm_race/db/models.py`

  **What to do**:
  Implement 4 SQLAlchemy 2.0 ORM models using `DeclarativeBase` + `mapped_column` syntax:

  **Model** table:
  - `id: int` — PK, autoincrement
  - `name: str` — model name (e.g. "Qwen3.6-35B-A3B-FP8")
  - `version: str | None` — model version
  - `quantization: str | None` — quantization format (FP8, INT4, AWQ, GGUF Q4_K_M, etc.)
  - `provider_name: str` — provider name (openai, anthropic, vllm, ollama, etc.)
  - `context_window: int | None` — max context window in tokens
  - `created_at: datetime` — defaults to `datetime.utcnow()`
  - `__table_args__`: UniqueConstraint on (`name`, `version`, `quantization`, `provider_name`)
  - Relationship: `benchmarks: list[Benchmark]`

  **Machine** table:
  - `id: int` — PK, autoincrement
  - `hostname: str` — machine hostname (unique natural key)
  - `cpu: str | None` — CPU model/description
  - `gpu: str | None` — GPU model name
  - `gpu_count: int | None` — number of GPUs
  - `ram_gb: float | None` — total RAM in GB
  - `os: str | None` — operating system name
  - `os_version: str | None` — OS version
  - `driver_version: str | None` — GPU driver version (e.g. CUDA 12.1)
  - `python_version: str | None` — Python version used
  - `created_at: datetime` — defaults to `datetime.utcnow()`
  - `__table_args__`: UniqueConstraint on (`hostname`)
  - Relationship: `benchmarks: list[Benchmark]`

  **Benchmark** table:
  - `id: int` — PK, autoincrement
  - `run_id: str` — UUID4 string (unique identifier for this run), use `default=uuid4_string`
  - `model_id: int` — FK → `models.id`
  - `machine_id: int` — FK → `machines.id`
  - `workload_profile: str` — workload profile name (single-user, chat, multi-agent, high-throughput, stress)
  - `prompt_size: str` — size category (tiny, small, medium, large, max)
  - `prompt_token_count: int | None` — actual prompt length in tokens
  - `prompt_hash: str | None` — SHA256 hash of the prompt text
  - `prompt_text_size: int | None` — size of prompt text in bytes
  - `concurrency: int` — concurrency level used
  - `max_tokens: int` — max completion tokens configured
  - `temperature: float` — sampling temperature
  - `top_p: float` — nucleus sampling threshold
  - `started_at: datetime` — UTC timestamp when the run started
  - `completed_at: datetime | None` — UTC timestamp when the run completed
  - `wall_clock_seconds: float | None` — total wall clock time
  - `total_requests: int` — total requests attempted
  - `successful_requests: int` — successful requests count
  - `failed_requests: int` — failed requests count
  - `throughput_rps: float | None` — requests per second
  - `throughput_tps: float | None` — tokens per second (output)
  - `e2e_mean_ms: float | None` — mean end-to-end latency
  - `e2e_p50_ms: float | None` — median e2e latency
  - `e2e_p90_ms: float | None` — p90 e2e latency
  - `e2e_p99_ms: float | None` — p99 e2e latency
  - `ttft_mean_ms: float | None` — mean time-to-first-token
  - `ttft_p50_ms: float | None` — median TTFT
  - `ttft_p90_ms: float | None` — p90 TTFT
  - `ttft_p99_ms: float | None` — p99 TTFT
  - `itl_mean_ms: float | None` — mean inter-token latency
  - `itl_p50_ms: float | None` — median ITL
  - `itl_p90_ms: float | None` — p90 ITL
  - `itl_p99_ms: float | None` — p99 ITL
  - `cost_per_token: float | None` — cost per token in USD (optional, provider-reported)
  - `status: str` — run status (running, completed, failed)
  - `error_message: str | None` — error message if failed
  - `created_at: datetime` — defaults to `datetime.utcnow()`
  - Relationships: `model: Model`, `machine: Machine`, `results: list[Result]`
  - Index on `run_id` for fast lookups

  **Result** table:
  - `id: int` — PK, autoincrement
  - `benchmark_id: int` — FK → `benchmarks.id`
  - `request_id: int` — per-request identifier within the benchmark (0-indexed)
  - `status: str` — request status (success, error)
  - `error_message: str | None` — error details if failed
  - `ttft_ms: float | None` — time-to-first-token in ms
  - `e2e_latency_ms: float | None` — end-to-end latency in ms
  - `prompt_tokens: int` — prompt token count
  - `completion_tokens: int` — completion token count
  - `total_tokens: int` — total tokens (prompt + completion)
  - `tokens_per_second: float | None` — output tokens per second
  - `itl_mean: float | None` — mean inter-token latency
  - `itl_p50: float | None` — median ITL
  - `itl_p90: float | None` — p90 ITL
  - `itl_p99: float | None` — p99 ITL
  - `cost_per_token: float | None` — cost per token in USD (optional)
  - `created_at: datetime` — defaults to `datetime.utcnow()`
  - Relationship: `benchmark: Benchmark`
  - UniqueConstraint on (`benchmark_id`, `request_id`)

  **init_db()** function:
  ```python
  def init_db(db_path: str | Path = DB_PATH) -> tuple[Engine, sessionmaker[Session]]:
      """Initialize the database, create tables if they don't exist.
      
      Returns:
          A tuple of (engine, session_factory).
      """
      engine = create_engine(f"sqlite:///{db_path}", echo=False)
      Base.metadata.create_all(engine)
      session_factory = sessionmaker(bind=engine)
      logger.info("Database initialized at %s", db_path)
      return engine, session_factory
  ```

  **UUID4 helper** for Benchmark.run_id default:
  ```python
  import uuid
  def uuid4_string() -> str:
      return str(uuid.uuid4())
  ```

  **Logging setup**:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```

  **Must NOT do**:
  - Do NOT add Any/type:ignore — use proper type hints
  - Do NOT use legacy `Column()`, `Integer`, `String` syntax — use SQLAlchemy 2.0 `mapped_column()` style
  - Do NOT add print() statements — use logging
  - Do NOT import from queries.py or modify other db modules (except __init__.py for re-exports)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file implementation with well-defined spec, straightforward ORM models
  - **Skills**: none needed
  - **Skills Evaluated but Omitted**:
    - All skills — pure Python/SQLAlchemy code, no special domain

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Task 1)
  - **Blocks**: Task 2 (schema.sql), Task 3 (tests)
  - **Blocked By**: None

  **References**:
  - `llm_race/config/__init__.py:11` — `DB_PATH = DATA_DIR / "benchmarks.db"` — path to use in init_db()
  - `llm_race/bench/runner.py:26-42` — `RequestMetrics` dataclass — maps to Result model fields
  - `llm_race/bench/runner.py:44-68` — `ScenarioResult` dataclass — maps to Benchmark aggregated fields
  - `llm_race/config/base.py:16-32` — `StreamResult` dataclass — additional metrics that feed into Runner
  - `AGENTS.md` — Project conventions (type hints, logging, UTC timestamps, etc.)
  - SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/orm/quickstart.html — declarative base + mapped_column pattern

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Models import successfully and have correct structure
    Tool: Bash
    Preconditions: models.py written, cwd = project root
    Steps:
      1. Run: python -c "from llm_race.db.models import Model, Machine, Benchmark, Result, init_db; print('OK')"
    Expected Result: Output contains "OK"
    Evidence: .sisyphus/evidence/task-1-imports.txt

  Scenario: init_db() creates tables in a temp database
    Tool: Bash
    Preconditions: models.py written
    Steps:
      1. Run: python -c "
        from llm_race.db.models import init_db
        from pathlib import Path
        import tempfile, os
        tmp = Path(tempfile.mktemp(suffix='.db'))
        engine, sf = init_db(tmp)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f'Tables: {sorted(tables)}')
        os.unlink(tmp)
      "
    Expected Result: Tables list contains ['benchmarks', 'machines', 'models', 'results']
    Evidence: .sisyphus/evidence/task-1-tables.txt

  Scenario: Model creation with relationships works
    Tool: Bash
    Preconditions: models.py written
    Steps:
      1. Run: python -c "
        from llm_race.db.models import Model, Machine, Benchmark, Result, init_db
        import tempfile, os
        from pathlib import Path
        tmp = Path(tempfile.mktemp(suffix='.db'))
        engine, sf = init_db(tmp)
        session = sf()
        m = Model(name='test-model', version='1.0', quantization='FP8', provider_name='vllm', context_window=4096)
        machine = Machine(hostname='test-host')
        session.add_all([m, machine])
        session.commit()
        b = Benchmark(
            run_id='00000000-0000-0000-0000-000000000001',
            model_id=m.id,
            machine_id=machine.id,
            workload_profile='single-user',
            prompt_size='medium',
            concurrency=1,
            max_tokens=256,
            temperature=0.0,
            top_p=1.0,
            started_at=__import__('datetime').datetime.utcnow(),
            total_requests=1,
            successful_requests=1,
            failed_requests=0,
            status='completed'
        )
        session.add(b)
        session.commit()
        r = Result(
            benchmark_id=b.id,
            request_id=0,
            status='success',
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
        )
        session.add(r)
        session.commit()
        # verify relationships
        assert b.model.name == 'test-model'
        assert b.machine.hostname == 'test-host'
        assert len(b.results) == 1
        assert b.results[0].completion_tokens == 100
        print('Relationships OK')
        os.unlink(tmp)
      "
    Expected Result: Output contains "Relationships OK"
    Evidence: .sisyphus/evidence/task-1-relationships.txt

  Scenario: Unique constraints work
    Tool: Bash
    Preconditions: models.py written
    Steps:
      1. Run: python -c "
        from llm_race.db.models import Model, Machine, init_db
        import tempfile, os
        from pathlib import Path
        from sqlalchemy.exc import IntegrityError
        tmp = Path(tempfile.mktemp(suffix='.db'))
        engine, sf = init_db(tmp)
        session = sf()
        m1 = Model(name='dup', version='1', quantization='FP8', provider_name='test')
        session.add(m1)
        session.commit()
        m2 = Model(name='dup', version='1', quantization='FP8', provider_name='test')
        session.add(m2)
        try:
            session.commit()
            print('ERROR: No constraint violation')
        except IntegrityError:
            session.rollback()
            print('Unique constraint OK')
        os.unlink(tmp)
      "
    Expected Result: Output contains "Unique constraint OK"
    Evidence: .sisyphus/evidence/task-1-unique-constraint.txt
  ```

  **Commit**: YES
  - Message: `feat(db): implement SQLAlchemy ORM models with relationships`
  - Files:
    - `llm_race/db/models.py`
    - `llm_race/db/__init__.py`
  - Pre-commit: `python -c "from llm_race.db.models import Model, Machine, Benchmark, Result, init_db; print('OK')"`

---

- [x] 2. Create raw SQLite schema in `llm_race/db/schema.sql`

  **What to do**:
  Write a raw SQLite DDL script that mirrors the SQLAlchemy models exactly. Must include:
  - `CREATE TABLE IF NOT EXISTS` statements for all 4 tables
  - Column definitions matching Python model types (INTEGER, TEXT, REAL, DATETIME)
  - NOT NULL constraints where applicable
  - PRIMARY KEY definitions
  - FOREIGN KEY constraints with ON DELETE CASCADE
  - UNIQUE constraints matching Python model
  - CREATE INDEX on `benchmarks.run_id`
  - Proper SQLite type affinity

  **Must NOT do**:
  - Do NOT include INSERT/DELETE/UPDATE statements
  - Do NOT include PRAGMA or ATTACH statements
  - Do NOT include SQLite-specific features that differ from the SQLAlchemy models
  - Do NOT add docstrings or comments beyond the initial header

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small, well-defined DDL file with clear structure
  - **Skills**: none needed
  - **Skills Evaluated but Omitted**:
    - All skills — pure SQL, no special domain

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on models.py)
  - **Parallel Group**: Sequential (Task 2)
  - **Blocks**: Task 3 (tests)
  - **Blocked By**: Task 1 (models.py)

  **References**:
  - `llm_race/db/models.py` — The source of truth for all column names, types, constraints, and relationships
  - SQLite CREATE TABLE syntax: https://www.sqlite.org/lang_createtable.html
  - SQLite FOREIGN KEY: https://www.sqlite.org/foreignkeys.html

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: schema.sql is valid SQLite and matches model expectations
    Tool: Bash
    Preconditions: schema.sql + models.py both written
    Steps:
      1. Run: sqlite3 :memory: < llm_race/db/schema.sql
    Expected Result: Exit code 0, no errors
    Evidence: .sisyphus/evidence/task-2-valid-sql.txt

  Scenario: Tables created from schema.sql match expected structure
    Tool: Bash
    Preconditions: schema.sql written
    Steps:
      1. Run: sqlite3 :memory: "
          .read llm_race/db/schema.sql
          .tables
        "
    Expected Result: Output contains "models", "machines", "benchmarks", "results"
    Evidence: .sisyphus/evidence/task-2-tables.txt

  Scenario: schema.sql creates same tables as SQLAlchemy models
    Tool: Bash
    Preconditions: schema.sql + models.py written
    Steps:
      1. Run: python -c "
        from llm_race.db.models import Base, init_db
        import tempfile, os
        from pathlib import Path
        import sqlite3
        # Create DB via SQLAlchemy
        algo_path = Path(tempfile.mktemp(suffix='.db'))
        engine, _ = init_db(algo_path)
        from sqlalchemy import inspect
        algo_tables = set(inspect(engine).get_table_names())
        engine.dispose()
        # Create DB via schema.sql
        sql_path = Path(tempfile.mktemp(suffix='.db'))
        conn = sqlite3.connect(str(sql_path))
        with open('llm_race/db/schema.sql') as f:
            conn.executescript(f.read())
        cursor = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'\")
        sql_tables = set(row[0] for row in cursor.fetchall())
        conn.close()
        os.unlink(algo_path)
        os.unlink(sql_path)
        if algo_tables == sql_tables:
            print(f'Tables match: {sorted(algo_tables)}')
        else:
            print(f'MISMATCH: algo={algo_tables} sql={sql_tables}')
      "
    Expected Result: "Tables match" with all 4 table names
    Evidence: .sisyphus/evidence/task-2-schema-match.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `feat(db): add raw SQLite schema mirroring ORM models`
  - Files:
    - `llm_race/db/schema.sql`

---

- [x] 3. Write unit tests in `tests/test_models.py`

  **What to do**:
  Create a `tests/` directory at project root (if not exists) and write comprehensive tests.

  Test file structure:
  ```python
  """Unit tests for the database models."""
  
  from __future__ import annotations
  
  import logging
  import os
  import tempfile
  import uuid
  from pathlib import Path
  from datetime import datetime
  
  import pytest
  from sqlalchemy import create_engine, inspect
  from sqlalchemy.orm import Session, sessionmaker
  
  from llm_race.db.models import Model, Machine, Benchmark, Result, Base, init_db
  from llm_race.config import DB_PATH  # or not — we use temp db
  ```

  Tests to write:

  1. **test_init_db_creates_tables** — Verify all 4 tables created
  2. **test_model_create** — Create a Model and verify fields
  3. **test_machine_create** — Create a Machine and verify fields
  4. **test_benchmark_create** — Create a Benchmark with FK to Model and Machine
  5. **test_result_create** — Create a Result with FK to Benchmark
  6. **test_model_unique_constraint** — Verify duplicate Model raises IntegrityError
  7. **test_machine_unique_constraint** — Verify duplicate hostname raises IntegrityError
  8. **test_result_unique_constraint** — Verify duplicate (benchmark_id, request_id) raises IntegrityError
  9. **test_model_benchmark_relationship** — Verify Model.benchmarks backref
  10. **test_machine_benchmark_relationship** — Verify Machine.benchmarks backref
  11. **test_benchmark_result_relationship** — Verify Benchmark.results backref
  12. **test_benchmark_run_id_uuid** — Verify run_id is a valid UUID4
  13. **test_cascade_delete** — Verify deleting a Model cascades to benchmarks (optional, depends on cascade config)

  Use temp files for the database so tests don't pollute each other or the real DB:
  ```python
  @pytest.fixture
  def db_session():
      tmp = Path(tempfile.mktemp(suffix=".db"))
      engine, sf = init_db(tmp)
      session = sf()
      yield session
      session.close()
      engine.dispose()
      os.unlink(tmp)
  ```

  Add `__init__.py` to `tests/` directory:
  ```python
  """Tests for llm-race."""
  ```

  **Must NOT do**:
  - Do NOT test the real database at `data/benchmarks.db` — use temp files
  - Do NOT depend on an LLM endpoint being available
  - Do NOT use print() — use pytest assertions
  - Do NOT write integration tests (no need for real provider)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward pytest unit tests with clear structure
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on models.py + schema.sql)
  - **Parallel Group**: Sequential (Task 3)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 1 (models.py), Task 2 (schema.sql)

  **References**:
  - `llm_race/db/models.py` — All model definitions to test against
  - `llm_race/db/schema.sql` — Schema for reference
  - pytest docs: https://docs.pytest.org/en/stable/ — fixture patterns, temp db approach
  - `llm_race/bench/runner.py` — Shows how models are actually used at runtime (context for good test data)

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: All tests pass
    Tool: Bash
    Preconditions: tests/test_models.py written, cwd = project root
    Steps:
      1. Run: pip install -e . 2>&1 | tail -1 || python -m pip install -e . 2>&1 | tail -1
      2. Run: python -m pytest tests/test_models.py -v 2>&1
    Expected Result: All tests PASS (no FAILURES, no ERRORS)
    Evidence: .sisyphus/evidence/task-3-pytest-pass.txt

  Scenario: Test coverage includes constraint violations
    Tool: Bash
    Preconditions: tests written
    Steps:
      1. Run: grep -c "IntegrityError" tests/test_models.py
    Expected Result: Output >= 3 (tests for model, machine, and result unique constraints)
    Evidence: .sisyphus/evidence/task-3-constraint-tests.txt

  Scenario: Test coverage includes relationships
    Tool: Bash
    Preconditions: tests written
    Steps:
      1. Run: grep -c "relationship\|\.benchmarks\|\.results\|\.model\|\.machine" tests/test_models.py
    Expected Result: Output >= 3 (tests verify backrefs work)
    Evidence: .sisyphus/evidence/task-3-relationship-tests.txt
  ```

  **Commit**: YES (groups with Task 1, 2)
  - Message: `test(db): add unit tests for ORM models`
  - Files:
    - `tests/test_models.py`
    - `tests/__init__.py`
  - Pre-commit: `python -m pytest tests/test_models.py -v`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -c "from llm_race.db.models import *"` + `python -m pytest tests/test_models.py -v`. Review all changed files for: type hints consistency, logging over print, unused imports, SQLAlchemy 2.0 style compliance.
  Output: `Import [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task. Test cross-task integration (models + schema match, tests pass). Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built (no query changes, no runner changes, no web changes).
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **1 + 2 + 3**: `feat(db): implement SQLAlchemy ORM models with raw schema and tests` — `llm_race/db/models.py`, `llm_race/db/__init__.py`, `llm_race/db/schema.sql`, `tests/test_models.py`, `tests/__init__.py`

---

## Success Criteria

### Verification Commands
```bash
python -c "from llm_race.db.models import Model, Machine, Benchmark, Result, init_db; print('OK')"
# Expected: OK

python -m pytest tests/test_models.py -v
# Expected: All tests PASS (≥10 tests)

sqlite3 :memory: < llm_race/db/schema.sql
# Expected: exit code 0

python -c "
from llm_race.db.models import init_db
import tempfile, os
from pathlib import Path
engine, _ = init_db(Path(tempfile.mktemp(suffix='.db')))
from sqlalchemy import inspect
tables = inspect(engine).get_table_names()
print(sorted(tables))
os.unlink(engine.url.database)
"
# Expected: ['benchmarks', 'machines', 'models', 'results']
```

### Final Checklist
- [ ] All 4 models implemented with relationships
- [ ] schema.sql mirrors models exactly
- [ ] init_db() creates tables on first call
- [ ] All ≥10 tests pass
- [ ] UUID4 run_id on Benchmark
- [ ] Unique constraints on Model(name+version+quantization+provider) and Machine(hostname)
- [ ] Timestamps use UTC, types match conventions (ints for tokens, floats for latency)
- [ ] No raw prompt/response text stored
- [ ] No print statements — logging used throughout
- [ ] No modifications to queries.py, runner.py, cli.py, or web/
