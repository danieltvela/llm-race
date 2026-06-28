# Implement Workload Profiles Module (Issue #3)

## TL;DR

> **Quick Summary**: Create `llm_race/bench/workloads.py` with 5 workload profiles (single-user, chat, multi-agent, high-throughput, stress), add `--workload` CLI argument that replaces manual `--concurrency`/`--prompt-lengths`, and make the benchmark runner dispatch based on the selected profile.
>
> **Deliverables**:
> - `llm_race/bench/workloads.py` — WorkloadProfile dataclass + 5 profile definitions + registry
> - Updated `llm_race/bench/cli.py` — `--workload` argument (mutually exclusive with `--concurrency`/`--prompt-lengths`)
> - Updated `llm_race/bench/runner.py` — Dispatch using workload profile
> - `llm_race/bench/__init__.py` — Re-export workload profiles
> - `tests/test_workloads.py` — Unit tests for profiles + integration tests for CLI/runner dispatch
>
> **Estimated Effort**: Short
> **Parallel Execution**: YES — 2 waves parallelizable
> **Critical Path**: Task 1 → Task 2 → Task 4 → Final Wave

---

## Context

### Original Request
[GitHub Issue #3](https://github.com/danieltvela/llm-race/issues/3) — Implement workload profiles module as described in README.md.

### Interview Summary
**Key Decisions**:
- `--workload` replaces everything: when provided, `--concurrency` and `--prompt-lengths` are ignored (mutually exclusive)
- Chat profile: define with defaults only — no context growth simulation yet
- Prompt sizes: all profiles use `[64, 512, 2048, 4096]` (existing DEFAULT_PROMPT_LENGTHS)
- Concurrency per profile: single-user=[1], chat=[1], multi-agent=[4,8,16], high-throughput=[32,64,128], stress=[256,512]
- Test strategy: tests after (not TDD), but QA scenarios required per task

**Research Findings**:
- DB already has `workload_profile: str` column in `Benchmark` model
- Web viewer already filters by `workload_profile`
- Current CLI defaults: `DEFAULT_CONCURRENCY = [1, 16, 128, 512]`, `DEFAULT_PROMPT_LENGTHS = [64, 512, 2048, 4096]`
- `run_benchmarks()` signature: `(provider, model, concurrency, prompt_lengths, max_tokens, temperature, top_p, output)`

### Metis Review
**Identified Gaps** (addressed):
- CLI interaction semantics: `--workload` mutually exclusive with `--concurrency`/`--prompt-lengths` (resolved in plan)
- Backward compatibility: when `--workload` absent, behavior is identical to current code (guardrail applied)
- Profile name validation: reject unknown names with clear error listing valid options (guardrail applied)
- Extensibility: simple registry dict pattern for adding profiles later (default applied)
- Warmup/prompt_size mapping: explicitly excluded from scope (guardrail applied)

---

## Work Objectives

### Core Objective
Create a workload profiles system that allows users to select a pre-defined benchmark scenario via `--workload <profile>`, which automatically configures concurrency levels and prompt lengths for the benchmark run.

### Concrete Deliverables
- `llm_race/bench/workloads.py` — WorkloadProfile dataclass + 5 named profiles + registry
- `llm_race/bench/__init__.py` — Public exports
- `llm_race/bench/cli.py` — `--workload` argparse argument
- `llm_race/bench/runner.py` — Workload dispatch logic
- `tests/test_workloads.py` — Unit + integration tests

### Definition of Done
- [x] `python -m llm_race.bench run --help` shows `--workload` with profile names
- [ ] `python -m llm_race.bench run --workload single-user` runs with concurrency=[1] and default prompt lengths
- [x] `python -m llm_race.bench run --concurrency 4` still works identically to before (backward compat)
- [x] `python -m llm_race.bench run --workload invalid` raises clear error with valid options
- [x] `python -m pytest tests/test_workloads.py -v` passes
- [x] All QA scenarios pass

### Must Have
- WorkloadProfile dataclass with fields: name, description, concurrency_levels, default_prompt_lengths, behavior
- 5 profile definitions matching README spec
- CLI `--workload` argument with validation
- Runner dispatches concurrency/prompt lengths based on profile
- Backward compatible: existing `--concurrency`/`--prompt-lengths` usage unchanged

### Must NOT Have (Guardrails)
- No context growth simulation for chat profile (future issue)
- No changes to web viewer (already works with workload_profile from DB)
- No changes to provider implementations
- No changes to warmup/measured iteration counts
- No changes to prompt_size label mapping (independent of workload)
- No database schema changes

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, tests/conftest.py)
- **Automated tests**: Tests after (unit tests added after implementation tasks)
- **Framework**: pytest (with pytest_asyncio plugin)
- **QA Policy**: Agent-executed scenarios using Bash for CLI/runner verification

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI tests**: Use Bash to run `python -m llm_race.bench run --help` and verify output
- **Module tests**: Use Bash with `python -c "from llm_race.bench.workloads import ...; ..."` imports
- **Runner tests**: Use Bash with `python -m pytest tests/test_workloads.py -v`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — can start immediately):
├── Task 1: Create workloads.py with WorkloadProfile dataclass + 5 profiles + registry [quick]
├── Task 2: Update bench/__init__.py with public exports [quick]

Wave 2 (Core integration, depends on Wave 1):
├── Task 3: Add --workload to CLI + runner dispatch logic [quick]
├── Task 4: Write unit + integration tests [quick]

Wave FINAL (After ALL tasks):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality + test suite verification (unspecified-high)
└── Task F3: Scope fidelity check (deep)
```

### Dependency Matrix
- **1**: None
- **2**: 1
- **3**: 2
- **4**: 3
- **F1-F3**: 4

### Agent Dispatch Summary
- **Wave 1**: 2 agents — T1 → `quick`, T2 → `quick`
- **Wave 2**: 2 agents — T3 → `quick`, T4 → `quick`
- **Final**: 3 agents — F1 → `oracle`, F2 → `unspecified-high`, F3 → `deep`

---

## TODOs

> Implementation + Test = sometimes separate (tests after). EVERY task MUST have QA Scenarios.

- [x] 1. Create `llm_race/bench/workloads.py` with WorkloadProfile dataclass, 5 profile definitions, and registry

  **What to do**:
  - Create `llm_race/bench/workloads.py` with:
    - `WorkloadProfile` dataclass with fields: `name: str`, `description: str`, `concurrency_levels: list[int]`, `default_prompt_lengths: list[int]`, `behavior: str`
    - 5 named constants: `SINGLE_USER`, `CHAT`, `MULTI_AGENT`, `HIGH_THROUGHPUT`, `STRESS` (instances of WorkloadProfile)
    - A `WORKLOAD_REGISTRY: dict[str, WorkloadProfile]` mapping profile name → profile instance
    - A `get_workload(name: str) -> WorkloadProfile` function that raises `ValueError` with valid names on invalid input
    - Profile details:
      - SINGLE_USER: name="single-user", desc="Single request, measure raw latency", concurrency=[1], prompt_lengths=DEFAULT_PROMPT_LENGTHS, behavior="single request"
      - CHAT: name="chat", desc="Conversational flow with context growth", concurrency=[1], prompt_lengths=DEFAULT_PROMPT_LENGTHS, behavior="conversational (context growth not simulated yet)"
      - MULTI_AGENT: name="multi-agent", desc="Multiple independent agents running in parallel", concurrency=[4,8,16], prompt_lengths=DEFAULT_PROMPT_LENGTHS, behavior="independent parallel agents"
      - HIGH_THROUGHPUT: name="high-throughput", desc="Many users hitting the endpoint simultaneously", concurrency=[32,64,128], prompt_lengths=DEFAULT_PROMPT_LENGTHS, behavior="constant concurrent load"
      - STRESS: name="stress", desc="Maximum concurrency until degradation", concurrency=[256,512], prompt_lengths=DEFAULT_PROMPT_LENGTHS, behavior="degradation testing"
  - Use `from __future__ import annotations` for consistency with existing code
  - Import `DEFAULT_PROMPT_LENGTHS` from `llm_race.config`

  **Must NOT do**:
  - Do NOT implement context growth for chat
  - Do NOT add warmup iteration logic
  - Do NOT modify any existing file yet (this is a new file only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single new file, straightforward dataclass + constants, no complex logic
  - **Skills**: none needed (`load_skills=[]`)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: [2, 3, 4]
  - **Blocked By**: None (can start immediately)

  **References**:
  - `llm_race/config/__init__.py` — Import `DEFAULT_PROMPT_LENGTHS` constant
  - `llm_race/db/types.py:BenchmarkFilters.workload_profile` — Shows the workload_profile string values used in the DB layer (e.g. "single-user", "chat")
  - `llm_race/config/base.py:StreamResult` — Dataclass pattern to follow (frozen=True, type hints, etc.)

  **Acceptance Criteria**:
  - [ ] File exists: `llm_race/bench/workloads.py`
  - [ ] All 5 profile constants exported
  - [ ] `WORKLOAD_REGISTRY` contains all 5 profiles
  - [ ] `get_workload("single-user")` returns correct profile
  - [ ] `get_workload("invalid")` raises ValueError with valid names in message

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Verify all profiles are importable and correct
    Tool: Bash
    Preconditions: None (new file)
    Steps:
      1. Run: python -c "from llm_race.bench.workloads import WORKLOAD_REGISTRY; print(list(WORKLOAD_REGISTRY.keys()))"
      2. Run: python -c "from llm_race.bench.workloads import get_workload; p = get_workload('single-user'); print(p.name, p.concurrency_levels)"
      3. Run: python -c "from llm_race.bench.workloads import get_workload; p = get_workload('stress'); print(p.name, p.concurrency_levels)"
    Expected Result:
      - Step 1 output contains "single-user", "chat", "multi-agent", "high-throughput", "stress"
      - Step 2 output: "single-user [1]"
      - Step 3 output: "stress [256, 512]"
    Evidence: .sisyphus/evidence/task-1-profiles.txt

  Scenario: Invalid workload name raises clear error
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.bench.workloads import get_workload; get_workload('nonexistent')" 2>&1
    Expected Result: Error message contains valid profile names
    Evidence: .sisyphus/evidence/task-1-invalid-error.txt
  ```

  **Commit**: NO (group with Task 2)
  - Files: `llm_race/bench/workloads.py`

---

- [x] 2. Update `llm_race/bench/__init__.py` with public exports

  **What to do**:
  - Create `llm_race/bench/__init__.py` (or update if exists) to export:
    - `from llm_race.bench.workloads import WorkloadProfile, WORKLOAD_REGISTRY, get_workload, SINGLE_USER, CHAT, MULTI_AGENT, HIGH_THROUGHPUT, STRESS`

  **Must NOT do**:
  - Do NOT change any existing __init__.py exports unless they already exist

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Trivial one-line exports
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: YES (but depends on Task 1 existing)
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: [3, 4]
  - **Blocked By**: Task 1

  **References**:
  - Existing `llm_race/bench/__init__.py` to check current exports

  **Acceptance Criteria**:
  - [ ] `python -c "from llm_race.bench import WorkloadProfile, WORKLOAD_REGISTRY, get_workload"` succeeds

  **QA Scenarios**:

  ```
  Scenario: Public exports work
    Tool: Bash
    Preconditions: Task 1 complete
    Steps:
      1. Run: python -c "from llm_race.bench import WorkloadProfile, WORKLOAD_REGISTRY, get_workload, SINGLE_USER; print(SINGLE_USER.name)"
    Expected Result: Output is "single-user"
    Evidence: .sisyphus/evidence/task-2-exports.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `feat(bench): add WorkloadProfile module with 5 workload profiles`

---

- [x] 3. Add `--workload` to CLI and runner dispatch logic

  **What to do**:
  - In `llm_race/bench/cli.py`:
    - Import `WORKLOAD_REGISTRY` from `llm_race.bench.workloads`
    - Add `--workload` argument to `run_parser`:
      ```python
      run_parser.add_argument(
          "--workload",
          choices=list(WORKLOAD_REGISTRY.keys()),
          default=None,
          help="Workload profile (overrides --concurrency and --prompt-lengths). Choices: %(choices)s",
      )
      ```
    - After parsing args, if `args.workload` is set, load the profile and pass its `concurrency_levels` and `default_prompt_lengths` to `run_benchmarks()`
    - The `--concurrency` and `--prompt-lengths` args remain available but are ignored when `--workload` is provided
    - Log which profile was selected
  - In `llm_race/bench/runner.py`:
    - Add `workload_profile: str | None = None` parameter to `run_benchmarks()`
    - When `workload_profile` is set, log it at the start
    - No behavioral change when `workload_profile` is None (backward compat)

  **Must NOT do**:
  - Do NOT change `run_benchmarks()` existing parameter order
  - Do NOT remove `--concurrency` or `--prompt-lengths` from CLI
  - Do NOT add DB persistence logic for workload_profile here (already handled)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small, scoped changes to two existing files
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: [4]
  - **Blocked By**: Tasks 1, 2

  **References**:
  - `llm_race/bench/cli.py` — Current CLI structure
  - `llm_race/bench/runner.py:run_benchmarks()` — Add workload_profile parameter
  - `llm_race/config/__init__.py` — DEFAULT_CONCURRENCY and DEFAULT_PROMPT_LENGTHS

  **Acceptance Criteria**:
  - [ ] `python -m llm_race.bench run --help` shows `--workload` with choices
  - [ ] `python -m llm_race.bench run --workload single-user` runs with concurrency=[1]
  - [ ] `python -m llm_race.bench run --concurrency 4` works as before (no --workload)
  - [ ] `python -m llm_race.bench run --workload nonexistent` exits with error

  **QA Scenarios**:

  ```
  Scenario: --help shows workload choices
    Tool: Bash
    Preconditions: Tasks 1-2 complete
    Steps:
      1. Run: python -m llm_race.bench run --help
    Expected Result: Output contains "--workload", "single-user", "chat", "multi-agent", "high-throughput", "stress"
    Evidence: .sisyphus/evidence/task-3-help.txt

  Scenario: Invalid workload name raises error
    Tool: Bash
    Preconditions: Tasks 1-2 complete
    Steps:
      1. Run: python -m llm_race.bench run --workload invalid_profile 2>&1
    Expected Result: Exit code != 0, error mentions "invalid choice" with valid options
    Evidence: .sisyphus/evidence/task-3-invalid-error.txt

  Scenario: Backward compat — --concurrency still works
    Tool: Bash
    Preconditions: Tasks 1-2 complete
    Steps:
      1. Run: python -m llm_race.bench run --help 2>&1 | grep -E "concurrency|prompt-lengths"
    Expected Result: Both --concurrency and --prompt-lengths still shown in help
    Evidence: .sisyphus/evidence/task-3-backward-compat.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): add --workload argument and wire into runner dispatch`
  - Files: `llm_race/bench/cli.py`, `llm_race/bench/runner.py`

---

- [x] 4. Write unit + integration tests

  **What to do**:
  - Create `tests/test_workloads.py` with:
    - **Unit tests for WorkloadProfile dataclass**:
      - Test all 5 profiles exist in WORKLOAD_REGISTRY
      - Test each profile has correct name, concurrency_levels, description
      - Test `get_workload()` returns correct profile
      - Test `get_workload("invalid")` raises ValueError
    - **Integration tests for CLI**:
      - Test `--help` shows workload choices (use `argparse` directly)
      - Test `--workload single-user` sets correct concurrency/prompt_lengths
      - Test `--workload` without value shows error
    - **Integration tests for runner dispatch**:
      - Test that passing workload_profile to `run_benchmarks()` logs correctly
      - Test backward compat: `run_benchmarks()` without workload_profile works as before
  - Use pytest conventions matching existing tests
  - Mock httpx connections to avoid real API calls

  **Must NOT do**:
  - Do NOT test actual LLM endpoints
  - Do NOT modify existing test files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward unit + integration tests
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: [F1, F2, F3]
  - **Blocked By**: Task 3

  **References**:
  - `tests/conftest.py` — Pytest fixtures
  - `tests/test_models.py` — Existing test patterns
  - `llm_race/bench/cli.py` — CLI arg parsing
  - `llm_race/bench/runner.py` — Runner function

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/test_workloads.py -v` passes (all tests)

  **QA Scenarios**:

  ```
  Scenario: All tests pass
    Tool: Bash
    Preconditions: Tasks 1-3 complete
    Steps:
      1. Run: python -m pytest tests/test_workloads.py -v 2>&1
    Expected Result: All tests pass (exit code 0)
    Evidence: .sisyphus/evidence/task-4-all-tests.txt
  ```

  **Commit**: YES
  - Message: `test(bench): add unit and integration tests for workload profiles`
  - Files: `tests/test_workloads.py`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality + Test Suite** — `unspecified-high`
  Run `python -m pytest tests/test_workloads.py -v`. Review changed files for: type safety, logic errors, commented-out code, unused imports. Check consistency with existing code patterns.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Scope Fidelity Check** — `deep`
  Read actual diff (git log/diff) for each task. Verify everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

| Task | Message | Files |
|------|---------|-------|
| 1+2 | `feat(bench): add WorkloadProfile module with 5 workload profiles` | `llm_race/bench/workloads.py`, `llm_race/bench/__init__.py` |
| 3 | `feat(cli): add --workload argument and wire into runner dispatch` | `llm_race/bench/cli.py`, `llm_race/bench/runner.py` |
| 4 | `test(bench): add unit and integration tests for workload profiles` | `tests/test_workloads.py` |

---

## Success Criteria

### Verification Commands
```bash
python -m llm_race.bench run --help
# Should show: --workload with choices single-user, chat, multi-agent, high-throughput, stress

python -m pytest tests/test_workloads.py -v
# Should: ALL pass (exit code 0)

python -c "from llm_race.bench.workloads import WORKLOAD_REGISTRY; print(len(WORKLOAD_REGISTRY))"
# Should: 5
```

### Final Checklist
- [x] `llm_race/bench/workloads.py` exists with 5 profiles
- [x] `llm_race/bench/__init__.py` exports workload symbols
- [x] `cli.py` has `--workload` argument
- [x] `runner.py` accepts `workload_profile` parameter
- [x] All tests pass
- [x] Backward compatible (no --workload still works)

---


