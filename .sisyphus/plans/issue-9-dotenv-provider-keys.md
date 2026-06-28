# Issue #9: Provider API keys from .env (dotenv + provider key fallback)

## TL;DR

> **Quick Summary**: Add `.env.example`, auto-load `.env` via `python-dotenv` at startup, and ensure all providers read API keys from environment variables instead of hardcoded values.
>
> **Deliverables**:
> - `.env.example` at project root
> - `load_dotenv()` call in `config/__init__.py`
> - `VLLM_API_KEY` env var fallback in `VLLMProvider`
> - Unit test for VLLMProvider env var reading
>
> **Estimated Effort**: Quick
> **Parallel Execution**: YES — 2 waves
> **Critical Path**: Task 3 → Task 4 (test depends on provider fix)

---

## Context

### Original Request

GitHub Issue #9: Provider API keys should be read from environment variables or a `.env` file, not hardcoded.

### Interview Summary

**Key Decisions**:
- `load_dotenv()` placement: `config/__init__.py` (user choice)
- Test strategy: Tests-after (add test for VLLMProvider env var reading)
- `.env.example` only documents **implemented** providers (vllm, lm_studio, mlx_lm, ollama), not forward-looking ones

**Already done** (not in scope):
- `python-dotenv>=1.0,<2.0` already in `requirements.txt` ✅
- `.env` already in `.gitignore` ✅
- `LMStudioProvider`, `MLXLMProvider`, `OllamaProvider` already have `os.environ.get("XXX_API_KEY")` fallbacks ✅

### Metis Review

**Identified Gaps** (addressed):
- **Ordering**: `load_dotenv()` must be called **before** the `os.environ.get()` default-value lines at module level → plan ensures correct placement at top of `config/__init__.py`
- **`.env.example` scope**: Only document vars for existing providers, not imagined future ones
- **VLLMProvider pattern**: Must match exact existing pattern (`api_key or os.environ.get("VLLM_API_KEY")`)
- **Test approach**: Must use `os.environ` manipulation / `patch.dict`, not real API keys

---

## Work Objectives

### Core Objective

Ensure all LLM providers read API keys from environment variables (`.env` or shell env), replacing any hardcoded patterns.

### Concrete Deliverables

- `.env.example` template documenting all project-relevant env vars
- `config/__init__.py` calls `load_dotenv()` at import time
- `VLLMProvider.__init__()` falls back to `VLLM_API_KEY` env var
- Unit test in `tests/test_providers.py` verifying VLLM env var fallback

### Definition of Done

- [ ] `python -c "from llm_race.config import VLLMProvider; p = VLLMProvider(base_url='http://x'); assert p.api_key == 'test-key'"` with `VLLM_API_KEY=test-key` set
- [ ] All existing tests pass: `python -m pytest tests/test_providers.py -v`

### Must Have

- `.env` auto-loaded on startup before any `os.environ.get()` call
- All 4 providers (vllm, lm_studio, mlx_lm, ollama) read API key from env var
- `.env.example` documents every env var used by the project

### Must NOT Have (Guardrails)

- No changes to `create_provider()` function in `config/__init__.py`
- No changes to `LMStudioProvider`, `MLXLMProvider`, `OllamaProvider` (they already work)
- No addition of fake/forward-looking env vars for unimplemented providers
- No real API keys or secrets committed
- No changes to CLI arguments or runner logic

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after
- **Framework**: pytest (already set up)
- **Approach**: Add one test class to existing `tests/test_providers.py`

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Library/Module**: Use Bash (python REPL or pytest) — Import, set env vars, check behavior
- **File verification**: Use Bash `ls`, `cat`, `grep` to confirm file contents

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — all independent, MAX PARALLEL):
├── Task 1: Create .env.example (new file)
├── Task 2: Add load_dotenv() to config/__init__.py
└── Task 3: Add env var fallback to VLLMProvider

Wave 2 (Depends on Wave 1):
└── Task 4: Add unit test for VLLM env var fallback (depends: Task 3)

Wave FINAL:
├── F1: Plan Compliance Audit
├── F2: Code Quality Review
├── F3: Real Manual QA
└── F4: Scope Fidelity Check

Critical Path: Task 3 → Task 4 → F1-F4
Parallel Speedup: ~50% faster (Wave 1 runs 3 tasks in parallel)
```

### Dependency Matrix

- **Task 1**: — — 4
- **Task 2**: — — 4
- **Task 3**: — — 4, 2
- **Task 4**: 3 — F1-F4, 3

### Agent Dispatch Summary

- **Wave 1**: 3 parallel — all → `quick`
- **Wave 2**: 1 task → `unspecified-low`
- **FINAL**: 4 parallel reviewers

---

## TODOs

- [x] 1. Create `.env.example` at project root

  **What to do**:
  - Create `.env.example` file at the project root (`/Users/danielvela/projects/ai/llm-race/.env.example`)
  - Document every env var the project currently uses, with placeholder values
  - Use clear section headers and comments explaining each variable
  - All values must be placeholder/example values, never real secrets
  - Follow this structure:
    ```
    # LLM Race — Environment Configuration
    # Copy this file to .env and fill in your values.

    ## Server Configuration
    LLM_RACE_BASE_URL=http://localhost:8000/v1
    LLM_RACE_MODEL=Qwen3-8B
    LLM_RACE_PROVIDER=vllm
    LLM_RACE_WEB_PORT=8080
    LLM_RACE_WEB_HOST=127.0.0.1

    ## Provider API Keys
    # Set the API key for your chosen provider. Unused ones can be left blank.
    VLLM_API_KEY=
    LMSTUDIO_API_KEY=
    MLXLM_API_KEY=
    OLLAMA_API_KEY=
    ```

  **Must NOT do**:
  - Do NOT include env vars for unimplemented providers (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
  - Do NOT include real API keys or secrets
  - Do NOT create `.env` file itself (only `.env.example`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: New file creation with documented values, trivial and well-defined
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Nothing
  - **Blocked By**: None

  **References**:
  - No pattern references needed (new file)
  - External convention: https://saurabh-khariwal.medium.com/the-importance-of-env-example-and-gitignore-in-your-project-1c6b249d9faa

  **Acceptance Criteria**:
  - [ ] File exists at `.env.example` in project root
  - [ ] Contains all env vars: LLM_RACE_BASE_URL, LLM_RACE_MODEL, LLM_RACE_PROVIDER, LLM_RACE_WEB_PORT, LLM_RACE_WEB_HOST, VLLM_API_KEY, LMSTUDIO_API_KEY, MLXLM_API_KEY, OLLAMA_API_KEY
  - [ ] No real/valid API keys present
  - [ ] File is valid plaintext (no encoding issues)

  **QA Scenarios**:

  ```
  Scenario: .env.example exists and is well-formed
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: test -f .env.example
      2. Run: grep -c "LLM_RACE_BASE_URL" .env.example  # should be 1
      3. Run: grep -c "VLLM_API_KEY" .env.example       # should be 1
      4. Run: grep -c "OPENAI_API_KEY" .env.example      # should be 0 (not implemented)
    Expected Result: All grep counts match expected values. File is parseable.
    Evidence: .sisyphus/evidence/task-1-env-example.txt
  ```

  **Evidence to Capture**:
  - [ ] `.sisyphus/evidence/task-1-env-example.txt` — verification output

  **Commit**: YES
  - Message: `chore: add .env.example with documented env vars`
  - Files: `.env.example`

---

- [x] 2. Add `load_dotenv()` to `config/__init__.py`

  **What to do**:
  - Add `from dotenv import load_dotenv` at the top of `config/__init__.py`
  - Call `load_dotenv()` **immediately after imports, before any `os.environ.get()` calls**
  - Use explicit path: `load_dotenv(PROJECT_ROOT.parent / ".env")` — this guarantees it finds `.env` regardless of CWD
  - The call must be idempotent (safe if `.env` doesn't exist — `load_dotenv` is silent by default)

  **Critical ordering** — the file currently has:
  ```python
  import os
  from pathlib import Path
  from typing import Any
  from llm_race.config.base import Provider

  PROJECT_ROOT = ...   # line 9
  DATA_DIR = ...       # line 10
  DB_PATH = ...        # line 11

  DEFAULT_BASE_URL = os.environ.get(...)  # line 13 — this MUST come AFTER load_dotenv
  ```

  After the change it should be:
  ```python
  import os
  from pathlib import Path
  from typing import Any
  from dotenv import load_dotenv

  from llm_race.config.base import Provider

  PROJECT_ROOT = Path(__file__).resolve().parent.parent
  load_dotenv(PROJECT_ROOT.parent / ".env")

  DATA_DIR = ...
  DB_PATH = ...
  DEFAULT_BASE_URL = os.environ.get(...)
  ...
  ```

  **Must NOT do**:
  - Do NOT remove the existing `import os` (keep both imports)
  - Do NOT change any of the `os.environ.get()` default value lines

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 2-line addition in a single file, well-defined
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Nothing
  - **Blocked By**: None

  **References**:
  - `llm_race/config/__init__.py:1-26` — Current file structure, must insert before line 13

  **Acceptance Criteria**:
  - [ ] `from dotenv import load_dotenv` present in imports
  - [ ] `load_dotenv(PROJECT_ROOT.parent / ".env")` called before any `os.environ.get()` default lines
  - [ ] Python can import module without error: `python -c "from llm_race.config import DEFAULT_BASE_URL"`
  - [ ] Existing tests still pass: `python -m pytest tests/ -x -q`

  **QA Scenarios**:

  ```
  Scenario: .env is loaded and env vars are readable
    Tool: Bash
    Preconditions: Create temporary .env with content "LLM_RACE_TEST_VAR=from_dotenv"
    Steps:
      1. Create temp .env: echo "LLM_RACE_TEST_VAR=from_dotenv" > /tmp/test_llm_race.env
      2. Run: LLM_RACE_TEST_VAR="" python -c "
         from dotenv import load_dotenv
         import os
         load_dotenv('/tmp/test_llm_race.env')
         assert os.environ.get('LLM_RACE_TEST_VAR') == 'from_dotenv'
         print('OK: load_dotenv works')
         "
    Expected Result: Prints "OK: load_dotenv works"
    Evidence: .sisyphus/evidence/task-2-load-dotenv.txt

  Scenario: Module imports without error and defaults still work
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config import DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_PROVIDER; print(f'Base URL: {DEFAULT_BASE_URL}'); print(f'Model: {DEFAULT_MODEL}'); print(f'Provider: {DEFAULT_PROVIDER}')"
    Expected Result: Prints default values (not crashing)
    Evidence: .sisyphus/evidence/task-2-import-defaults.txt
  ```

  **Evidence to Capture**:
  - [ ] `.sisyphus/evidence/task-2-load-dotenv.txt`
  - [ ] `.sisyphus/evidence/task-2-import-defaults.txt`

  **Commit**: YES
  - Message: `feat(config): auto-load .env file on startup via python-dotenv`
  - Files: `llm_race/config/__init__.py`
  - Pre-commit: `python -m pytest tests/ -x -q`

---

- [x] 3. Add `VLLM_API_KEY` env var fallback to `VLLMProvider`

  **What to do**:
  - In `llm_race/config/vllm.py`, modify `VLLMProvider.__init__` to fall back to `VLLM_API_KEY` env var
  - Change line 31 from:
    ```python
    def __init__(self, base_url: str, api_key: str | None = None, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
    ```
    To:
    ```python
    def __init__(self, base_url: str, api_key: str | None = None, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("VLLM_API_KEY")
    ```
  - Add `import os` at the top of the file (if not already present — check current imports)

  **Must NOT do**:
  - Do NOT use `os.getenv()` — must match pattern `os.environ.get("VLLM_API_KEY")` used by other providers
  - Do NOT change any other part of VLLMProvider

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-line change in one method, trivially scoped
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 4 (test depends on this fix)
  - **Blocked By**: None

  **References**:
  - `llm_race/config/vllm.py:22-34` — Current `__init__` to modify
  - `llm_race/config/lm_studio.py:27-30` — Reference pattern: `self.api_key = api_key or os.environ.get("LMSTUDIO_API_KEY")`

  **Acceptance Criteria**:
  - [ ] VLLMProvider reads `VLLM_API_KEY` from env when no explicit api_key passed
  - [ ] `VLLM_API_KEY` not set → `api_key` is `None` (backward compatible)
  - [ ] Explicit `api_key` param still takes priority over env var
  - [ ] Existing tests pass: `python -m pytest tests/test_providers.py -v`

  **QA Scenarios**:

  ```
  Scenario: VLLMProvider reads VLLM_API_KEY from environment
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: VLLM_API_KEY="test-key-from-env" python -c "
         from llm_race.config.vllm import VLLMProvider
         p = VLLMProvider(base_url='http://localhost:8000/v1')
         assert p.api_key == 'test-key-from-env', f'Expected test-key-from-env, got {p.api_key}'
         print('OK: VLLMProvider reads VLLM_API_KEY from env')
         "
    Expected Result: Prints "OK: VLLMProvider reads VLLM_API_KEY from env"
    Evidence: .sisyphus/evidence/task-3-vllm-env-var.txt

  Scenario: Explicit api_key overrides env var
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: VLLM_API_KEY="env-key" python -c "
         from llm_race.config.vllm import VLLMProvider
         p = VLLMProvider(base_url='http://localhost:8000/v1', api_key='explicit-key')
         assert p.api_key == 'explicit-key', f'Expected explicit-key, got {p.api_key}'
         print('OK: explicit api_key takes priority')
         "
    Expected Result: Prints "OK: explicit api_key takes priority"
    Evidence: .sisyphus/evidence/task-3-vllm-explicit-override.txt

  Scenario: No env var set → api_key is None (backward compatibility)
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: env -u VLLM_API_KEY python -c "
         from llm_race.config.vllm import VLLMProvider
         p = VLLMProvider(base_url='http://localhost:8000/v1')
         assert p.api_key is None, f'Expected None, got {p.api_key}'
         print('OK: no VLLM_API_KEY → api_key is None')
         "
    Expected Result: Prints "OK: no VLLM_API_KEY → api_key is None"
    Evidence: .sisyphus/evidence/task-3-vllm-none-fallback.txt
  ```

  **Evidence to Capture**:
  - [ ] `.sisyphus/evidence/task-3-vllm-env-var.txt`
  - [ ] `.sisyphus/evidence/task-3-vllm-explicit-override.txt`
  - [ ] `.sisyphus/evidence/task-3-vllm-none-fallback.txt`

  **Commit**: YES
  - Message: `feat(vllm): add VLLM_API_KEY env var fallback to VLLMProvider`
  - Files: `llm_race/config/vllm.py`
  - Pre-commit: `python -m pytest tests/test_providers.py -v`

---

- [x] 4. Add unit test for VLLMProvider env var fallback

  **What to do**:
  - Add a new test class `TestVLLMProviderEnvVars` to `tests/test_providers.py`
  - Test three scenarios:
    1. `VLLM_API_KEY` set in environment → provider reads it
    2. Explicit `api_key` param overrides env var
    3. No env var → `api_key` is `None`
  - Use `pytest.mark.parametrize` or `os.environ` manipulation via `patch.dict`
  - Follow existing test patterns in `test_providers.py` (use `MagicMock`, `AsyncMock`, etc.)
  - Do NOT test with real HTTP calls — only test the `__init__` logic

  **Must NOT do**:
  - Do NOT modify existing test classes
  - Do NOT add external dependencies
  - Do NOT test with real API keys or network requests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Small, well-defined test addition following existing patterns
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential after Task 3)
  - **Blocks**: Nothing
  - **Blocked By**: Task 3 (VLLMProvider fix must be applied first)

  **References**:
  - `tests/test_providers.py:40-80` — Existing test class `TestVLLMProvider` to follow patterns
  - `llm_race/config/vllm.py:31-34` — Code under test (env var fallback logic)
  - `unittest.mock.patch.dict` — Standard library for manipulating `os.environ` in tests

  **Acceptance Criteria**:
  - [ ] New test class `TestVLLMProviderEnvVars` added to `test_providers.py`
  - [ ] 3 test methods covering: env var read, explicit override, no-env-var
  - [ ] `python -m pytest tests/test_providers.py::TestVLLMProviderEnvVars -v` → 3/3 pass

  **QA Scenarios**:

  ```
  Scenario: New test class runs and passes all 3 tests
    Tool: Bash
    Preconditions: Tasks 1-3 completed
    Steps:
      1. Run: python -m pytest tests/test_providers.py::TestVLLMProviderEnvVars -v
    Expected Result: 3 passed, 0 failed
    Evidence: .sisyphus/evidence/task-4-test-results.txt

  Scenario: All provider tests still pass (no regressions)
    Tool: Bash
    Preconditions: Tasks 1-3 completed
    Steps:
      1. Run: python -m pytest tests/test_providers.py -v
    Expected Result: All tests pass (existing + new)
    Evidence: .sisyphus/evidence/task-4-all-tests-pass.txt
  ```

  **Evidence to Capture**:
  - [ ] `.sisyphus/evidence/task-4-test-results.txt`
  - [ ] `.sisyphus/evidence/task-4-all-tests-pass.txt`

  **Commit**: YES
  - Message: `test(vllm): add unit tests for VLLM_API_KEY env var fallback`
  - Files: `tests/test_providers.py`
  - Pre-commit: `python -m pytest tests/test_providers.py -v`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. Verify each "Must Have" is implemented. Check that no "Must NOT Have" violations exist (particularly: no `create_provider()` changes, no edits to LMStudio/MLXLM/Ollama providers). Verify `.env.example` exists and has no real keys. Verify `load_dotenv()` is called before `os.environ.get()` lines. Verify VLLMProvider has `os.environ.get("VLLM_API_KEY")`.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/ -x -q`. Review changes for: `import os` present in vllm.py, `os.environ.get` vs `os.getenv` consistency, proper dotenv import path. Check for commented-out code or real API keys.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute EVERY QA scenario from EVERY task. Start from clean state (no `.env` file). Test cross-task integration: create a `.env` with `VLLM_API_KEY=test-key-qa`, run import check, verify VLLMProvider picks it up. Test edge case: `.env` file does not exist.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1. Check "Must NOT do" compliance for Tasks 1-4. Detect cross-task contamination. Verify no files outside `.env.example`, `config/__init__.py`, `config/vllm.py`, `tests/test_providers.py` were modified.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **1**: `chore: add .env.example with documented env vars` — `.env.example`
- **2**: `feat(config): auto-load .env file on startup via python-dotenv` — `llm_race/config/__init__.py`
- **3**: `feat(vllm): add VLLM_API_KEY env var fallback to VLLMProvider` — `llm_race/config/vllm.py`
- **4**: `test(vllm): add unit tests for VLLM_API_KEY env var fallback` — `tests/test_providers.py`

---

## Success Criteria

### Verification Commands
```bash
# Full test suite
python -m pytest tests/ -x -q

# Provider-specific tests
python -m pytest tests/test_providers.py -v

# Verify .env.example exists
test -f .env.example

# Verify load_dotenv works
VLLM_API_KEY="test-qa" python -c "
from llm_race.config.vllm import VLLMProvider
p = VLLMProvider(base_url='http://localhost:8000/v1')
assert p.api_key == 'test-qa'
print('Full integration: OK')
"
```

### Final Checklist
- [ ] `.env.example` created with all env vars documented
- [ ] `load_dotenv()` called at top of `config/__init__.py` (before defaults)
- [ ] `VLLMProvider` has `os.environ.get("VLLM_API_KEY")` fallback
- [ ] All existing tests pass
- [ ] New env var test class passes
- [ ] No real API keys committed
- [ ] No changes to providers other than vllm
- [ ] No changes to `create_provider()`
