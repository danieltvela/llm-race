# F3: Scope Fidelity Check — Issue #3 Workload Profiles

## Tasks Verified

### Task 1 (workloads.py) — COMPLIANT
- [x] ALL 5 profiles exist with correct concurrency levels:
  - single-user: [1] ✓
  - chat: [1] ✓
  - multi-agent: [4, 8, 16] ✓
  - high-throughput: [32, 64, 128] ✓
  - stress: [256, 512] ✓
- [x] All profiles have DEFAULT_PROMPT_LENGTHS = [64, 512, 2048, 4096] ✓
- [x] `get_workload()` raises `ValueError` on invalid names ✓

### Task 2 (__init__.py) — COMPLIANT
- [x] Exports all workload symbols: `WorkloadProfile`, `WORKLOAD_REGISTRY`, `get_workload`, `SINGLE_USER`, `CHAT`, `MULTI_AGENT`, `HIGH_THROUGHPUT`, `STRESS` ✓

### Task 3 (CLI + runner) — COMPLIANT
- [x] `--workload` arg with choices from `WORKLOAD_REGISTRY` ✓
- [x] When `--workload` is set, `--concurrency` and `--prompt-lengths` are overridden ✓
- [x] `runner.run_benchmarks()` has `workload_profile` parameter ✓
- [x] Backward compatible when `--workload` is not used ✓

### Task 4 (tests) — COMPLIANT
- [x] 18 tests pass covering registry, get_workload, CLI, runner ✓

## Contamination Check

### Forbidden Patterns Search
```bash
grep -rn "context.*growth\|warmup\|web.*viewer\|provider.*change\|schema.*change" llm_race/bench/ tests/test_workloads.py --include="*.py"
```

**Result**: 2 matches found in `llm_race/bench/workloads.py` lines 44 and 46.

**Analysis**: Both matches are in the `CHAT` profile's *description* and *behavior* string fields only:
- Line 44: `description="Conversational flow with context growth"`
- Line 46: `behavior="conversational (context growth not simulated yet)"`

These are explicitly allowed by the plan (see plan lines 152 and 161: "Conversational flow with context growth" description, and guardrail "Do NOT implement context growth for chat"). The code does **not** implement any context growth simulation — it merely documents that it is not yet simulated. **This is NOT scope creep.**

### Git Diff Summary
```
llm_race/bench/__init__.py  |  23 +++++++
llm_race/bench/cli.py       |  23 ++++++-
llm_race/bench/runner.py    |   3 +
llm_race/bench/workloads.py |  87 +++++++++++++++++++++++++++
tests/test_workloads.py     | 142 +++++++++++++++++++++++++++++++++++++++++++
5 files changed, 276 insertions(+), 2 deletions(-)
```

**Files touched**: Exactly the 5 files specified in the plan deliverables. No additional files modified.

## Final Verdict

**Tasks [4/4 compliant] | Contamination [CLEAN/0 issues]**

- Task 1: COMPLIANT
- Task 2: COMPLIANT
- Task 3: COMPLIANT
- Task 4: COMPLIANT

**VERDICT: APPROVE**
