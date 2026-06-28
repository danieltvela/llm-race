# QA Verdict — Issue #8 presets.json

## Scenarios 10/10 pass | Integration 10/10 | VERDICT: APPROVE

### T1: presets.json integrity
| # | Scenario | Result |
|---|----------|--------|
| 1 | 8 presets, unique keys, all have key field | **PASS** |
| 2 | Print all keys | **PASS** — 8 keys match expected list |

### T2: presets.py loader
| # | Scenario | Result |
|---|----------|--------|
| 3 | load_preset('qwen3-8b-vllm') returns correct dict | **PASS** |
| 4 | load_preset('nonexistent') raises KeyError with available keys | **PASS** |
| 5 | list_presets() returns 8 presets | **PASS** |

### T3: CLI integration
| # | Scenario | Result |
|---|----------|--------|
| 6 | run --help shows --preset and --list-presets | **PASS** |
| 7 | run --list-presets prints 8 presets + header | **PASS** |
| 8 | run --preset nonexistent exits 1 with error | **PASS** |

### T4: Tests
| # | Scenario | Result |
|---|----------|--------|
| 9 | pytest tests/test_presets.py -v → 15 passed | **PASS** |
| 10 | pytest full suite → 163 passed, no regressions | **PASS** |

## Observations
- `libgomp: Affinity not supported on this configuration` warning appears on CLI invocations (environment-specific, unrelated to functionality).
- The `presets.json` structure is `{ "presets": [...] }` (dict wrapper), not a raw list — the loader handles this correctly.
- All expected keys present: qwen3-8b-vllm, qwen3-27b-fp8-vllm, llama3.2-3b-lm-studio, mistral-7b-lm-studio, llama3.2-3b-mlx, mistral-7b-mlx, llama3.2-ollama, mistral-ollama.

## Code Quality Review — F2 Full Test Suite & File Review

### Test Results
- `python3 -m pytest` → **163 passed, 0 failed, 3097 warnings** (14.94s)
- `python3 -m pytest tests/test_presets.py -v` → **15 passed** (0.64s)
- No regressions detected.

### Checks Performed
| Check | Result | Notes |
|-------|--------|-------|
| Bare `except:` clauses | **PASS** | None found in any changed file. |
| Type errors / missing hints | **PASS** | All public functions in `presets.py` and `cli.py` have type hints. |
| Unused imports | **PASS** | All imports are used in `presets.py`, `test_presets.py`, `cli.py`. |
| Test quality | **PASS with minor issues** | Tests are meaningful; one weak smoke test noted. |
| Evidence files exist | **PASS** | Evidence files present and mostly meaningful. |
| `presets.json` data correctness | **PASS** | 8 presets, unique keys, supported providers. |

### Issues Found (5 minor)

1. **`presets.py:48` — Fragile `available` list construction**
   - `available = [p["key"] for p in presets]` will crash with `KeyError` if any preset is missing the `"key"` field.
   - The validation (lines 28-35) only logs a warning and does not reject malformed presets.
   - **Impact**: MEDIUM — unintended exception before the helpful `KeyError` message.

2. **`presets.py:27-35` — Non-blocking validation**
   - Missing required fields trigger a `logger.warning` but the preset is still included in the cached list.
   - **Impact**: LOW — allows partially invalid data to propagate.

3. **`cli.py:112-113` — `_is_default` ambiguity**
   - Cannot distinguish "user didn't pass the flag" from "user explicitly passed the same value as the default".
   - Example: `--provider vllm` (same as default) would still be overridden by a preset's provider.
   - **Impact**: LOW — known argparse limitation.

4. **`tests/test_presets.py:136-139` — Weak smoke test**
   - `test_cli_preset_smoke_test` passes `--preset` alongside `--help`, so preset resolution is never exercised.
   - **Impact**: LOW — test docstring is honest, but coverage is minimal.

5. **`.sisyphus/evidence/task-2-cli-help.txt` — Stale evidence**
   - Shows CLI help *without* `--preset` / `--list-presets` flags.
   - Contradicts actual implementation and `task-3-help.txt`.
   - **Impact**: LOW — confusing if referenced later.

### Verdict
Tests **163 pass / 0 fail** | Issues **5 (all minor)** | **VERDICT: APPROVE**
