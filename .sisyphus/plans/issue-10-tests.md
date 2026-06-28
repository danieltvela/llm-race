# Issue #10 — Unit tests for benchmark utilities and queries

## TL;DR

> **Quick Summary**: Add 3 missing test files for utility modules in the llm-race project — timing utilities, prompt generation, and reporter output formatting. Most of the original issue (#10) was already completed in prior work (DB queries: 31 tests, providers: 37 tests). This covers the remaining gap.
>
> **Deliverables**:
> - `tests/test_timing.py` — 10+ tests for `compute_latency_stats`, `compute_itl_stats`
> - `tests/test_bench_prompts.py` — 6+ tests for `generate_prompt`
> - `tests/test_reporter.py` — 10+ tests for `format_table`, `save_csv`, `save_json`
>
> **Estimated Effort**: Quick (1 wave + final wave)
> **Parallel Execution**: YES — all 3 tasks independent
> **Critical Path**: T1 → F1-F3 (all in parallel)

---

## Context

### Original Request
Issue #10: Add unit tests for benchmark utility functions and database queries.

### Key Adjustments from Original Issue
The issue was written early in the project. Many parts are now already covered:
- `tests/test_queries.py` → **31 tests** already exist (in-memory SQLite, list_benchmarks/compare_runs/timeseries)
- `tests/test_providers.py` → **37 tests** already exist (mock streaming)
- `tests/conftest.py` → already exists with `_mock_monotonic` fixture
- `tests/__init__.py` → already exists

The prompt generation module lives at `llm_race/bench/prompts.py` (not `utils/prompts.py` as originally assumed). Test file named `test_bench_prompts.py` to match module location.

### Current Test Coverage
- **163 existing tests** across 9 test files
- Test runner: pytest (in requirements.txt)
- Patterns: plain assertions, `pytest.approx` for floats, `subprocess` for CLI tests
- CI: `python -m pytest`

### Methodology Note
This plan generates test files, which themselves have no automated tests. Instead, every test file task includes **Agent-Executed QA Scenarios** where the executing agent runs the new tests and verifies they pass — this IS the QA for test-generation work.

---

## Work Objectives

### Core Objective
Add unit tests for the 3 remaining untested utility modules, bringing total coverage to 190+ tests without modifying any source code.

### Concrete Deliverables
- `tests/test_timing.py` — tests for `utils/timing.py`
- `tests/test_bench_prompts.py` — tests for `bench/prompts.py`
- `tests/test_reporter.py` — tests for `utils/reporter.py`

### Definition of Done
- [ ] `python -m pytest tests/test_timing.py -v` — all tests pass
- [ ] `python -m pytest tests/test_bench_prompts.py -v` — all tests pass
- [ ] `python -m pytest tests/test_reporter.py -v` — all tests pass
- [ ] `python -m pytest` — 190+ tests pass (no regressions)

### Must Have
- Test empty input edge cases for all functions
- Test single-value edge cases for timing functions
- Test file I/O works correctly for CSV and JSON exports
- Follow existing test patterns (plain assertions, pytest.approx, subprocess if needed)

### Must NOT Have (Guardrails)
- Do NOT modify any source code in `llm_race/` (these are pure test additions)
- Do NOT modify existing test files
- Do NOT add new dependencies
- Do NOT add CI configuration (GitHub Actions, etc.) — out of scope
- Do NOT add integration tests requiring real LLM endpoints
- Do NOT add conftest fixtures that affect other test files (use inline fixtures)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest, conftest.py with _mock_monotonic)
- **Automated tests**: This IS the test work — QA is verifying tests themselves
- **Framework**: pytest (existing)

### QA Policy
Each task MUST include agent-executed QA scenarios that:
1. Run the new test file and verify all tests pass
2. Run the full test suite and verify no regressions
3. Verify specific edge cases were tested by reading the test file

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (ALL independent — start simultaneously):
├── T1: tests/test_timing.py [quick]
├── T2: tests/test_bench_prompts.py [quick]
└── T3: tests/test_reporter.py [quick]

Wave FINAL (After ALL tasks — 3 parallel reviewers):
├── F1: Plan Compliance Audit (oracle)
├── F2: Code Quality + Full Test Suite (unspecified-high)
└── F3: Real Manual QA (unspecified-high)
```

**Critical Path**: T1-T3 → F1-F3 (all parallel)
**Parallel Speedup**: ~90% faster than sequential (all independent)
**Max Concurrent**: 3 in wave 1, 3 in final

---

## TODOs

- [x] 1. Create `tests/test_timing.py` — tests for `utils/timing.py`

  **What to do**:
  - Create `tests/test_timing.py` with tests for both functions in `llm_race/utils/timing.py`:
    - `compute_latency_stats(values: list[float]) -> dict[str, float]`
    - `compute_itl_stats(inter_token_times: list[float]) -> dict[str, float | None]`

  **Test cases**:

  **TestComputeLatencyStats**:
  - `test_normal_values` — list of [10, 20, 30, 40, 50] returns correct mean(30), p50(30), p95(48), p99(49.6), max(50)
  - `test_empty_list` — empty list returns all 0.0
  - `test_single_value` — [42] returns mean=42, p50=42, max=42
  - `test_all_same` — [5,5,5,5,5] returns all 5.0
  - `test_floats` — list of floats returns correct stats

  **TestComputeItlStats**:
  - `test_normal_values` — list of values returns correct dict with float values
  - `test_empty_list` — empty list returns all None (not 0.0)
  - `test_single_value` — single value returns that value for all stats

  **Must NOT do**:
  - Do NOT modify `utils/timing.py`
  - Do NOT add numpy as a test dependency (already present as runtime dep)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple test file creation following existing patterns
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3)
  - **Blocks**: F1, F2, F3
  - **Blocked By**: None

  **References**:
  - `llm_race/utils/timing.py:6-28` — Full source of functions under test
  - `tests/test_workloads.py:27-110` — Existing test patterns (classes, assertions, pytest.approx)
  - `tests/conftest.py:8-18` — Autouse mock_monotonic fixture (won't affect these tests but good to know)

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: All timing tests pass
    Tool: Bash
    Steps:
      1. python3 -m pytest tests/test_timing.py -v 2>&1 | tail -25
    Expected Result: All tests PASSED (10+ tests, 0 failures)
    Evidence: .sisyphus/evidence/task-1-timing-tests.txt

  Scenario: No regressions
    Tool: Bash
    Steps:
      1. python3 -m pytest 2>&1 | tail -5
    Expected Result: 175+ tests pass (includes new tests), no regressions
    Evidence: .sisyphus/evidence/task-1-no-regression.txt

  Scenario: Empty list returns zeros/Nones
    Tool: Bash
    Steps:
      1. python3 -c "from llm_race.utils.timing import compute_latency_stats as s; r=s([]); assert r['mean']==0.0; assert r['max']==0.0; print('OK empty list')"
      2. python3 -c "from llm_race.utils.timing import compute_itl_stats as s; r=s([]); assert r['mean'] is None; print('OK empty itl')"
    Expected Result: Both assertions pass
    Evidence: .sisyphus/evidence/task-1-edge-cases.txt
  ```

  **Evidence to Capture**:
  - [ ] task-1-timing-tests.txt
  - [ ] task-1-no-regression.txt
  - [ ] task-1-edge-cases.txt

  **Commit**: YES (groups with T2, T3)
  - Message: `test(utils): add unit tests for timing utilities`
  - Files: `tests/test_timing.py`

---

- [x] 2. Create `tests/test_bench_prompts.py` — tests for `bench/prompts.py`

  **What to do**:
  - Create `tests/test_bench_prompts.py` with tests for `llm_race/bench/prompts.py`:
    - `generate_prompt(token_approx: int) -> str`

  **Test cases**:

  **TestGeneratePrompt**:
  - `test_returns_string` — returns a non-empty string
  - `test_capitalized_sentences` — sentences start with capital letter, end with period
  - `test_no_placeholder_text` — output doesn't contain Python placeholder markers (no `...object at...`, no repr artifacts)
  - `test_small_token_approx` — token_approx=0 or 1 still returns a valid string (edge case)
  - `test_deterministic_with_seed` — with `random.seed(42)`, same input produces same output (stability test)
  - `test_output_length_scales` — larger token_approx produces longer output

  **Must NOT do**:
  - Do NOT modify `bench/prompts.py`
  - Do NOT add mock/patch for random — test behavior, not implementation
  - Do NOT assert exact output (randomized)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple test file creation
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3)
  - **Blocks**: F1, F2, F3
  - **Blocked By**: None

  **References**:
  - `llm_race/bench/prompts.py:1-24` — Full source of function under test
  - `tests/test_workloads.py:27-110` — Existing test patterns

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: All prompts tests pass
    Tool: Bash
    Steps:
      1. python3 -m pytest tests/test_bench_prompts.py -v 2>&1 | tail -25
    Expected Result: All tests PASSED (6+ tests, 0 failures)
    Evidence: .sisyphus/evidence/task-2-prompt-tests.txt

  Scenario: No regressions
    Tool: Bash
    Steps:
      1. python3 -m pytest 2>&1 | tail -5
    Expected Result: 180+ tests pass (includes new tests), no regressions
    Evidence: .sisyphus/evidence/task-2-no-regression.txt

  Scenario: Basic output smoke test
    Tool: Bash
    Steps:
      1. python3 -c "from llm_race.bench.prompts import generate_prompt; p=generate_prompt(100); assert len(p) > 0; assert p[0].isupper(); assert p.endswith('.'); print(f'OK: generated {len(p)} chars')"
    Expected Result: All assertions pass
    Evidence: .sisyphus/evidence/task-2-smoke.txt
  ```

  **Evidence to Capture**:
  - [ ] task-2-prompt-tests.txt
  - [ ] task-2-no-regression.txt
  - [ ] task-2-smoke.txt

  **Commit**: YES (groups with T1, T3)
  - Message: `test(bench): add unit tests for prompt generation`
  - Files: `tests/test_bench_prompts.py`

---

- [x] 3. Create `tests/test_reporter.py` — tests for `utils/reporter.py`

  **What to do**:
  - Create `tests/test_reporter.py` with tests for `llm_race/utils/reporter.py`:
    - `format_table(results: list[ScenarioResult]) -> str`
    - `save_csv(results: list["ScenarioResult"], path: str) -> None`
    - `save_json(results: list["ScenarioResult"], path: str) -> None`

  **Approach**: Create `ScenarioResult` instances directly in tests (it's a plain dataclass in `llm_race/bench/runner.py`). Use `tempfile` for file I/O tests (following pattern from `tests/test_queries.py`).

  **Test cases**:

  **TestFormatTable**:
  - `test_header_in_output` — output contains expected column headers (Concurrency, Prompt Len, TPS, etc.)
  - `test_single_result` — one ScenarioResult appears in the formatted output
  - `test_multiple_results` — two ScenarioResults both appear in output
  - `test_empty_list` — empty list returns a string with header and separator only

  **TestSaveCsv**:
  - `test_csv_created` — file is created at specified path
  - `test_csv_content` — file contains expected headers and data values
  - `test_empty_list_writes_header_only` — empty results writes only header row
  - `test_csv_values_match` — values in CSV match the ScenarioResult fields

  **TestSaveJson**:
  - `test_json_created` — file is created at specified path
  - `test_json_structure` — file contains `timestamp` and `scenarios` keys
  - `test_json_content` — scenario data appears correctly in the JSON
  - `test_empty_list_writes_empty_scenarios` — empty results gives empty scenarios array

  **Must NOT do**:
  - Do NOT modify `utils/reporter.py`
  - Do NOT leave temp files behind (use `tempfile` + cleanup)
  - Do NOT mock file I/O — test actual writes to temp files
  - Do NOT test `logging` output (the module logs but we don't need to capture log output)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple test file creation with standard patterns (tempfile, assertions)
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2)
  - **Blocks**: F1, F2, F3
  - **Blocked By**: None

  **References**:
  - `llm_race/utils/reporter.py:1-68` — Full source of functions under test
  - `llm_race/bench/runner.py:46-68` — ScenarioResult dataclass definition (all 18 fields)
  - `tests/test_queries.py:44-52` — tempfile + cleanup pattern for file I/O tests

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: All reporter tests pass
    Tool: Bash
    Steps:
      1. python3 -m pytest tests/test_reporter.py -v 2>&1 | tail -25
    Expected Result: All tests PASSED (10+ tests, 0 failures)
    Evidence: .sisyphus/evidence/task-3-reporter-tests.txt

  Scenario: No regressions
    Tool: Bash
    Steps:
      1. python3 -m pytest 2>&1 | tail -5
    Expected Result: 190+ tests pass (includes new tests), no regressions
    Evidence: .sisyphus/evidence/task-3-no-regression.txt

  Scenario: CSV file actual content
    Tool: Bash
    Steps:
      1. python3 -c "
    from llm_race.utils.reporter import save_csv
    from llm_race.bench.runner import ScenarioResult
    import tempfile, os
    r = ScenarioResult(concurrency=1, prompt_length=100, total_requests=10, successful_requests=9, failed_requests=1)
    f = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
    save_csv([r], f.name)
    content = open(f.name).read()
    os.unlink(f.name)
    assert 'concurrency' in content
    assert '1' in content
    assert '9' in content
    print('OK: CSV content verified')
    "
    Expected Result: All assertions pass
    Evidence: .sisyphus/evidence/task-3-csv-verify.txt
  ```

  **Evidence to Capture**:
  - [ ] task-3-reporter-tests.txt
  - [ ] task-3-no-regression.txt
  - [ ] task-3-csv-verify.txt

  **Commit**: YES (groups with T1, T2)
  - Message: `test(utils): add unit tests for reporter (format_table, save_csv, save_json)`
  - Files: `tests/test_reporter.py`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each task: verify test file exists and covers the stated requirements. Check no source files were modified. Check evidence files exist.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality + Full Test Suite** — `unspecified-high`
  Run `python -m pytest`. Review new test files for: meaningful assertions, no bare except, no commented-out tests, proper cleanup of temp files.
  Output: `Tests [N pass/N fail] | Issues [N] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute every QA scenario from every task. Verify edge cases manually (empty lists, None returns, single values). Cross-check that all required test cases from the plan are actually in each test file.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

---

## Commit Strategy

- **T1+T2+T3**: `test(utils): add unit tests for timing, prompts, and reporter` (single commit for all 3 test files)

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/test_timing.py -v
# Expected: 10+ tests pass

python -m pytest tests/test_bench_prompts.py -v
# Expected: 6+ tests pass

python -m pytest tests/test_reporter.py -v
# Expected: 10+ tests pass

python -m pytest
# Expected: 190+ tests pass, no regressions
```

### Final Checklist
- [x] `tests/test_timing.py` — 18 tests, covers empty/single/normal/edge
- [x] `tests/test_bench_prompts.py` — 6 tests, covers format/content/edge
- [x] `tests/test_reporter.py` — 12 tests, covers table/CSV/JSON/edge
- [x] All 199 tests pass
- [x] No source files modified
- [x] No existing tests broken
