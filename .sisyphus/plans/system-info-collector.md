# Plan: System Info Collector (Issue #5)

## TL;DR

> **Quick Summary**: Implement `llm_race/utils/system.py` to collect machine/GPU/OS/network info for benchmark metadata. Produces a typed `SystemInfo` dataclass with in-memory caching, maps to existing `Machine` ORM model, with full unit test coverage.
>
> **Deliverables**:
> - `llm_race/utils/system.py` — full system info collector module
> - `tests/test_system.py` — unit tests with mocked platform/subprocess/socket
> - `llm_race/utils/__init__.py` — updated if needed
> - `requirements.txt` — add `psutil` if needed for RAM collection
>
> **Estimated Effort**: Quick (single module, ~200 lines)
> **Parallel Execution**: YES — 2 waves + final verification
> **Critical Path**: Task 3 (collectors) → Task 4 (orchestrator) → Task 5 (tests)

---

## Context

### Original Request

Issue #5: Implement `llm_race/utils/system.py` to collect machine/GPU/OS information for benchmark metadata. Required fields: OS (platform, version, kernel), CPU (model, cores, threads, architecture), GPU (model, driver, CUDA version, VRAM via nvidia-smi), RAM (total, available), Network (hostname, IP optional).

### Interview Summary (user decisions)

**Key Discussions**:
- GPU detection: NVIDIA (`nvidia-smi`) + AMD (`rocm-smi`) + Apple Silicon (`system_profiler SPDisplaysDataType`) — graceful fallback chain
- Output format: Typed dataclass `SystemInfo` + `asdict()` — follows `config/base.py:StreamResult` pattern
- Tests: YES with pytest — mocking `platform`, `subprocess`, `socket`
- Network: hostname + local IP
- Caching: in-memory via module-level variable, re-collect with `force=True`

### Research Findings & Metis Review

**Identified Gaps** (addressed in plan):
- RAM collection via stdlib: `psutil` is the cleanest option but adds a dependency — plan includes adding it to requirements.txt
- Machine model mapping: `SystemInfo` fields must map cleanly to `db/models.py:Machine` fields (hostname, cpu, gpu, gpu_count, ram_gb, os, os_version, driver_version, python_version)
- WSL/containers: platform detection may be misleading — note in docstring
- GPU graceful degradation: entire GPU section returns None fields if no GPU tool available
- Hostname deduplication: `Machine` model has `UniqueConstraint("hostname")` — machine info should be hashable/dedupeable

---

## Work Objectives

### Core Objective
Create a reusable system info collection module that provides structured machine data for benchmark runs, with in-memory caching and graceful degradation on unavailable data sources.

### Concrete Deliverables
- `llm_race/utils/system.py` — system info dataclass, collectors, cache
- `tests/test_system.py` — unit tests with full mocking
- `requirements.txt` — add `psutil>=6.0`

### Definition of Done
- [ ] `python -c "from llm_race.utils.system import get_system_info; info = get_system_info(); print(info)"` produces valid output
- [ ] `python -m pytest tests/test_system.py -v` passes all tests
- [ ] Output fields map 1:1 to `Machine` model fields

### Must Have
- Collect OS info (platform, version, kernel) via `platform` stdlib
- Collect CPU info (model, cores, threads, architecture) via `platform` + `os.cpu_count()`
- Collect RAM (total GB, available GB) via `psutil`
- Collect GPU info via `nvidia-smi` → `rocm-smi` → `system_profiler` fallback chain
- Collect Network (hostname, local IP) via `socket`
- Return typed `SystemInfo` dataclass with `asdict()` 
- Module-level cache: `get_system_info(force=False)` / `collect_system_info()` pattern
- `force=True` re-collects from scratch
- Graceful fallback: all GPU fields are `None` if no GPU tool available

### Must NOT Have (Guardrails)
- NO disk/IO info collection
- NO CPU temperature or utilization metrics
- NO process list or running services
- NO network bandwidth or latency checks
- NO public IP lookup (local IP only)
- NO persistent cache to disk — in-memory only
- NO modification to existing `Machine` model schema

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: YES (TDD)
- **Framework**: pytest
- **Test approach**: Each collector function has a corresponding test with mocked dependencies

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Library/Module**: Bash (python -c) — import module, call functions, inspect output
- **Tests**: Bash (pytest) — run test suite, assert all pass
- **Integration**: Python REPL — verify dataclass → dict → Machine model fields

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — 2 parallel tasks):
├── Task 1: SystemInfo dataclass + module scaffold + cache mechanism
└── Task 2: Test module scaffold + fixtures + test skeleton

Wave 2 (After Wave 1 — 1 task):
├── Task 3: All collector functions (_get_os_info, _get_cpu_info, _get_ram_info, _get_network_info, _get_gpu_info)

Wave 3 (After Wave 2 — 1 task):
├── Task 4: collect_system_info() orchestrator + Machine model compatibility

Wave 4 (After Wave 3 — 2 parallel tasks):
├── Task 5: Complete unit tests (test_system.py)
└── Task 6: QA evidence collection + final verification

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
```

### Dependency Matrix
- **1**: None — 3, 5
- **2**: None — 5
- **3**: 1 — 4
- **4**: 3 — 5, 6
- **5**: 2, 4 — F1-F4
- **6**: 4 — F1-F4

### Agent Dispatch Summary
- **Wave 1**: 2 tasks — quick
- **Wave 2**: 1 task — deep (GPU detection complexity)
- **Wave 3**: 1 task — quick
- **Wave 4**: 2 tasks — quick + deep
- **FINAL**: 4 review agents in parallel

---

## TODOs

- [x] 1. SystemInfo dataclass + module scaffold + cache mechanism

  **What to do**:
  - Create `llm_race/utils/system.py` with:
    - `SystemInfo` dataclass matching `Machine` model fields:
      ```python
      @dataclass
      class SystemInfo:
          hostname: str
          cpu: str
          cpu_cores: int
          cpu_threads: int
          cpu_architecture: str
          gpu: str | None
          gpu_count: int | None
          gpu_driver_version: str | None
          gpu_cuda_version: str | None
          gpu_vram_gb: float | None
          ram_total_gb: float
          ram_available_gb: float
          os: str
          os_version: str
          os_kernel: str
          python_version: str
          ip_local: str
          def to_dict(self) -> dict[str, Any]: ...
      ```
    - Module-level cache: `_cached_info: SystemInfo | None = None`
    - `get_system_info(force: bool = False) -> SystemInfo` — returns cached or calls `collect_system_info()`
    - `force=True` sets `_cached_info = None` before collection
    - Proper module docstring and logging setup
    - Export `SystemInfo`, `get_system_info`, `collect_system_info` in `__all__`
    - Follow existing import style: stdlib → third-party → local
  - Add `psutil>=6.0,<7.0` to `requirements.txt`
  - Update `llm_race/utils/__init__.py` if needed (for clean imports)

  **Must NOT do**:
  - Do NOT add any collector logic yet (just dataclass + cache scaffold)
  - Do NOT modify `db/models.py`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small, well-scoped module scaffold with known patterns
  - **Skills**: none needed
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None

  **References**:
  - `llm_race/config/base.py:StreamResult` — Follow dataclass + asdict() pattern exactly
  - `llm_race/db/models.py:Machine` — Fields to map in `to_dict()`
  - `llm_race/utils/timing.py` — Simpler sibling module pattern (functions + no class)

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: SystemInfo dataclass can be instantiated and converted to dict
    Tool: Bash (python -c)
    Preconditions: Module file exists
    Steps:
      1. Run: python -c "from llm_race.utils.system import SystemInfo; import datetime; info = SystemInfo(hostname='test', cpu='test', cpu_cores=4, cpu_threads=8, cpu_architecture='x86_64', gpu=None, gpu_count=None, gpu_driver_version=None, gpu_cuda_version=None, gpu_vram_gb=None, ram_total_gb=16.0, ram_available_gb=8.0, os='Linux', os_version='5.15', os_kernel='5.15.0', python_version='3.11', ip_local='127.0.0.1'); d = info.to_dict(); print(sorted(d.keys()))"
    Expected Result: Prints sorted field names matching Machine model columns
    Failure Indicators: ImportError, KeyError, missing fields
    Evidence: .sisyphus/evidence/task-1-dataclass-init.txt

  Scenario: get_system_info returns cached value on second call
    Tool: Bash (python -c)
    Preconditions: Module loaded
    Steps:
      1. Run: python -c "from llm_race.utils.system import get_system_info; a = get_system_info(force=True); b = get_system_info(); print(a is b)"
    Expected Result: Prints 'True' (same object returned from cache)
    Failure Indicators: Prints 'False'
    Evidence: .sisyphus/evidence/task-1-cache-hit.txt

  Scenario: force=True triggers re-collection
    Tool: Bash (python -c)
    Preconditions: Module loaded
    Steps:
      1. Run: python -c "from llm_race.utils.system import get_system_info; a = get_system_info(); b = get_system_info(force=True); print(a is b)"
    Expected Result: Prints 'False' (different objects)
    Failure Indicators: Prints 'True'
    Evidence: .sisyphus/evidence/task-1-cache-force.txt
  ```

  **Evidence to Capture**:
  - [ ] task-1-dataclass-init.txt
  - [ ] task-1-cache-hit.txt
  - [ ] task-1-cache-force.txt

  **Commit**: YES (groups with 3, 4)
  - Message: `feat(utils): implement system info collector`
  - Files: `llm_race/utils/system.py`, `llm_race/utils/__init__.py`, `requirements.txt`

---

- [x] 2. Test module scaffold + fixtures + test skeleton

  **What to do**:
  - Create `tests/test_system.py` with:
    - Fixtures: `mock_platform`, `mock_subprocess`, `mock_socket`, `mock_psutil`
    - Mock `platform.system()` → "Linux"
    - Mock `platform.release()` → "5.15.0"
    - Mock `platform.version()` → "#1 SMP"
    - Mock `platform.processor()` → "x86_64"
    - Mock `os.cpu_count()` → 8
    - Mock `socket.gethostname()` → "test-machine"
    - Mock `socket.gethostbyname()` → "192.168.1.1"
    - Mock `psutil.virtual_memory().total` → 17179869184 (16 GB)
    - Mock `psutil.virtual_memory().available` → 8589934592 (8 GB)
    - Follow `tests/test_models.py` conventions (fixtures, docstrings, imports)
    - Test skeleton with `pass` for 8+ test functions:
      - `test_get_os_info`
      - `test_get_cpu_info`
      - `test_get_ram_info`
      - `test_get_network_info`
      - `test_get_gpu_info_nvidia`
      - `test_get_gpu_info_apple`
      - `test_get_gpu_info_no_gpu`
      - `test_collect_system_info`
    - Each test function has docstring describing what it tests

  **Must NOT do**:
  - Do NOT implement test bodies yet (just skeletons + fixtures)
  - Do NOT mock `system.py` internals yet (tests will be completed in Task 5)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard test scaffolding, depends on existing test patterns
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - `tests/test_models.py` — Fixture pattern (in-memory SQLite not needed, but pytest fixture style)
  - `tests/test_models.py:db_session` — Fixture naming conventions

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: All test functions exist in skeleton
    Tool: Bash (python -c)
    Preconditions: test file exists
    Steps:
      1. Run: python -c "import tests.test_system as t; funcs = [f for f in dir(t) if f.startswith('test_')]; print(sorted(funcs))"
    Expected Result: Prints at least 8 test functions
    Failure Indicators: Fewer than 8 test functions
    Evidence: .sisyphus/evidence/task-2-test-skeleton.txt

  Scenario: Fixtures can be imported
    Tool: Bash (python -c)
    Preconditions: test file exists
    Steps:
      1. Run: python -c "from tests.test_system import mock_platform, mock_subprocess, mock_socket, mock_psutil; print('fixtures OK')"
    Expected Result: Prints 'fixtures OK'
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-2-fixtures-import.txt
  ```

  **Evidence to Capture**:
  - [ ] task-2-test-skeleton.txt
  - [ ] task-2-fixtures-import.txt

  **Commit**: YES (groups with 5)
  - Message: `test(utils): add unit tests for system info collector`
  - Files: `tests/test_system.py`

---

- [x] 3. All collector functions

  **What to do**:
  - Implement these private functions in `llm_race/utils/system.py`:
    - `_get_os_info() -> dict[str, str]`:
      - `os`: `platform.system()` ("Linux", "Darwin", "Windows", "Unknown")
      - `os_version`: `platform.version()` (or `platform.mac_ver()[0]` on macOS)
      - `os_kernel`: `platform.release()`
      - `python_version`: `platform.python_version()`
    - `_get_cpu_info() -> dict[str, Any]`:
      - `cpu`: `platform.processor()` ("arm64", "x86_64", "Intel64")
      - `cpu_cores`: `os.cpu_count()` (physical cores not reliably available via stdlib)
      - `cpu_threads`: `os.cpu_count()` (same, stdlib doesn't distinguish)
      - `cpu_architecture`: `platform.machine()` or `platform.architecture()[0]`
      - Note: On macOS, `platform.processor()` may return "i386" — use `platform.machine()` as fallback
    - `_get_ram_info() -> dict[str, float]`:
      - `ram_total_gb`: `psutil.virtual_memory().total / (1024**3)`, rounded to 2 decimals
      - `ram_available_gb`: `psutil.virtual_memory().available / (1024**3)`, rounded to 2 decimals
    - `_get_network_info() -> dict[str, str]`:
      - `hostname`: `socket.gethostname()`
      - `ip_local`: `socket.gethostbyname(socket.gethostname())` (handle `socket.gaierror`)
    - `_get_gpu_info() -> dict[str, Any]`:
      - Fallback chain: NVIDIA → AMD → Apple Silicon → None
      - **NVIDIA**: `subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=10)`
        - Parse CSV output: `name`, `driver_version`, `memory.total` (MiB → GB)
        - CUDA version: `subprocess.run(["nvidia-smi", "--query"], ...)` or parse from driver
        - Returns: `gpu`, `gpu_count`, `gpu_driver_version`, `gpu_cuda_version`, `gpu_vram_gb`
      - **AMD**: `subprocess.run(["rocm-smi", "--showproductname", "--showdrive", "--showmeminfo", "vram"], capture_output=True, text=True, timeout=10)`
        - Parse key=value output for product name, driver, VRAM
      - **Apple Silicon**: `subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True, timeout=15)`
        - Parse for "Chipset Model", "VRAM (Total)" or "VRAM"
      - **Fallback**: All fields return `None` if no GPU tool succeeds
      - Use `logging.debug()` for which detection method was attempted
      - Wrap each subprocess call in try/except (FileNotFoundError, TimeoutExpired, CalledProcessError)
    - All functions raise `SystemInfoError` (custom exception) on unexpected failures
    - All functions use `import logging; logger = logging.getLogger(__name__)`

  **Must NOT do**:
  - Do NOT add `psutil` as hard dependency — it's already in requirements.txt
  - Do NOT call `nvidia-smi` with `--xml` or `--json` variants (use CSV)
  - Do NOT add disk IO, temp, or network latency info
  - Do NOT catch broad `Exception` — use specific exceptions

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: GPU detection requires parsing multiple CLI output formats, error handling across 3 platforms
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 1's dataclass + scaffold)
  - **Parallel Group**: Wave 2 (sequential)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:
  - NVIDIA SMI query docs: `nvidia-smi --help-query-gpu` for format
  - `llm_race/utils/timing.py` — Function structure and error handling patterns
  - `llm_race/config/base.py` — Logging pattern: `logger = logging.getLogger(__name__)`

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: OS info returns platform data
    Tool: Bash (python -c)
    Preconditions: system.py module exists
    Steps:
      1. Run: python -c "import llm_race.utils.system as s; import platform; info = s._get_os_info(); assert info['os'] == platform.system(); assert info['os_kernel'] == platform.release(); print('OS info OK')"
    Expected Result: Prints 'OS info OK'
    Failure Indicators: AssertionError, KeyError
    Evidence: .sisyphus/evidence/task-3-os-info.txt

  Scenario: CPU info returns processor data
    Tool: Bash (python -c)
    Preconditions: system.py module exists
    Steps:
      1. Run: python -c "import llm_race.utils.system as s; import os; info = s._get_cpu_info(); assert info['cpu_cores'] == (os.cpu_count() or 0); assert isinstance(info['cpu_architecture'], str); print('CPU info OK')"
    Expected Result: Prints 'CPU info OK'
    Failure Indicators: AssertionError, KeyError
    Evidence: .sisyphus/evidence/task-3-cpu-info.txt

  Scenario: GPU detection fails gracefully (no nvidia-smi available)
    Tool: Bash (python -c)
    Preconditions: system.py module exists, may or may not have GPU
    Steps:
      1. Run: python -c "import llm_race.utils.system as s; info = s._get_gpu_info(); assert isinstance(info['gpu'], str) or info['gpu'] is None; print('GPU info graceful:', info['gpu'])"
    Expected Result: Prints 'GPU info graceful: None' or actual GPU name (never crashes)
    Failure Indicators: Exception raised, subprocess.FileNotFoundError
    Evidence: .sisyphus/evidence/task-3-gpu-graceful.txt
  ```

  **Evidence to Capture**:
  - [ ] task-3-os-info.txt
  - [ ] task-3-cpu-info.txt
  - [ ] task-3-ram-info.txt
  - [ ] task-3-network-info.txt
  - [ ] task-3-gpu-graceful.txt

  **Commit**: YES (groups with 1, 4)
  - Message: `feat(utils): implement system info collector`
  - Files: `llm_race/utils/system.py`

---

- [x] 4. collect_system_info() orchestrator + Machine model compatibility

  **What to do**:
  - Implement `collect_system_info() -> SystemInfo`:
    - Calls all `_get_*_info()` functions
    - Assembles result into `SystemInfo(**os_info, **cpu_info, **gpu_info, **ram_info, **network_info)`
    - Sets `_cached_info` and returns
    - Wrap in try/except with specific exceptions — never return partial/empty SystemInfo
    - Logging: `logger.info("System info collected")`, `logger.debug(...)` per collector
  - Implement `to_dict()` on `SystemInfo`:
    - Returns dict with keys matching `Machine` model column names:
      - `hostname` → `hostname`
      - `cpu` → `cpu` (format: "Intel Xeon 16 cores @ 2.5GHz")
      - `gpu` → `gpu` (format: "NVIDIA A100 80GB")
      - `gpu_count` → `gpu_count`
      - `ram_gb` → `ram_gb` (use `ram_total_gb` rounded to 1 decimal)
      - `os` → `os`
      - `os_version` → `os_version`
      - `driver_version` → `gpu_driver_version`
      - `python_version` → `python_version`
    - Extra fields (cpu_cores, cpu_threads, cpu_architecture, os_kernel, ram_available_gb, ip_local, gpu_cuda_version, gpu_vram_gb) remain accessible on the dataclass but aren't in Machine model yet

  **Must NOT do**:
  - Do NOT modify `db/models.py` or `db/queries.py`
  - Do NOT add DB saving logic (that's the caller's responsibility)
  - Do NOT catch bare `Exception`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple orchestrator, straightforward field mapping
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 3 collectors)
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 3

  **References**:
  - `llm_race/db/models.py:Machine` — Target model fields (hostname, cpu, gpu, gpu_count, ram_gb, os, os_version, driver_version, python_version)

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: collect_system_info returns complete SystemInfo
    Tool: Bash (python -c)
    Preconditions: system.py module exists
    Steps:
      1. Run: python -c "from llm_race.utils.system import collect_system_info; info = collect_system_info(); print(f'hostname={info.hostname} os={info.os} cpu={info.cpu[:30]}... ram={info.ram_total_gb}GB')"
    Expected Result: Prints system info fields without error
    Failure Indicators: TypeError, AttributeError, Exception
    Evidence: .sisyphus/evidence/task-4-collect-full.txt

  Scenario: to_dict() maps to Machine model fields
    Tool: Bash (python -c)
    Preconditions: system.py module exists
    Steps:
      1. Run: python -c "
  from llm_race.utils.system import collect_system_info
  info = collect_system_info()
  d = info.to_dict()
  machine_fields = {'hostname','cpu','gpu','gpu_count','ram_gb','os','os_version','driver_version','python_version'}
  missing = machine_fields - set(d.keys())
  extra = set(d.keys()) - machine_fields
  print(f'missing={missing}')
  print(f'extra={extra}')
  assert not missing, f'Missing Machine fields: {missing}'
  "
    Expected Result: Prints missing=set() and extra=set() (or extra fields that are optional)
    Failure Indicators: AssertionError with missing fields
    Evidence: .sisyphus/evidence/task-4-to-dict-mapping.txt
  ```

  **Evidence to Capture**:
  - [ ] task-4-collect-full.txt
  - [ ] task-4-to-dict-mapping.txt

  **Commit**: YES (groups with 1, 3)
  - Message: `feat(utils): implement system info collector`
  - Files: `llm_race/utils/system.py`

---

- [x] 5. Complete unit tests

  **What to do**:
  - Implement test bodies in `tests/test_system.py` using the fixtures from Task 2:
    - `test_get_os_info`: patch `platform.system()`, `platform.release()`, `platform.version()`, `platform.python_version()`
      - Assert: returns dict with `os='Linux'`, `os_kernel='5.15.0'`, `os_version='#1 SMP'`, `python_version='3.11'`
    - `test_get_cpu_info`: patch `platform.processor()`, `platform.machine()`, `os.cpu_count()`
      - Assert: returns dict with `cpu='arm64'`, `cpu_cores=8`, `cpu_threads=8`, `cpu_architecture='arm64'`
    - `test_get_ram_info`: patch `psutil.virtual_memory` returning namedtuple
      - Assert: `ram_total_gb=16.0`, `ram_available_gb=8.0`
    - `test_get_network_info`: patch `socket.gethostname()`, `socket.gethostbyname()`
      - Assert: `hostname='test-machine'`, `ip_local='192.168.1.1'`
    - `test_get_gpu_info_nvidia`: patch `subprocess.run` to simulate `nvidia-smi` output ("A100, 12.0, 81250 MiB")
      - Assert: `gpu='NVIDIA A100'`, `gpu_count=1`, `gpu_driver_version='12.0'`
    - `test_get_gpu_info_apple`: patch `subprocess.run` failing for nvidia-smi, then simulate `system_profiler` output
      - Assert: `gpu='Apple M3 Max'` 
    - `test_get_gpu_info_no_gpu`: patch `subprocess.run` raising `FileNotFoundError` for all tools
      - Assert: All GPU fields are `None`
    - `test_collect_system_info`: patch all collectors, assert `SystemInfo` assembled correctly
    - `test_get_system_info_cache`: assert caching behavior (same object on repeated call)
    - `test_get_system_info_force`: assert `force=True` returns new object
  - Use `unittest.mock.patch` or `pytest.monkeypatch`
  - Each test function has docstring

  **Must NOT do**:
  - Do NOT test external GPU tools (tests mock all subprocess calls)
  - Do NOT modify `system.py` to make tests pass — tests should pass against real module

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard unit test implementation with well-defined mocking
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Tasks 2 and 4)
  - **Parallel Group**: Wave 4 (with Task 6)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 2, 4

  **References**:
  - `tests/test_models.py` — Test structure, assertions, import patterns
  - `python -m pytest tests/test_system.py -v` — Expected to pass all

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: All tests pass
    Tool: Bash (pytest)
    Preconditions: system.py and test_system.py exist
    Steps:
      1. Run: python -m pytest tests/test_system.py -v 2>&1
    Expected Result: All 10+ tests pass (PASSED), 0 failures
    Failure Indicators: FAILED, ERROR, any test not passing
    Evidence: .sisyphus/evidence/task-5-all-tests-pass.txt

  Scenario: GPU no-gpu test verifies graceful fallback
    Tool: Bash (pytest -k)
    Preconditions: test_system.py exists
    Steps:
      1. Run: python -m pytest tests/test_system.py::test_get_gpu_info_no_gpu -v 2>&1
    Expected Result: PASSED
    Failure Indicators: FAILED
    Evidence: .sisyphus/evidence/task-5-gpu-fallback-test.txt
  ```

  **Evidence to Capture**:
  - [ ] task-5-all-tests-pass.txt
  - [ ] task-5-gpu-fallback-test.txt

  **Commit**: YES (groups with 2)
  - Message: `test(utils): add unit tests for system info collector`
  - Files: `tests/test_system.py`

---

- [x] 6. QA evidence collection + final verification

  **What to do**:
  - Run all QA scenarios from Tasks 1-5 to collect evidence
  - Verify all evidence files exist in `.sisyphus/evidence/`
  - Run integration smoke test:
    - `python -c "from llm_race.utils.system import get_system_info; info = get_system_info(force=True); print(info)"`
  - Run full test suite: `python -m pytest tests/test_system.py -v`
  - Run machine model mapping verification
  - Run `python -m pytest tests/ -v` to ensure no regression on existing tests

  **Must NOT do**:
  - Do NOT modify any source code (evidence collection only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward evidence collection and verification
  - **Skills**: none needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 5)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 4

  **References**:
  - `.sisyphus/evidence/` — Evidence directory

  **Acceptance Criteria**:

  **QA Scenarios**:

  ```
  Scenario: Full integration smoke test
    Tool: Bash (python -c)
    Preconditions: All module code exists
    Steps:
      1. Run: python -c "from llm_race.utils.system import get_system_info; info = get_system_info(force=True); print(f'hostname={info.hostname} os={info.os} python={info.python_version} ram={info.ram_total_gb}GB')"
    Expected Result: Prints valid system info
    Failure Indicators: Any exception
    Evidence: .sisyphus/evidence/task-6-integration-smoke.txt

  Scenario: No regression on existing tests
    Tool: Bash (pytest)
    Preconditions: All tests exist
    Steps:
      1. Run: python -m pytest tests/ -v 2>&1
    Expected Result: All tests pass (including model tests)
    Failure Indicators: Any regression failure
    Evidence: .sisyphus/evidence/task-6-no-regression.txt
  ```

  **Evidence to Capture**:
  - [ ] task-6-integration-smoke.txt
  - [ ] task-6-no-regression.txt

  **Commit**: NO (evidence-only task)

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run python -c). For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/test_system.py -v`. Review changed files for: broad except clauses, unused imports, commented-out code. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute every QA scenario from every task — follow exact steps, capture evidence. Test cross-task integration (all collectors work together). Test edge cases: no GPU, WSL detection. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **1**: `feat(utils): add SystemInfo dataclass and caching mechanism` — llm_race/utils/system.py, llm_race/utils/__init__.py
- **2**: `test(utils): add test fixtures and skeleton for system info` — tests/test_system.py
- **3**: `feat(utils): implement OS, CPU, RAM, network, GPU collectors` — llm_race/utils/system.py
- **4**: `feat(utils): implement collect_system_info orchestrator` — llm_race/utils/system.py
- **5**: `test(utils): complete unit tests for system info collector` — tests/test_system.py

---

## Success Criteria

### Verification Commands
```bash
python -c "from llm_race.utils.system import get_system_info; info = get_system_info(); print(info)"
# Expected: SystemInfo(hostname='...', os='...', cpu='...', ...)

python -m pytest tests/test_system.py -v
# Expected: 8+ tests passed, 0 failures

python -c "
from llm_race.utils.system import SystemInfo, get_system_info
from llm_race.db.models import Machine
info = get_system_info()
d = info.to_dict()
# Verify Machine fields exist
machine_fields = {'hostname','cpu','gpu','gpu_count','ram_gb','os','os_version','driver_version','python_version'}
assert machine_fields.issubset(d.keys()), f'Missing fields: {machine_fields - d.keys()}'
print('Machine model compatibility: OK')
"
```

### Final Checklist
- [ ] `collect_system_info()` returns complete `SystemInfo` dataclass
- [ ] `get_system_info()` returns cached version; `force=True` re-collects
- [ ] GPU detection gracefully falls back through NVIDIA → AMD → Apple Silicon → None
- [ ] All GPU fields are None when no GPU tool available (no crash)
- [ ] `SystemInfo.to_dict()` maps 1:1 to `Machine` model fields
- [ ] All pytest tests pass
- [ ] No forbidden patterns (disk IO, temp, public IP, etc.)
