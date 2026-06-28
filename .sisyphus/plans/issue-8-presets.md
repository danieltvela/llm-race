# Issue #8 — Create presets.json for Predefined Model/Provider Combos

## TL;DR

> **Quick Summary**: Extend the existing `presets.json` with slug keys, create a preset loader module, and wire `--preset` into the CLI so users can run benchmarks with a single short flag like `--preset qwen3-8b-vllm`.
>
> **Deliverables**:
> - Extended `presets.json` with `key` fields for all 8 presets
> - New `config/presets.py` loader module (`load_preset()`, `list_presets()`)
> - `--preset` CLI flag with post-parse resolution (explicit flags win over preset)
> - Unit tests for loading + CLI integration
>
> **Estimated Effort**: Quick
> **Parallel Execution**: NO — sequential (T1→T2→T3, then T4 in parallel with T3's completion)
> **Critical Path**: T1 → T2 → T3 → T4 → F1-F3

---

## Context

### Original Request
[Issue #8](https://github.com/danieltvela/llm-race/issues/8): Create `presets.json` with predefined model/provider combos and wire `--preset` into the CLI.

### Interview Summary
**Key Decisions**:
- No cloud provider presets (OpenAI/Anthropic providers don't exist yet) — scope to existing 4 providers only
- Presets contain only connection info (provider, model, base_url) — no concurrency/prompt_length defaults
- Explicit CLI flags always override preset values
- Slug-style naming: `--preset qwen3-8b-vllm` (add `key` field to each preset)
- Tests-after strategy

**Research Findings**:
- `presets.json` already exists at `llm_race/config/presets.json` with 8 local presets
- Current schema: `{name, provider, model, base_url, api_key_env, description}` — no `key` field
- CLI has no `--preset` flag — all params passed individually
- Provider factory (`create_provider`) supports: vllm, lm_studio, mlx_lm, ollama
- `--workload` profile already overrides `--concurrency`/`--prompt-lengths` — orthogonal to presets

### Metis Review
**Identified Gaps** (addressed):
- OpenAI/Anthropic provider gap: explicitly out of scope — user confirmed
- Preset-vs-workload overlap: none — presets set connection info, workloads set benchmark params
- Preset-vs-CLI override semantics: resolved — explicit flags always win
- Preset key naming: resolved — add `key` field to each preset

---

## Work Objectives

### Core Objective
Add `--preset CLI` flag backed by `presets.json` so users can run benchmarks with a single short identifier.

### Concrete Deliverables
- `llm_race/config/presets.json` — extended with `key` fields
- `llm_race/config/presets.py` — `load_preset(key)` and `list_presets()`
- `llm_race/bench/cli.py` — `--preset` argument + post-parse merge logic

### Definition of Done
- [x] `python -m pytest tests/test_presets.py -v` — all tests pass
- [x] `python -m pytest` — 148+ tests pass (no regressions)
- [x] `python -m llm_race run --help` shows `--preset` flag
- [x] `python -m llm_race run --preset qwen3-8b-vllm` resolves correctly (dry-run check)

### Must Have
- `--preset <key>` loads matching preset from `presets.json`
- Explicit `--provider`/`--model`/`--base-url` override preset values
- `list_presets()` returns all available presets
- Unknown preset key raises clear error message

### Must NOT Have (Guardrails)
- No OpenAI/Anthropic provider implementations added
- No changes to `presets.json` schema beyond adding `key` field
- No changes to `--workload`, `--concurrency`, `--prompt-lengths` behavior
- No changes to benchmark runner logic
- No schema changes beyond adding `key`

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after
- **Framework**: pytest
- **Coverage**: Unit tests for `load_preset`, `list_presets`, CLI integration

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario}.{ext}`.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (sequential — data first):
├── T1: presets.json — add key field to all presets [quick]
└── T2: config/presets.py — loader module [quick]

Wave 2 (starts after T2):
├── T3: cli.py — --preset flag + resolution [quick]
└── T4: Tests for preset loading + CLI [quick]

Wave FINAL (parallel verification):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality + full test suite (unspecified-high)
└── F3: Real manual QA (unspecified-high)
```

---

## TODOs

- [x] 1. Add `key` fields to all presets in `presets.json`

  **What to do**:
  - Read the existing 8 presets in `llm_race/config/presets.json`
  - Add a `key` field to each object with a short slug identifier
  - Preserve all existing fields exactly as-is

  Preset keys to add:
  | Name | key |
  |------|-----|
  | Qwen3-8B on vLLM | `qwen3-8b-vllm` |
  | Qwen3-27B-FP8 on vLLM | `qwen3-27b-fp8-vllm` |
  | Llama-3.2-3B on LM Studio | `llama3.2-3b-lm-studio` |
  | Mistral-7B on LM Studio | `mistral-7b-lm-studio` |
  | Llama-3.2-3B on MLX | `llama3.2-3b-mlx` |
  | Mistral-7B on MLX | `mistral-7b-mlx` |
  | Llama3.2 via Ollama | `llama3.2-ollama` |
  | Mistral via Ollama | `mistral-ollama` |

  **Must NOT do**:
  - Do not change existing field names or values
  - Do not add fields other than `key`
  - Do not change the JSON structure

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T2
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `presets.json` — 8 presets each have a `key` field
  - [ ] JSON remains valid (parseable by `json.load`)
  - [ ] All existing fields preserved

  **QA Scenarios**:

  ```
  Scenario: Validate JSON structure with keys
    Tool: Bash
    Preconditions: presets.json exists
    Steps:
      1. Run: python3 -c "
  import json
  with open('llm_race/config/presets.json') as f:
      data = json.load(f)
  assert len(data['presets']) == 8, f'Expected 8 presets, got {len(data[\"presets\"])}'
  keys = [p['key'] for p in data['presets']]
  assert len(keys) == len(set(keys)), 'Duplicate keys found'
  print(f'OK: {len(keys)} presets with unique keys')
  for p in data['presets']:
      assert all(k in p for k in ['key','name','provider','model']), f'Missing required field in {p[\"name\"]}'
      print(f'  {p[\"key\"]}: {p[\"name\"]}')
  "
    Expected Result: OK: 8 presets with unique keys, each with required fields
    Evidence: .sisyphus/evidence/task-1-validate-presets.txt
  ```

  **Commit**: YES
  - Message: `chore(config): add key field to all presets`
  - Files: `llm_race/config/presets.json`

---

- [x] 2. Create `config/presets.py` — preset loader module

  **What to do**:
  - Create `llm_race/config/presets.py`
  - Implement `load_preset(key: str) -> dict`:
    - Reads `presets.json` (use `PROJECT_ROOT` from `config/__init__.py` or resolve relative to the module)
    - Finds preset by `key` field
    - Raises `KeyError` with available keys on unknown key
  - Implement `list_presets() -> list[dict]`:
    - Returns all preset dicts from the JSON file
  - Validate each preset has required fields: `key`, `name`, `provider`, `model`, `base_url`
  - Re-export from `config/__init__.py` for discoverability

  **Must NOT do**:
  - Do not add any business logic or heavy dependencies
  - Pure data access functions only
  - No changes to existing config files or providers

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T3, T4
  - **Blocked By**: T1 (presets.json schema)

  **References**:
  - `llm_race/config/__init__.py:1-30` — Import pattern, `PROJECT_ROOT` resolver
  - `llm_race/config/__init__.py:32-61` — `create_provider()` as pattern for public API functions
  - `llm_race/config/presets.json` — Data file to read

  **Acceptance Criteria**:
  - [ ] `python3 -c "from llm_race.config.presets import load_preset, list_presets; print('OK')"` — imports cleanly
  - [ ] `python3 -c "from llm_race.config import load_preset, list_presets; print('OK')"` — re-exported from __init__
  - [ ] `load_preset('qwen3-8b-vllm')` returns the correct preset dict
  - [ ] `load_preset('nonexistent')` raises `KeyError`
  - [ ] `list_presets()` returns all 8 presets

  **QA Scenarios**:

  ```
  Scenario: Happy path — load known preset
    Tool: Bash
    Preconditions: presets.py exists
    Steps:
      1. python3 -c "
  from llm_race.config.presets import load_preset
  p = load_preset('qwen3-8b-vllm')
  assert p['key'] == 'qwen3-8b-vllm'
  assert p['provider'] == 'vllm'
  assert p['model'] == 'Qwen3-8B'
  print(f'OK: loaded {p[\"key\"]} -> {p[\"provider\"]}/{p[\"model\"]}')
  "
    Expected Result: OK: loaded qwen3-8b-vllm -> vllm/Qwen3-8B
    Evidence: .sisyphus/evidence/task-2-load-preset.txt

  Scenario: Error — unknown preset key
    Tool: Bash
    Preconditions: presets.py exists
    Steps:
      1. python3 -c "
  from llm_race.config.presets import load_preset
  try:
      load_preset('nonexistent')
      print('FAIL: no error raised')
  except KeyError as e:
      print(f'OK: KeyError raised with message: {e}')
  "
    Expected Result: OK: KeyError raised with message listing available keys
    Evidence: .sisyphus/evidence/task-2-unknown-key.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add presets.py loader module`
  - Files: `llm_race/config/presets.py`, `llm_race/config/__init__.py`

---

- [x] 3. Wire `--preset` into CLI with post-parse resolution

  **What to do**:
  - Add `--preset` argument to the `run` subparser in `cli.py`:
    - `type=str`, `default=None`
    - Help text: `"Load preset config (use --list-presets to see available)"`
  - After `parse_args()`, add preset resolution block. The key insight: compare each CLI arg against its module-level default; if it matches the default AND the preset has a value, use the preset instead. Wrap in try/except to catch unknown presets:
    ```python
    if args.preset:
        try:
            from llm_race.config import list_presets
            from llm_race.config.presets import load_preset
            preset = load_preset(args.preset)
        except KeyError:
            print(f"Error: unknown preset {args.preset!r}. Available presets:")
            for p in list_presets():
                print(f"  {p['key']}: {p['name']} ({p['provider']})")
            sys.exit(1)
    
        # Preset acts as defaults; explicit CLI flags override
        def _is_default(val: str, default: str) -> bool:
            return val == default
    
        if _is_default(args.provider, DEFAULT_PROVIDER) and "provider" in preset:
            args.provider = preset["provider"]
        if _is_default(args.model, DEFAULT_MODEL) and "model" in preset:
            args.model = preset["model"]
        if _is_default(args.base_url, DEFAULT_BASE_URL) and "base_url" in preset:
            args.base_url = preset["base_url"]
    ```
  - Add `--list-presets` flag on the `run` subparser:
    - `action="store_true"`
    - When set: call `list_presets()`, print each preset as `key: name (provider/model)`, then `sys.exit(0)`
  - Update the provider_kwargs block to use the resolved `args.provider` and `args.base_url` (they're already used — no change needed since we mutate args directly)

  **Must NOT do**:
  - Do not change `--workload`, `--concurrency`, `--prompt-lengths` behavior
  - Do not change the `run_benchmarks()` call signature
  - Do not modify provider implementations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T4
  - **Blocked By**: T2 (presets.py)

  **References**:
  - `llm_race/bench/cli.py:27-135` — Full CLI structure to modify
  - `llm_race/bench/cli.py:92-99` — Provider creation block (uses resolved args)

  **Acceptance Criteria**:
  - [ ] `python -m llm_race run --help` shows `--preset` and `--list-presets`
  - [ ] `python -m llm_race run --list-presets` prints all presets and exits
  - [ ] `python -m llm_race run --preset qwen3-8b-vllm` → loads preset values
  - [ ] `python -m llm_race run --preset qwen3-8b-vllm --model test-model` → model is "test-model" (explicit wins)
  - [ ] `python -m llm_race run --preset nonexistent` → clear error message

  **QA Scenarios**:

  ```
  Scenario: --help shows preset flags
    Tool: Bash
    Steps:
      1. python3 -m llm_race run --help 2>&1 | grep -E "(\-\-preset|\-\-list-presets)"
    Expected Result: Output contains both --preset PRESET and --list-presets
    Evidence: .sisyphus/evidence/task-3-help.txt

  Scenario: --list-presets prints preset table
    Tool: Bash
    Steps:
      1. python3 -m llm_race run --list-presets 2>&1
    Expected Result: Prints all 8 presets with key, provider, model — exits code 0
    Evidence: .sisyphus/evidence/task-3-list-presets.txt

  Scenario: --preset unknown key shows error
    Tool: Bash
    Steps:
      1. python3 -m llm_race run --preset nonexistent --no-db 2>&1; echo "exit=$?"
    Expected Result: Prints "Error: unknown preset 'nonexistent'" and lists available keys, exit code 1
    Evidence: .sisyphus/evidence/task-3-unknown-preset.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): add --preset flag with post-parse resolution`
  - Files: `llm_race/bench/cli.py`

---

- [x] 4. Write unit tests for preset loading and CLI integration

  **What to do**:
  - Create `tests/test_presets.py`
  - Test `load_preset()` — known key returns correct dict
  - Test `load_preset()` — unknown key raises `KeyError`
  - Test `list_presets()` — returns all 8 presets
  - Test `--preset` flag shows in help
  - Test `--list-presets` flag prints presets
  - Test `--preset` + explicit `--model` override behavior (mock or integration)

  **Must NOT do**:
  - Do not modify existing tests
  - Do not test deep benchmark execution

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: T2, T3

  **References**:
  - `tests/test_workloads.py` — Test structure patterns to follow
  - `tests/test_db_saver.py` — Another test module pattern

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/test_presets.py -v` — all tests pass
  - [ ] `python -m pytest` — no regressions

  **QA Scenarios**:

  ```
  Scenario: All tests pass
    Tool: Bash
    Steps:
      1. python3 -m pytest tests/test_presets.py -v 2>&1 | tail -20
    Expected Result: All tests PASSED
    Evidence: .sisyphus/evidence/task-4-test-results.txt
  ```

  **Commit**: YES
  - Message: `test(config): add unit tests for preset loader and CLI`
  - Files: `tests/test_presets.py`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in `.sisyphus/evidence/`.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality + Full Test Suite** — `unspecified-high`
  Run `python -m pytest`. Review changed files for: bare `except:`, type errors, unused imports, test quality.
  Output: `Tests [N pass/N fail] | Issues [N] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute every QA scenario from every task. Test real CLI behavior: `--preset` resolution, `--list-presets` output, unknown key error.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

---

## Commit Strategy

- **T1**: `chore(config): add key field to all presets` — `presets.json`
- **T2**: `feat(config): add presets.py loader module` — `presets.py`, `config/__init__.py`
- **T3**: `feat(cli): add --preset flag with post-parse resolution` — `cli.py`
- **T4**: `test(config): add unit tests for preset loader and CLI` — `test_presets.py`

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/test_presets.py -v
# Expected: all tests pass

python -m pytest
# Expected: 148+ tests pass (no regressions)

python -m llm_race run --help
# Expected: shows --preset and --list-presets flags

python -m llm_race run --list-presets
# Expected: prints all 8 presets
```

### Final Checklist
- [ ] `presets.json` — all 8 presets have unique `key` fields
- [ ] `load_preset(key)` — returns correct preset for known keys
- [ ] `load_preset(key)` — raises `KeyError` for unknown keys
- [ ] `--preset` — loads preset and resolves values correctly
- [ ] Explicit flags override preset values
- [ ] All pre-existing tests still pass
