# Add More LLM Providers (LM Studio, mlx-lm, Ollama)

## TL;DR

> **Quick Summary**: Implement 3 new LLM provider classes (LM Studio, mlx-lm, Ollama) that extend the Provider ABC, add a non-streaming `complete()` method to the base class and all providers, create `presets.json`, and add unit tests with mocked HTTP responses.
>
> **Deliverables**:
> - `llm_race/config/lm_studio.py` — LM Studio provider (OpenAI-compatible)
> - `llm_race/config/mlx_lm.py` — mlx-lm provider (OpenAI-compatible)
> - `llm_race/config/ollama.py` — Ollama provider (OpenAI-compatible endpoint)
> - `llm_race/config/base.py` — Updated with `complete()` abstract method
> - `llm_race/config/vllm.py` — Updated with `complete()` implementation
> - `llm_race/config/__init__.py` — Updated factory with new providers
> - `llm_race/config/presets.json` — Predefined model/provider combos
> - `tests/test_providers.py` — Unit tests for all providers
>
> **Estimated Effort**: Medium (~2-3 hours)
> **Parallel Execution**: YES — 3 waves, up to 4 parallel tasks
> **Critical Path**: T1 (base class) → T3-T6 (providers) → T7-T11 (registration + tests)

---

## Context

### Original Request
Issue #7: Add more LLM providers (LM Studio, mlx-lm, Ollama) to the benchmarking tool. Currently only vLLM is implemented.

### Interview Summary
**Key Discussions**:
- **Providers**: LM Studio, mlx-lm, and Ollama (confirmed from issue body over title)
- **`complete()` method**: Add abstract method to `Provider` base class and implement in ALL providers (including existing vLLM)
- **Ollama API**: Use OpenAI-compatible endpoint `/v1/chat/completions` (consistent with other providers)
- **Tests**: Include unit tests with httpx mocking
- **Presets.json**: Create with predefined model/provider combinations
- **Scope OUT**: Runner, CLI, and web viewer changes

**Research Findings**:
- All 3 providers support an OpenAI-compatible chat completions endpoint
- LM Studio exposes API at `http://localhost:1234/v1` by default
- mlx-lm exposes API at `http://localhost:8080/v1` by default
- Ollama supports `/v1/chat/completions` since v0.1.32 at `http://localhost:11434/v1`
- Existing SSE utility (`iter_sse_events`) in `llm_race/utils/sse.py` is reused for streaming
- Non-streaming `complete()` reads a single JSON response body, no SSE parsing needed

### Metis Review
**Identified Gaps** (addressed):
- **StreamResult for non-streaming**: `inter_token_latencies` and ITL stats fields will be `[]`/`None` for `complete()` — already handled by existing code that uses `.get()` defaults
- **No existing provider tests**: New test file `test_providers.py` will follow patterns from existing tests
- **complete() usage**: Not used by runner currently — purely for API completeness / direct usage, but consistent with AGENTS.md spec

---

## Work Objectives

### Core Objective
Implement 3 new LLM providers (LM Studio, mlx-lm, Ollama) extending `Provider`, add `complete()` to base class and all providers, register in factory, and add unit tests.

### Concrete Deliverables
- 3 new provider files in `llm_race/config/`
- Updated `base.py` with `complete()` abstract method
- Updated `vllm.py` with `complete()` implementation
- Updated `__init__.py` factory with new provider types
- `presets.json` with recommended model/provider combos
- `tests/test_providers.py` with mocked unit tests

### Definition of Done
- [x] `python -c "from llm_race.config import create_provider; p=create_provider('lm_studio', base_url='http://localhost:1234/v1'); print(type(p).__name__)"` → prints `LMStudioProvider`
- [x] Same for `mlx_lm` → `MLXLMProvider` and `ollama` → `OllamaProvider`
- [x] `python -m pytest tests/test_providers.py -v` → all tests pass
- [ ] `python -c "from llm_race.config.base import Provider; print(hasattr(Provider, 'complete'))"` → True
- [x] `cat llm_race/config/presets.json | python -m json.tool` → valid JSON

### Must Have
- Each provider extends `Provider` and implements both `stream_complete()` and `complete()`
- API keys read from env vars (case-insensitive, with sensible defaults)
- All 3 providers registered in `create_provider()` factory
- Unit tests with mocked httpx for all providers (streaming + non-streaming)
- `presets.json` with at least 2 model entries per provider

### Must NOT Have (Guardrails)
- NO changes to runner (`llm_race/bench/runner.py`)
- NO changes to CLI (`llm_race/bench/cli.py`)
- NO changes to web viewer (`llm_race/web/`)
- NO integration tests requiring real API endpoints
- NO hardcoded credentials or API keys in source code

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: YES (pytest in `tests/`)
- **Automated tests**: YES (tests-after implementation)
- **Framework**: pytest with httpx mocking (using `respx` or manual `httpx.MockTransport`)
- **Coverage**: Each provider tested for both streaming success, streaming error, non-streaming success, non-streaming error

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Provider tests**: `python -m pytest tests/test_providers.py -v --tb=short`
- **Factory registration**: Python one-liner to instantiate each provider
- **Module import**: `python -c "from llm_race.config import lm_studio, mlx_lm, ollama"`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — 2 parallel tasks):
├── T1: Add complete() abstract method to Provider base class [quick]
└── T2: Create presets.json with model/provider combos [quick]

Wave 2 (Provider implementations — 4 parallel, all depend on T1):
├── T3: Implement complete() in VLLMProvider [quick]
├── T4: Create LMStudioProvider [medium]
├── T5: Create MLXLMProvider [medium]
└── T6: Create OllamaProvider [medium]

Wave 3 (Integration + Tests — 5 parallel):
├── T7: Register all providers in create_provider() factory [quick]
├── T8: Unit tests for VLLMProvider complete() [quick]
├── T9: Unit tests for LMStudioProvider [quick]
├── T10: Unit tests for MLXLMProvider [quick]
└── T11: Unit tests for OllamaProvider [quick]

Wave FINAL (Verification — 2 parallel):
├── F1: Plan compliance + scope fidelity audit
└── F2: Full test suite run + manual QA

Critical Path: T1 → T4 → T9 → F1/F2
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 3)
```

### Dependency Matrix

- **T1**: - (independent) — blocks T3, T4, T5, T6
- **T2**: - (independent) — no blockers
- **T3**: T1 — blocks T7
- **T4**: T1 — blocks T7, T9
- **T5**: T1 — blocks T7, T10
- **T6**: T1 — blocks T7, T11
- **T7**: T3, T4, T5, T6 — blocks none
- **T8**: T3 — blocks none
- **T9**: T4 — blocks none
- **T10**: T5 — blocks none
- **T11**: T6 — blocks none

### Agent Dispatch Summary

- **Wave 1**: 2 × `quick`
- **Wave 2**: 1 × `quick` + 3 × `unspecified-high`
- **Wave 3**: 5 × `quick`
- **FINAL**: 2 × `unspecified-high`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

- [x] 1. Add `complete()` abstract method to `Provider` base class

  **What to do**:
  - Add abstract method `complete()` to `Provider` class in `llm_race/config/base.py` with same signature as `stream_complete()` but no `client` parameter (non-streaming doesn't need external client passthrough as much — but keep it for consistency)
  - Method should send a non-streaming POST request, parse the single JSON response, and return `asdict(StreamResult(...))` with `inter_token_latencies=[]` and ITL stats as `None`
  - Update `StreamResult` docstring to clarify that `inter_token_latencies` is empty for non-streaming calls
  - Import `asyncio`, `time`, `httpx` if not already imported

  **Must NOT do**:
  - Do NOT change the `stream_complete()` signature
  - Do NOT remove the `client` parameter from `complete()` — keep API consistent

  **Recommended Agent Profile**:
  - **Category**: `quick` — single file, well-defined change
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2)
  - **Parallel Group**: Wave 1 (with T2)
  - **Blocks**: T3, T4, T5, T6
  - **Blocked By**: None

  **References**:
  - `llm_race/config/base.py` — Current Provider ABC and StreamResult dataclass
  - `llm_race/utils/sse.py` — Existing SSE parser (not directly needed but shows project pattern)

  **Acceptance Criteria**:
- [x] `python -c "from llm_race.config.base import Provider; print(hasattr(Provider, 'complete'))"` → True
  - [ ] `python -c "from llm_race.config.base import Provider; print(Provider.complete.__isabstractmethod__)"` → True

  **QA Scenarios**:

  ```
  Scenario: Provider base class has complete() abstract method
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.base import Provider; print(hasattr(Provider, 'complete'))"
    Expected Result: Output is "True"
    Evidence: .sisyphus/evidence/task-1-has-complete.txt

  Scenario: complete() is abstract (cannot instantiate Provider directly)
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.base import Provider; Provider()" 2>&1
    Expected Result: TypeError (Can't instantiate abstract class Provider with abstract method complete)
    Evidence: .sisyphus/evidence/task-1-abstract-check.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add abstract complete() method to Provider base class`
  - Files: `llm_race/config/base.py`

- [x] 2. Create `presets.json` with model/provider combinations

  **What to do**:
  - Create `llm_race/config/presets.json` with a `presets` array of objects
  - Each preset has: `name`, `provider`, `model`, `base_url` (optional), `api_key_env` (env var name), `description`
  - Include at least 2 entries per provider (vLLM, LM Studio, mlx-lm, Ollama)
  - Follow the format described in AGENTS.md: "Predefined model/provider combos to test"
  - Example entries:
    - vLLM: `qwen3-8b`, `qwen3-27b-fp8`
    - LM Studio: `llama-3.2-3b`, `mistral-7b`
    - mlx-lm: `mlx-community/Llama-3.2-3B`, `mlx-community/Mistral-7B`
    - Ollama: `llama3.2`, `mistral`

  **Must NOT do**:
  - Do NOT include API keys in the file
  - Do NOT include sensitive or hardcoded credentials

  **Recommended Agent Profile**:
  - **Category**: `quick` — simple JSON file creation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T1)
  - **Parallel Group**: Wave 1 (with T1)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - AGENTS.md: mentions `presets.json` under project architecture
  - Common presets from README: `qwen3.6-27b-fp8`, etc.

  **Acceptance Criteria**:
  - [ ] `python -m json.tool llm_race/config/presets.json` → exits 0
  - [ ] `python -c "import json; d=json.load(open('llm_race/config/presets.json')); assert len(d.get('presets',d.get('models',[]))) >= 8"`
  - [ ] At least 2 entries per provider

  **QA Scenarios**:

  ```
  Scenario: presets.json is valid JSON
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -m json.tool llm_race/config/presets.json > /dev/null
    Expected Result: Exit code 0, no errors
    Evidence: .sisyphus/evidence/task-2-valid-json.txt

  Scenario: presets.json has entries for all 4 providers
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "import json; d=json.load(open('llm_race/config/presets.json')); presets=d.get('presets',[]); print(sorted(set(p['provider'] for p in presets)))"
    Expected Result: Output includes 'vllm', 'lm_studio', 'mlx_lm', 'ollama'
    Evidence: .sisyphus/evidence/task-2-provider-coverage.txt
  ```

  **Commit**: YES
  - Message: `feat(config): create presets.json with model/provider combinations`
  - Files: `llm_race/config/presets.json`

---

- [x] 3. Implement `complete()` in `VLLMProvider`

  **What to do**:
  - Add `complete()` method to `VLLMProvider` in `llm_race/config/vllm.py`
  - Same signature as `stream_complete()` but send `"stream": False` (or omit `stream` param)
  - Parse single JSON response body instead of SSE stream
  - Extract token usage from `response.json()["usage"]["completion_tokens"]`
  - Return `asdict(StreamResult(...))` with empty `inter_token_latencies` and ITL stats = None
  - Reuse error handling pattern from `stream_complete()`

  **Must NOT do**:
  - Do NOT break existing `stream_complete()` behavior
  - Do NOT import new dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick` — follows existing pattern closely
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T4, T5, T6)
  - **Parallel Group**: Wave 2 (with T4, T5, T6)
  - **Blocks**: T7, T8
  - **Blocked By**: T1

  **References**:
  - `llm_race/config/vllm.py` — Existing `stream_complete()` implementation (the pattern to follow for error handling, timing, and return value)
  - `llm_race/config/base.py` — `StreamResult` dataclass and the new `complete()` abstract method

  **Acceptance Criteria**:
  - [ ] `python -c "from llm_race.config.vllm import VLLMProvider; print(hasattr(VLLMProvider, 'complete'))"` → True
  - [ ] Method parses single JSON response (not SSE) correctly

  **QA Scenarios**:

  ```
  Scenario: VLLMProvider has complete() method
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.vllm import VLLMProvider; p=VLLMProvider(base_url='http://test:8000/v1'); print(hasattr(p, 'complete'))"
    Expected Result: Output "True"
    Evidence: .sisyphus/evidence/task-3-vllm-complete.txt

  Scenario: VLLMProvider imports don't break existing code
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.vllm import VLLMProvider; print('OK')"
    Expected Result: Output "OK"
    Evidence: .sisyphus/evidence/task-3-vllm-import.txt
  ```

  **Commit**: YES
  - Message: `feat(config): implement complete() in VLLMProvider`
  - Files: `llm_race/config/vllm.py`

---

- [x] 4. Create `LMStudioProvider` in `llm_race/config/lm_studio.py`

  **What to do**:
  - Create new file `llm_race/config/lm_studio.py`
  - Implement `LMStudioProvider(Provider)` class
  - `__init__(self, base_url: str = "http://localhost:1234/v1", api_key: str | None = None, timeout: int = 120)`
  - Read `api_key` from env var `LMSTUDIO_API_KEY` if not provided
  - Implement `stream_complete()`: OpenAI-compatible, uses `iter_sse_events()` from `llm_race/utils/sse.py`
  - Implement `complete()`: non-streaming POST, single JSON response
  - Follow exact same pattern as VLLMProvider for timing, error handling, and return value construction
  - Default headers: `Content-Type: application/json`, `Authorization: Bearer {api_key}` if key is set
  - LM Studio doesn't support `stream_options.include_usage` — use client-side token counting (split content by whitespace)

  **Must NOT do**:
  - Do NOT assume LM Studio sends token usage in response — count client-side
  - Do NOT import heavy dependencies beyond httpx, time, asyncio

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — new provider with specific quirks
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T3, T5, T6)
  - **Parallel Group**: Wave 2 (with T3, T5, T6)
  - **Blocks**: T7, T9
  - **Blocked By**: T1

  **References**:
  - `llm_race/config/vllm.py` — Reference implementation for OpenAI-compatible providers (streaming pattern, error handling, time measurement)
  - `llm_race/config/base.py` — `Provider` ABC and `StreamResult` dataclass
  - `llm_race/utils/sse.py` — `iter_sse_events()` for parsing SSE streams
  - `llm_race/utils/timing.py` — `compute_itl_stats()` for inter-token latency stats

  **Acceptance Criteria**:
  - [ ] `python -c "from llm_race.config.lm_studio import LMStudioProvider; print(type(LMStudioProvider(base_url='http://localhost:1234/v1')).__name__)"` → `LMStudioProvider`
  - [ ] Has both `stream_complete()` and `complete()` methods

  **QA Scenarios**:

  ```
  Scenario: LMStudioProvider can be instantiated
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.lm_studio import LMStudioProvider; p=LMStudioProvider(base_url='http://localhost:1234/v1'); print(type(p).__name__)"
    Expected Result: Output "LMStudioProvider"
    Evidence: .sisyphus/evidence/task-4-lm-studio-init.txt

  Scenario: LMStudioProvider has required methods
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.lm_studio import LMStudioProvider; p=LMStudioProvider(); print(hasattr(p,'stream_complete'), hasattr(p,'complete'))"
    Expected Result: Output "True True"
    Evidence: .sisyphus/evidence/task-4-lm-studio-methods.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add LM Studio provider`
  - Files: `llm_race/config/lm_studio.py`

---

- [x] 5. Create `MLXLMProvider` in `llm_race/config/mlx_lm.py`

  **What to do**:
  - Create new file `llm_race/config/mlx_lm.py`
  - Implement `MLXLMProvider(Provider)` class
  - `__init__(self, base_url: str = "http://localhost:8080/v1", api_key: str | None = None, timeout: int = 120)`
  - Read `api_key` from env var `MLXLM_API_KEY` if not provided
  - Implement `stream_complete()`: OpenAI-compatible, uses `iter_sse_events()`
  - Implement `complete()`: non-streaming POST, single JSON response
  - mlx-lm's OpenAI-compatible endpoint is similar to vLLM — can re-use `stream_options: {"include_usage": True}` if supported, otherwise client-side token counting
  - Follow same pattern as VLLMProvider

  **Must NOT do**:
  - Do NOT assume mlx-lm returns `usage` in streaming chunks — verify and fall back to client-side counting

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — new provider, similar to LM Studio
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T3, T4, T6)
  - **Parallel Group**: Wave 2 (with T3, T4, T6)
  - **Blocks**: T7, T10
  - **Blocked By**: T1

  **References**:
  - `llm_race/config/vllm.py` — Reference implementation for OpenAI-compatible providers
  - `llm_race/config/base.py` — `Provider` ABC and `StreamResult`
  - `llm_race/utils/sse.py` — SSE parser
  - `llm_race/utils/timing.py` — ITL stats

  **Acceptance Criteria**:
  - [ ] `python -c "from llm_race.config.mlx_lm import MLXLMProvider; print(type(MLXLMProvider(base_url='http://localhost:8080/v1')).__name__)"` → `MLXLMProvider`
  - [ ] Has both `stream_complete()` and `complete()` methods

  **QA Scenarios**:

  ```
  Scenario: MLXLMProvider can be instantiated
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.mlx_lm import MLXLMProvider; p=MLXLMProvider(base_url='http://localhost:8080/v1'); print(type(p).__name__)"
    Expected Result: Output "MLXLMProvider"
    Evidence: .sisyphus/evidence/task-5-mlx-lm-init.txt

  Scenario: MLXLMProvider has required methods
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.mlx_lm import MLXLMProvider; p=MLXLMProvider(); print(hasattr(p,'stream_complete'), hasattr(p,'complete'))"
    Expected Result: Output "True True"
    Evidence: .sisyphus/evidence/task-5-mlx-lm-methods.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add mlx-lm provider`
  - Files: `llm_race/config/mlx_lm.py`

---

- [x] 6. Create `OllamaProvider` in `llm_race/config/ollama.py`

  **What to do**:
  - Create new file `llm_race/config/ollama.py`
  - Implement `OllamaProvider(Provider)` class
  - `__init__(self, base_url: str = "http://localhost:11434/v1", api_key: str | None = None, timeout: int = 120)`
  - Read `api_key` from env var `OLLAMA_API_KEY` if not provided (Ollama typically doesn't need auth locally)
  - Implement `stream_complete()`: OpenAI-compatible endpoint `/v1/chat/completions`, uses `iter_sse_events()`
  - Implement `complete()`: non-streaming POST, single JSON response
  - Ollama's OpenAI-compatible mode may not support `stream_options.include_usage` — use client-side token counting (split by whitespace)
  - Ollama also may not return token usage in the response — count completion tokens by word count as fallback
  - Follow same pattern as VLLMProvider for timing, error handling, return value

  **Must NOT do**:
  - Do NOT use Ollama's native `/api/generate` or `/api/chat` endpoints — use `/v1/chat/completions`
  - Do NOT assume `usage` is present in the response

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — new provider with specific Ollama quirks
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T3, T4, T5)
  - **Parallel Group**: Wave 2 (with T3, T4, T5)
  - **Blocks**: T7, T11
  - **Blocked By**: T1

  **References**:
  - `llm_race/config/vllm.py` — Reference implementation for OpenAI-compatible providers
  - `llm_race/config/base.py` — `Provider` ABC and `StreamResult`
  - `llm_race/utils/sse.py` — SSE parser
  - `llm_race/utils/timing.py` — ITL stats

  **Acceptance Criteria**:
  - [ ] `python -c "from llm_race.config.ollama import OllamaProvider; print(type(OllamaProvider(base_url='http://localhost:11434/v1')).__name__)"` → `OllamaProvider`
  - [ ] Has both `stream_complete()` and `complete()` methods

  **QA Scenarios**:

  ```
  Scenario: OllamaProvider can be instantiated
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.ollama import OllamaProvider; p=OllamaProvider(base_url='http://localhost:11434/v1'); print(type(p).__name__)"
    Expected Result: Output "OllamaProvider"
    Evidence: .sisyphus/evidence/task-6-ollama-init.txt

  Scenario: OllamaProvider has required methods
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config.ollama import OllamaProvider; p=OllamaProvider(); print(hasattr(p,'stream_complete'), hasattr(p,'complete'))"
    Expected Result: Output "True True"
    Evidence: .sisyphus/evidence/task-6-ollama-methods.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add Ollama provider`
  - Files: `llm_race/config/ollama.py`

---

- [x] 7. Register all providers in `create_provider()` factory

  **What to do**:
  - Update `llm_race/config/__init__.py`:
    - Add `elif` branches in `create_provider()` for `"lm_studio"`, `"mlx_lm"`, and `"ollama"`
    - Each branch imports the corresponding module and instantiates the provider
    - Update the error message to list all available providers
  - Keep `DEFAULT_PROVIDER` as `"vllm"`
  - Ensure all new provider modules can be imported at the top level

  **Must NOT do**:
  - Do NOT change the function signature of `create_provider()`
  - Do NOT change default values in `__init__.py`

  **Recommended Agent Profile**:
  - **Category**: `quick` — straightforward factory updates
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T8, T9, T10, T11)
  - **Parallel Group**: Wave 3 (with T8, T9, T10, T11)
  - **Blocks**: None
  - **Blocked By**: T3, T4, T5, T6

  **References**:
  - `llm_race/config/__init__.py` — Existing `create_provider()` function
  - `llm_race/config/lm_studio.py`, `mlx_lm.py`, `ollama.py` — Provider files

  **Acceptance Criteria**:
  - [ ] All 4 provider types work via factory

  **QA Scenarios**:

  ```
  Scenario: All providers registered in factory
    Tool: Bash
    Preconditions: Provider files exist
    Steps:
      1. Run: python -c "from llm_race.config import create_provider; [create_provider(t, base_url='http://test:8000/v1') for t in ['vllm','lm_studio','mlx_lm','ollama']]; print('OK')"
    Expected Result: Output "OK"
    Evidence: .sisyphus/evidence/task-7-factory.txt

  Scenario: Unknown provider raises ValueError
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from llm_race.config import create_provider; create_provider('nonexistent')" 2>&1
    Expected Result: Error message includes "Unknown provider"
    Evidence: .sisyphus/evidence/task-7-unknown.txt
  ```

  **Commit**: YES
  - Message: `feat(config): register new providers in create_provider factory`
  - Files: `llm_race/config/__init__.py`

---

- [x] 8. Unit tests for `VLLMProvider.complete()`

  **What to do**:
  - Add test class `TestVLLMProvider` to `tests/test_providers.py`
  - Test `complete()` returns correct `StreamResult`-shaped dict on success
  - Test `complete()` handles HTTP errors gracefully
  - Test `complete()` handles timeouts
  - Mock `httpx.AsyncClient` using `unittest.mock`

  **Must NOT do**:
  - Do NOT hit real HTTP endpoints

  **Recommended Agent Profile**:
  - **Category**: `quick` — single test class
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T9, T10, T11)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T3

  **References**:
  - `tests/test_models.py` — Existing test patterns

  **Acceptance Criteria**:
  - [ ] All VLLM tests pass

  **QA Scenarios**:

  ```
  Scenario: VLLM complete() tests pass
    Tool: Bash
    Steps:
      1. Run: python -m pytest tests/test_providers.py::TestVLLMProvider -v --tb=short
    Expected Result: All PASS (exit code 0)
    Evidence: .sisyphus/evidence/task-8-vllm-tests.txt
  ```

  **Commit**: YES (group with T9, T10, T11)
  - Message: `test(config): add unit tests for all providers`
  - Files: `tests/test_providers.py`

---

- [x] 9. Unit tests for `LMStudioProvider`

  **What to do**:
  - Add test class `TestLMStudioProvider` to `tests/test_providers.py`
  - Test `stream_complete()` and `complete()` for success, HTTP errors, timeout, API key from env
  - Mock httpx responses

  **Must NOT do**:
  - Do NOT hit real endpoints

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T8, T10, T11)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T4

  **Acceptance Criteria**:
  - [ ] All LM Studio tests pass

  **QA Scenarios**:

  ```
  Scenario: LMStudioProvider tests pass
    Tool: Bash
    Steps:
      1. Run: python -m pytest tests/test_providers.py::TestLMStudioProvider -v --tb=short
    Expected Result: All PASS (exit code 0)
    Evidence: .sisyphus/evidence/task-9-lm-studio-tests.txt
  ```

  **Commit**: YES (group with T8, T10, T11)

---

- [x] 10. Unit tests for `MLXLMProvider`

  **What to do**:
  - Add test class `TestMLXLMProvider` to `tests/test_providers.py`
  - Same test coverage as T9

  **Must NOT do**:
  - Do NOT hit real endpoints

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T8, T9, T11)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T5

  **Acceptance Criteria**:
  - [ ] All mlx-lm tests pass

  **QA Scenarios**:

  ```
  Scenario: MLXLMProvider tests pass
    Tool: Bash
    Steps:
      1. Run: python -m pytest tests/test_providers.py::TestMLXLMProvider -v --tb=short
    Expected Result: All PASS (exit code 0)
    Evidence: .sisyphus/evidence/task-10-mlx-lm-tests.txt
  ```

  **Commit**: YES (group with T8, T9, T11)

---

- [x] 11. Unit tests for `OllamaProvider`

  **What to do**:
  - Add test class `TestOllamaProvider` to `tests/test_providers.py`
  - Same test coverage as T9/T10
  - Specifically test the fallback token counting (when API doesn't return `usage`)

  **Must NOT do**:
  - Do NOT hit real endpoints

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T7, T8, T9, T10)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T6

  **Acceptance Criteria**:
  - [ ] All Ollama tests pass

  **QA Scenarios**:

  ```
  Scenario: OllamaProvider tests pass
    Tool: Bash
    Steps:
      1. Run: python -m pytest tests/test_providers.py::TestOllamaProvider -v --tb=short
    Expected Result: All PASS (exit code 0)
    Evidence: .sisyphus/evidence/task-11-ollama-tests.txt
  ```

  **Commit**: YES (group with T8, T9, T10)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 2 review agents run in PARALLEL. ALL must APPROVE.

- [x] F1. **Plan Compliance + Scope Fidelity Audit** — `unspecified-high`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, check class inheritance, check method signatures). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Full Test Suite + Integration Check** — `unspecified-high`
  Run `python -m pytest tests/test_providers.py -v --tb=short`. Verify all tests pass. Test factory: instantiate each provider via `create_provider()`. Test imports: all provider modules import cleanly.
  Output: `Tests [N pass/N fail] | Factory [PASS/FAIL] | Imports [PASS/FAIL] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(config): add abstract complete() method to Provider base class` — `llm_race/config/base.py`
- **T2**: `feat(config): create presets.json with model/provider combinations` — `llm_race/config/presets.json`
- **T3**: `feat(config): implement complete() in VLLMProvider` — `llm_race/config/vllm.py`
- **T4**: `feat(config): add LM Studio provider` — `llm_race/config/lm_studio.py`
- **T5**: `feat(config): add mlx-lm provider` — `llm_race/config/mlx_lm.py`
- **T6**: `feat(config): add Ollama provider` — `llm_race/config/ollama.py`
- **T7**: `feat(config): register new providers in create_provider factory` — `llm_race/config/__init__.py`
- **T8-T11**: `test(config): add unit tests for all providers` — `tests/test_providers.py`

---

## Success Criteria

### Verification Commands
```bash
python -c "from llm_race.config import create_provider; \
  for t in ['lm_studio','mlx_lm','ollama']: \
    p=create_provider(t, base_url='http://localhost:8000/v1'); \
    print(f'{t}: {type(p).__name__}')"
# Expected: lm_studio: LMStudioProvider, mlx_lm: MLXLMProvider, ollama: OllamaProvider

python -m pytest tests/test_providers.py -v --tb=short
# Expected: all tests PASS

python -c "from llm_race.config.base import Provider; print(hasattr(Provider, 'complete'))"
# Expected: True
```

### Final Checklist
- [x] All 3 providers implement both `stream_complete()` and `complete()`
- [x] All registered in `create_provider()`
- [x] API keys read from env vars (no hardcoded values)
- [x] `presets.json` is valid JSON with model entries
- [x] All unit tests pass
- [x] No changes to runner, CLI, or web viewer
