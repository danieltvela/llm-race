# Plan: Add Missing Dependencies to requirements.txt

## TL;DR

> **Quick Summary**: Update `requirements.txt` with 4 missing Python dependencies (`sqlalchemy`, `jinja2`, `python-dotenv`, `pytest`) following consistent major-version pinning, plus verify everything installs correctly.
>
> **Deliverables**:
> - Updated `requirements.txt` with all 6 dependencies (2 existing + 4 new)
>
> **Estimated Effort**: Quick (~5 min execution)
> **Parallel Execution**: NO — single task, single file
> **Critical Path**: Edit file → `pip install` verify → import check

---

## Context

### Original Request
[Issue #11](https://github.com/danieltvela/llm-race/issues/11) — Add missing dependencies and update `requirements.txt`. Currently only has `httpx` and `numpy`. Need to add `sqlalchemy`, `jinja2`, `python-dotenv`, and optionally `pytest`.

### Interview Summary
**Key Decisions**:
- **pytest location**: In `requirements.txt` itself (no separate `requirements-dev.txt`)
- **pytest config**: None needed — just the dependency entry
- **Version pinning**: Follow existing pattern `>=X.Y,<X+1.0`

**Metis Review** (gaps addressed):
- **Future deps note**: sqlalchemy, jinja2, python-dotenv are for stub/future code. This is expected per the issue — the user is proactively adding them ahead of implementation.
- **Consistency**: All new entries will use the same `>=X.Y,<X+1.0` format as existing deps.

---

## Work Objectives

### Core Objective
Update `requirements.txt` to include all project dependencies.

### Concrete Deliverables
- `requirements.txt` — updated file with 6 entries total

### Definition of Done
- [ ] `pip install -r requirements.txt` → exit 0 with no errors
- [ ] `python -c "import httpx, numpy, sqlalchemy, jinja2, pytest"` → no ImportError
- [ ] `python -c "import dotenv"` → no ImportError
- [ ] Existing `httpx` and `numpy` entries preserved unchanged

### Must Have
- Add `sqlalchemy>=2.0,<3.0`
- Add `jinja2>=3.1,<4.0`
- Add `python-dotenv>=1.0,<2.0`
- Add `pytest>=8.0,<9.0`
- Keep existing `httpx>=0.27,<1.0` and `numpy>=1.24,<2.0`
- Dependencies sorted alphabetically

### Must NOT Have (Guardrails)
- Do NOT modify or remove existing entries
- Do NOT create additional files (no `requirements-dev.txt`, no `pytest.ini`)
- Do NOT change version pinning style mid-file
- Do NOT add dependencies beyond the 4 specified

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: NO (no test setup)
- **Automated tests**: None for this task (dependency update)
- **QA**: Agent-executed scenario verification only

### QA Policy
Every task MUST include agent-executed QA scenarios.

- **pip install**: Bash — run `pip install -r requirements.txt`, verify exit code 0
- **Import check**: Bash — run `python -c "import ..."` for each package
- **File check**: Bash — verify file content with `cat requirements.txt`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Single task — one file to edit):
├── Task 1: Update requirements.txt [quick]
```

### Dependency Matrix
- **1**: None — can start immediately

---

## TODOs

- [x] 1. Update requirements.txt with missing dependencies

  **What to do**:
  - Replace the current `requirements.txt` content with the full sorted list
  - Maintain alphabetical order
  - Keep existing version pinning style (`>=X.Y,<X+1.0`)

  **Must NOT do**:
  - Do not modify the version bounds of existing entries (`httpx`, `numpy`)
  - Do not add any extras (no comments, no section headers)
  - Do not create `requirements-dev.txt`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file edit with trivial content changes. No domain expertise needed.
  - **Skills**: `[]`
    - No specialized skills required.

  **Parallelization**:
  - **Can Run In Parallel**: NO (single task)
  - **Parallel Group**: Wave 1
  - **Blocks**: None (final task)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `requirements.txt` (root) — Current file to edit. Read before modifying.
  - Version bound pattern from existing entries: `httpx>=0.27,<1.0`, `numpy>=1.24,<2.0`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Fresh pip install succeeds
    Tool: Bash
    Preconditions: requirements.txt has been updated with all 6 entries. Virtual environment may be active or not — test with --dry-run first.
    Steps:
      1. Run `pip install --dry-run -r requirements.txt 2>&1`
      2. Assert exit code is 0
      3. Verify output mentions all 6 packages: httpx, numpy, sqlalchemy, jinja2, python-dotenv, pytest
    Expected Result: pip reports all packages would be installed. No version conflicts.
    Failure Indicators: pip exits with non-zero. Missing packages in output. Version conflict errors.
    Evidence: .sisyphus/evidence/task-1-pip-dryrun.txt

  Scenario: All packages import successfully
    Tool: Bash
    Preconditions: pip install -r requirements.txt completed successfully
    Steps:
      1. Run `python -c "import httpx; import numpy; import sqlalchemy; import jinja2; import dotenv; import pytest; print('ALL IMPORTS OK')"`
      2. Assert exit code is 0
      3. Assert stdout contains "ALL IMPORTS OK"
    Expected Result: All 6 packages import without ImportError.
    Failure Indicators: ImportError for any package. Non-zero exit code.
    Evidence: .sisyphus/evidence/task-1-import-check.txt

  Scenario: File content is correct and sorted
    Tool: Bash
    Preconditions: requirements.txt exists at project root
    Steps:
      1. Run `cat requirements.txt`
      2. Verify exactly 6 non-empty lines
      3. Verify entries are alphabetically sorted
      4. Verify no comments or section headers
      5. Verify httpx and numpy entries are unchanged from original
    Expected Result:
      httpx>=0.27,<1.0
      jinja2>=3.1,<4.0
      numpy>=1.24,<2.0
      pytest>=8.0,<9.0
      python-dotenv>=1.0,<2.0
      sqlalchemy>=2.0,<3.0
    Failure Indicators: Wrong order. Modified existing entries. Missing entries. Extra entries.
    Evidence: .sisyphus/evidence/task-1-file-content.txt
  ```

  **Evidence to Capture:**
  - [ ] `.sisyphus/evidence/task-1-pip-dryrun.txt`
  - [ ] `.sisyphus/evidence/task-1-import-check.txt`
  - [ ] `.sisyphus/evidence/task-1-file-content.txt`

  **Commit**: YES
  - Message: `chore: add missing dependencies to requirements.txt`
  - Files: `requirements.txt`
  - Pre-commit: `pip install --dry-run -r requirements.txt`

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan and verify: requirements.txt has exactly the right content. All 6 entries present. Existing entries untouched. Evidence files exist.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Real Manual QA** — `unspecified-high`
  From clean state: `pip install -r requirements.txt` → verify all imports work.
  Output: `Scenarios [N/N pass] | VERDICT`

---

## Commit Strategy

- **1**: `chore: add missing dependencies to requirements.txt` — `requirements.txt`, `pip install --dry-run -r requirements.txt`

---

## Success Criteria

### Verification Commands
```bash
pip install --dry-run -r requirements.txt       # Expected: exit 0, lists all 6 packages
python -c "import httpx,numpy,sqlalchemy,jinja2,dotenv,pytest; print('OK')"  # Expected: prints OK
cat requirements.txt            # Expected: 6 sorted entries, no extras
```

### Final Checklist
- [x] `requirements.txt` has all 6 entries (2 existing + 4 new)
- [x] Existing `httpx` and `numpy` entries are unchanged
- [x] New entries use `>=X.Y,<X+1.0` pinning
- [x] `pip install` succeeds
- [x] All imports work
- [x] Evidence files captured
