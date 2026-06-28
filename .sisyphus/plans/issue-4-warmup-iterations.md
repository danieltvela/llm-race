# Plan: Warmup Iterations (Issue #4)

## TL;DR

> **Quick Summary**: Add warmup iterations to the benchmark runner — `run_scenario()` runs N warmup batches (default 2, discarded) before M measured batches (default 10, collected), with CLI flags to override.
>
> **Deliverables**:
> - Modified `llm_race/bench/runner.py` — warmup loop in `run_scenario()`, propagated through `run_benchmarks()`
> - Modified `llm_race/bench/cli.py` — `--warmup-iterations` and `--measured-iterations` CLI args
> - Modified `llm_race/config/__init__.py` — default constants
> - New `tests/test_warmup.py` — unit tests with mock provider
>
> **Estimated Effort**: Quick
> **Parallel Execution**: YES — 2 waves
> **Critical Path**: Task 1 → Task 3 → Final Wave

---

## Context

### Original Request
[Issue #4](https://github.com/danieltvela/llm-race/issues/4): Add warmup iterations to benchmark runner as specified in AGENTS.md.

### Interview Summary
**Key Discussions**:
- **Loop location**: Inside `run_scenario()` (not `run_benchmarks()`) — cleaner interface
- **request_ids**: Reset to 0 for measured results (warmup discarded entirely)
- **Logging**: Informative — "Warmup iteration 1/2 complete", "Measured iteration 1/10 complete"
- **Test strategy**: Tests after (not TDD), with agent-executed QA scenarios

### Metis Review
**Identified Gaps** (addressed):
- **Propagation through run_benchmarks()**: Auto-resolved — `run_benchmarks()` will accept `warmup_iterations` and `measured_iterations` params and pass to `run_scenario()`
- **httpx client reuse**: Auto-resolved — Same `AsyncClient` reused across warmup + measured phases (realistic connection pooling)
- **Warmup failures**: Auto-resolved — Log as warning, do NOT abort scenario
- **Wall clock timing**: Auto-resolved — `wall_clock_seconds` measures from warmup start to measured end (reflects real wall time)
- **warmup=0 edge case**: Auto-resolved — Skip warmup loop gracefully
- **Both=0 edge case**: Auto-resolved — Log warning, return empty `[]`

---

## Work Objectives

### Core Objective
Modify the benchmark runner to execute N warmup iterations (discarded) before M measured iterations (collected), per AGENTS.md specification.

### Concrete Deliverables
- `runner.py`: `run_scenario()` with `warmup_iterations` (default 2) and `measured_iterations` (default 10) params
- `runner.py`: `run_benchmarks()` forwards warmup/measured to `run_scenario()`
- `cli.py`: `--warmup-iterations` and `--measured-iterations` flags
- `config/__init__.py`: `DEFAULT_WARMUP_ITERATIONS = 2`, `DEFAULT_MEASURED_ITERATIONS = 10`
- `tests/test_warmup.py`: Unit tests with mock provider

### Definition of Done
- [x] `python3 -m pytest tests/test_warmup.py -v` → all tests pass
- [x] `python3 -m llm_race.bench.cli run --help` shows `--warmup-iterations` and `--measured-iterations`

### Must Have
- Warmup iterations run FIRST and are discarded (no metrics collected)
- Measured iterations run AFTER warmup and metrics ARE collected
- Defaults match AGENTS.md (2 warmup, 10 measured)
- CLI flags available to override defaults
- `--workload` profile works with warmup/measured (profiles don't set warmup values — defaults apply)

### Must NOT Have (Guardrails)
- Do NOT add warmup/measured to workload profiles (profiles only set concurrency + prompt_lengths)
- Do NOT change DB schema (no new columns for warmup/measured count)
- Do NOT modify web viewer
- Do NOT change provider implementations
- Do NOT break backward compatibility for providers that don't serve streaming (non-streaming `complete()` call pattern in providers like `mlx_lm` should still work — warmup uses same `stream_complete()` call)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests after
- **Framework**: pytest

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Library/Module**: Use Bash (python3) — Import runner, create mock provider, call `run_scenario()`, verify metrics

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation, parallel):
├── Task 1: Config constants + runner warmup loop [deep]
└── Task 2: CLI args + run_benchmarks propagation [quick]

Wave 2 (After Wave 1 — verification):
├── Task 3: Unit tests for warmup/measured behavior [unspecified-high]

Wave FINAL (After ALL tasks):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Scope fidelity check (deep)
└── F4: Real manual QA (unspecified-high)
```

### Dependency Matrix
- **1**: None
- **2**: None
- **3**: 1, 2
- **F1-F4**: 1, 2, 3

---

## TODOs

- [x] 1. Config constants + runner warmup loop

  **What to do**:
  - Add `DEFAULT_WARMUP_ITERATIONS = 2` and `DEFAULT_MEASURED_ITERATIONS = 10` to `llm_race/config/__init__.py`
  - Modify `run_scenario()` signature in `llm_race/bench/runner.py`:
    - Add `warmup_iterations: int = DEFAULT_WARMUP_ITERATIONS` parameter
    - Add `measured_iterations: int = DEFAULT_MEASURED_ITERATIONS` parameter
  - Implement warmup loop inside `run_scenario()`:
    - Extract the current single-batch logic (lines 103-153) into a helper `_run_batch(provider, model, messages, concurrency, max_tokens, temperature, top_p, client) -> list[RequestMetrics]`
    - Or simply loop the existing gathered execution
    - Phase 1: Run `warmup_iterations` batches of `concurrency` requests → discard all results
    - Phase 2: Run `measured_iterations` batches of `concurrency` requests → collect all results
    - Flatten the measured results into a single list of `RequestMetrics` (same as current return type)
  - Assign `request_id` sequentially across all measured batches (0..N-1)
  - Add informative logging:
    - `logger.info("Warmup iteration %d/%d complete", i+1, warmup_iterations)`
    - `logger.info("Measured iteration %d/%d complete", i+1, measured_iterations)`
  - Reuse the same `httpx.AsyncClient` for all warmup + measured iterations (connection pooling)
  - On warmup request failure: log warning (do NOT abort)
  - `wall_clock_seconds`: measure from warmup start to measured end
  - Edge cases:
    - If `warmup_iterations == 0`: skip warmup phase silently
    - If `measured_iterations == 0`: log warning, return empty `[]`
  - Update `run_scenario()` docstring to document new parameters

  **Must NOT do**:
  - Do NOT change the return type (still `list[RequestMetrics]`)
  - Do NOT collect any metrics from warmup iterations
  - Do NOT modify `_run_with_client()` inner structure — just loop around it

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core logic change with async loop, error handling, edge cases — needs careful implementation
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References** (existing code to follow):
  - `llm_race/bench/runner.py:run_scenario()` — Current single-batch implementation to modify
  - `llm_race/bench/runner.py:run_benchmarks()` — Caller that will pass warmup/measured params

  **API/Type References**:
  - `llm_race/bench/runner.py:RequestMetrics` — Return type, must stay unchanged
  - `llm_race/config/__init__.py:DEFAULT_PROMPT_LENGTHS` — Existing default pattern for new constants

  **External References**:
  - `https://docs.python.org/3/library/asyncio.html#asyncio.gather` — asyncio.gather with return_exceptions
  - `https://docs.python-httpx.org/en/stable/async/` — httpx.AsyncClient usage

  **WHY Each Reference Matters**:
  - The runner is the single file to modify — read it fully to understand the current `_run_with_client()` closure
  - Config defaults follow the same pattern as `DEFAULT_CONCURRENCY`, `DEFAULT_PROMPT_LENGTHS` etc.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Warmup iterations are discarded
    Tool: Bash (python3)
    Preconditions: Mock provider that tracks call count
    Steps:
      1. Import run_scenario, create FakeProvider that records invocations
      2. Call run_scenario(concurrency=2, prompt_length=64, ..., warmup_iterations=2, measured_iterations=3)
      3. Assert provider was called 2*2 + 3*2 = 10 times total
      4. Assert returned metrics list length = 3*2 = 6 (only measured)
    Expected Result: 6 metrics returned, warmup not included
    Evidence: .sisyphus/evidence/task-1-warmup-discard.txt

  Scenario: warmup_iterations=0 skips warmup
    Tool: Bash (python3)
    Preconditions: Mock provider
    Steps:
      1. Call run_scenario(warmup_iterations=0, measured_iterations=2, concurrency=2)
      2. Assert metrics length = 4 (only 2 measured batches of 2)
    Expected Result: 4 metrics, no warmup runs
    Evidence: .sisyphus/evidence/task-1-warmup-zero.txt

  Scenario: measured_iterations=0 returns empty
    Tool: Bash (python3)
    Preconditions: Mock provider
    Steps:
      1. Call run_scenario(warmup_iterations=1, measured_iterations=0, concurrency=2)
      2. Assert returned list is empty
    Expected Result: Empty list
    Evidence: .sisyphus/evidence/task-1-measured-zero.txt
  ```

  **Evidence to Capture**:
  - [ ] Console output showing log messages for warmup/measured iterations

  **Commit**: YES
  - Message: `feat(bench): add warmup loop to run_scenario with configurable iterations`
  - Files: `llm_race/config/__init__.py`, `llm_race/bench/runner.py`

- [x] 2. CLI args + run_benchmarks propagation

  **What to do**:
  - In `llm_race/config/__init__.py`: (if not already done by Task 1) add `DEFAULT_WARMUP_ITERATIONS = 2` and `DEFAULT_MEASURED_ITERATIONS = 10`
  - In `llm_race/bench/runner.py`: Modify `run_benchmarks()` signature to accept `warmup_iterations: int = DEFAULT_WARMUP_ITERATIONS` and `measured_iterations: int = DEFAULT_MEASURED_ITERATIONS`, then pass them to `run_scenario()`
  - In `llm_race/bench/cli.py`:
    - Add `--warmup-iterations` argument with `type=int, default=DEFAULT_WARMUP_ITERATIONS`
    - Add `--measured-iterations` argument with `type=int, default=DEFAULT_MEASURED_ITERATIONS`
    - Pass `warmup_iterations=args.warmup_iterations` and `measured_iterations=args.measured_iterations` to `run_benchmarks()`
  - Update `run_benchmarks()` docstring

  **Must NOT do**:
  - Do NOT modify `--workload` behavior (profiles don't set warmup/measured)
  - Do NOT change the return type of `run_benchmarks()`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward plumbing of parameters through 3 files
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `llm_race/bench/cli.py:41-44` — Existing `--max-tokens`, `--temperature` args (follow same pattern)
  - `llm_race/bench/cli.py:66-70` — Existing `run_benchmarks()` call (add params here)
  - `llm_race/bench/runner.py:run_benchmarks()` — Add params to signature
  - `llm_race/config/__init__.py:16-21` — Existing default constants pattern

  **WHY Each Reference Matters**:
  - CLI arguments follow the exact same argparse pattern as existing flags
  - The `run_benchmarks()` call in cli.py is the single point where args are passed to runner

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: CLI shows both new arguments in help
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run `python3 -m llm_race.bench.cli run --help`
      2. Assert output contains "warmup-iterations"
      3. Assert output contains "measured-iterations"
      4. Assert output shows "2" near warmup default
      5. Assert output shows "10" near measured default
    Expected Result: Both flags visible with correct defaults
    Evidence: .sisyphus/evidence/task-2-cli-help.txt

  Scenario: Custom values propagate through runner
    Tool: Bash (python3)
    Preconditions: Temporary script that imports run_benchmarks
    Steps:
      1. Create a test script that calls run_benchmarks(warmup_iterations=3, measured_iterations=5, ...)
      2. Assert run_benchmarks passes these to run_scenario (by mocking run_scenario)
    Expected Result: Parameters correctly forwarded
    Evidence: .sisyphus/evidence/task-2-propagation.txt
  ```

  **Evidence to Capture**:
  - [ ] CLI help output screenshot/console capture
  - [ ] Propagation test output

  **Commit**: YES
  - Message: `feat(cli): add --warmup-iterations and --measured-iterations arguments`
  - Files: `llm_race/config/__init__.py`, `llm_race/bench/runner.py`, `llm_race/bench/cli.py`

- [x] 3. Unit tests for warmup/measured behavior

  **What to do**:
  - Create `tests/test_warmup.py`
  - Test classes:
    - `TestWarmupDiscard`: Verify warmup results are NOT included in metrics
      - `test_warmup_discarded`: 2 warmup, 3 measured, concurrency=2 → 6 metrics (not 10)
      - `test_warmup_zero`: 0 warmup, 2 measured, concurrency=2 → 4 metrics
      - `test_measured_zero`: 1 warmup, 0 measured → empty list
    - `TestRequestIDs`: Verify request_id assignment
      - `test_sequential_ids`: 2 warmup, 3 measured, concurrency=2 → IDs 0,1,2,3,4,5
      - `test_ids_different_batches`: Verify IDs don't reset between measured batches
    - `TestDefaults`: Verify default values match AGENTS.md
      - `test_defaults`: Assert DEFAULT_WARMUP_ITERATIONS == 2 and DEFAULT_MEASURED_ITERATIONS == 10
    - `TestCLIArgs`: Verify CLI integration (can use pytest's capsys or argparse directly)
      - `test_cli_defaults`: Parse args without flags → defaults applied
      - `test_cli_custom`: Parse args with `--warmup-iterations 5 --measured-iterations 20` → values applied
  - Use a mock/fake provider that returns a known result (e.g., `FakeProvider` class with `stream_complete()` returning `{"status": "ok", ...}`)
  - Use `unittest.mock` or a simple FakeProvider class

  **Must NOT do**:
  - Do NOT make actual HTTP calls (use mock provider)
  - Do NOT test provider internals
  - Do NOT modify existing tests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple test classes, mock provider setup, async test patterns — moderate effort
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Wave 1)
  - **Blocks**: Final Wave
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `tests/test_workloads.py` — Existing test structure (pytest, async patterns, fixtures)
  - `tests/test_providers.py` — Check if there's a mock/fake provider pattern to follow

  **API/Type References**:
  - `llm_race/bench/runner.py:run_scenario` — Function under test
  - `llm_race/bench/runner.py:RequestMetrics` — Return type to assert against
  - `llm_race/config/__init__.py:DEFAULT_WARMUP_ITERATIONS, DEFAULT_MEASURED_ITERATIONS` — Defaults to verify
  - `llm_race/bench/cli.py` — CLI argument parsing (for CLI tests)

  **WHY Each Reference Matters**:
  - Follow the test structure pattern from test_workloads.py (class-based, fixtures, async tests with pytest.mark.asyncio if needed)
  - Understand RequestMetrics fields to assert correct values

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: All tests pass
    Tool: Bash
    Preconditions: Tasks 1 and 2 complete
    Steps:
      1. Run `python3 -m pytest tests/test_warmup.py -v`
      2. Assert exit code == 0
      3. Count passing tests — should be 7+ (all written tests)
    Expected Result: All tests green
    Evidence: .sisyphus/evidence/task-3-test-results.txt

  Scenario: Specific warmup discard test
    Tool: Bash
    Preconditions: Tasks 1 and 2 complete
    Steps:
      1. Run `python3 -m pytest tests/test_warmup.py::TestWarmupDiscard::test_warmup_discarded -v`
      2. Assert PASS
    Expected Result: 2 warmup batches of 2 = 4 discarded, 3 measured batches of 2 = 6 returned
    Evidence: .sisyphus/evidence/task-3-warmup-discard-test.txt
  ```

  **Evidence to Capture**:
  - [ ] Full pytest output showing test names and results

  **Commit**: YES
  - Message: `test(bench): add unit tests for warmup and measured iterations`
  - Files: `tests/test_warmup.py`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle` — **APPROVED**
  `Must Have [5/5] | Must NOT Have [5/5] | Tasks [3/3]`
- [x] F2. **Code Quality & Test Review** — `unspecified-high` — **APPROVED**
  `Tests [27/27 pass] | Types [OK] | No AI slop [CLEAN] | FakeProvider [no HTTP]`
- [x] F3. **Scope Fidelity Check** — `deep` — **APPROVED**
  `Tasks [3/3 compliant] | Contamination [CLEAN]`
- [x] F4. **Real Manual QA** — `unspecified-high` — **APPROVED**
  `Scenarios [5/5 pass] | Evidence: .sisyphus/evidence/final-qa/`

---

## Commit Strategy

- **1**: `feat(bench): add warmup loop to run_scenario with configurable iterations` — `config/__init__.py`, `runner.py`
- **2**: `feat(cli): add --warmup-iterations and --measured-iterations arguments` — `runner.py`, `cli.py`
- **3**: `test(bench): add unit tests for warmup and measured iterations` — `tests/test_warmup.py`

---

## Success Criteria

### Verification Commands
```bash
python3 -m pytest tests/test_warmup.py -v  # Expected: all tests pass
python3 -m llm_race.bench.cli run --help   # Expected: shows --warmup-iterations, --measured-iterations
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
