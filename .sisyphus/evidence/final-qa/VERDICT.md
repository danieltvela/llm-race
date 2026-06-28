F4 VERDICT: APPROVE

Scenarios [5/5 pass]:
- [x] 1. Warmup discarded (evidence: .sisyphus/evidence/final-qa/qa-1-output.txt)
  - Script: qa-1-warmup-discard.py
  - Result: PASS — len(metrics) == 6 (3 measured batches x 2 concurrency)
  - Result: PASS — provider.call_count == 10 (5 total batches x 2 concurrency)

- [x] 2. warmup=0 (evidence: .sisyphus/evidence/final-qa/qa-2-output.txt)
  - Script: qa-2-warmup-zero.py
  - Result: PASS — len(metrics) == 4 (2 measured batches x 2 concurrency)
  - Result: PASS — provider.call_count == 4 (no warmup calls made)

- [x] 3. measured=0 (evidence: .sisyphus/evidence/final-qa/qa-3-output.txt)
  - Script: qa-3-measured-zero.py
  - Result: PASS — len(metrics) == 0 (early return when measured_iterations==0)
  - Result: PASS — provider.call_count == 0 (warmup skipped due to early return)

- [x] 4. CLI help (evidence: .sisyphus/evidence/final-qa/qa-4-cli-help.txt)
  - Command: python3 -m llm_race.bench.cli run --help
  - Verified: --warmup-iterations appears with default: 2
  - Verified: --measured-iterations appears with default: 10

- [x] 5. Tests pass (evidence: .sisyphus/evidence/final-qa/qa-5-test-results.txt)
  - Command: python3 -m pytest tests/test_warmup.py -v
  - Result: 9/9 tests PASSED in 11.41s
  - Tests covered:
    - TestWarmupDiscard::test_warmup_discarded
    - TestWarmupDiscard::test_warmup_zero
    - TestWarmupDiscard::test_measured_zero
    - TestRequestIDs::test_sequential_ids
    - TestRequestIDs::test_ids_across_batches
    - TestDefaults::test_default_warmup
    - TestDefaults::test_default_measured
    - TestCLIArgs::test_cli_defaults
    - TestCLIArgs::test_cli_custom

Issues Found:
- None. All scenarios pass as expected.
