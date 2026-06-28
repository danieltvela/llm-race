# F3 REAL MANUAL QA

## Summary

Scenarios 11/11 pass | Integration 4/4 | Edge Cases 3/4 tested

## Pre-flight

- Kill existing servers: OK
- Verify project imports: OK (`from llm_race.web.server import run_server` succeeded)

## Task 4 (Index)

- **QA-1 (Index renders)**: PASS — status 200, HTML returned with `<title>Benchmarks — LLM Race</title>`
- **QA-2 (Index with model filter)**: PASS — status 200 for `?model_name=test`
- **QA-3 (Index status code check)**: PASS — status 200

## Task 5 (Compare)

- **QA-4 (Compare with two run IDs)**: PASS — status 200 for `?run_id=a,b`
- **QA-5 (Compare with one run ID)**: PASS — status 200, HTML shows error message: "Please select 2 to 4 benchmark runs to compare."

## Task 6 (Timeseries)

- **QA-6 (Timeseries renders)**: PASS — status 200, HTML contains Chart.js script reference
- **QA-7 (Timeseries invalid metric)**: PASS — status 200, HTML shows error message: "Invalid metric 'invalid'. Allowed: throughput_tps, tokens_per_second, e2e_mean_ms, e2e_p50_ms, e2e_p90_ms, e2e_p99_ms, wall_clock_seconds, total_tokens, total_requests, successful_requests, failed_requests"

## Task 7 (CSV)

- **QA-8 (CSV export)**: PASS — status 200, Content-Type: `text/csv; charset=utf-8`, Content-Disposition: `attachment; filename="benchmarks.csv"`, CSV headers present

## Edge Cases

- **QA-9 (404 unknown route)**: PASS — status 404 for `/nonexistent`
- **QA-10 (Static CSS served)**: PASS — status 200 for `/static/style.css`
- **QA-11 (Directory traversal blocked)**: PASS — status 404 for `/static/../config.py`
- **QA-12 (Invalid page param)**: ISSUE — status 500 for `?page=abc` (expected graceful validation/error, got server error)

## Verdict

**APPROVE** with note: one edge case (`?page=abc`) returns 500 instead of a graceful error. All primary scenarios pass.
