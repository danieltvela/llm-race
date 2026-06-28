# Learnings — issue-10-tests

## timing.py tests

### numpy percentile behavior
- `np.percentile([10,20,30,40,50], 95)` → `48.0` (linear interpolation)
- `np.percentile([10,20,30,40,50], 99)` → `49.6`
- Empty array → use `np.array([])` then check length before calling percentile

### Edge cases
- `compute_latency_stats([])` returns all `0.0` (not None)
- `compute_itl_stats([])` returns all `None` (not 0.0) — different contract
- Single value → all percentiles equal that value
- All same values → all percentiles equal that value

### Float precision
- Always use `pytest.approx()` for float comparisons — numpy can introduce tiny floating point errors (e.g., `0.10000000000000002`)
- Use `abs=0.001` or tighter tolerance for small values

### Test patterns
- Pure functions: no mocking needed, no fixtures required
- `_mock_monotonic` autouse fixture in conftest.py is harmless (doesn't affect numpy-based timing)
- Follow existing pattern: class per function, docstring with input→output example
- Return type checks: verify `isinstance(stats, dict)` and `set(stats.keys()) == expected_keys`
## test_bench_prompts.py — Prompt Generation Tests
- Created 6 unit tests for `generate_prompt(token_approx)` in `llm_race/bench/prompts.py`
- Key finding: `.capitalize()` uppercases first char and lowercases rest — test must check first char is upper after split
- Sentence split logic: `prompt.split(". ")` requires special handling for last element (no trailing `. `)
- Edge cases: token_approx=0 and 1 produce valid (empty/short) strings — no crash
- Total suite: 199 tests pass, 0 regressions
