# Plan: Web Viewer (Jinja2 + Chart.js)

## TL;DR

> **Quick Summary**: Build a lightweight HTTP web viewer for benchmark data using Python `http.server`, Jinja2 templates, and Chart.js CDN. Four routes, four templates, mobile-first responsive CSS with dark/light theme toggle.
>
> **Deliverables**:
> - `llm_race/web/server.py` — HTTP server with route dispatch, Jinja2 rendering, DB integration
> - `llm_race/web/__main__.py` — entry point: `python -m llm_race.web`
> - `llm_race/web/templates/base.html` — layout + theme toggle
> - `llm_race/web/templates/index.html` — benchmark list with filters
> - `llm_race/web/templates/compare.html` — side-by-side comparison with Chart.js
> - `llm_race/web/templates/timeseries.html` — time-series charts
> - `llm_race/web/static/style.css` — responsive CSS, dark/light theme
> - `llm_race/config/__init__.py` — add `WEB_PORT`, `WEB_HOST`
> - `tests/test_web.py` — TDD test suite
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 → Tasks 4-7 → Task 8

---

## Context

### Original Request

[GitHub Issue #6](https://github.com/danieltvela/llm-race/issues/6): Implement web viewer with Jinja2 + Chart.js. The existing web module is a stub.

### Interview Summary

**Key Discussions**:
- **Test strategy**: TDD (RED-GREEN-REFACTOR) — each task writes tests first
- **Default port**: 8080, configurable via env var or CLI flag
- **DB initialization**: Auto-create tables on startup if DB file doesn't exist
- **Design**: Follow AGENTS.md conventions — dark theme default, light toggle, mobile-first, Chart.js from CDN, no Bootstrap, no SPA framework

**Research Findings**:
- DB layer fully implemented: `llm_race/db/models.py` (SQLAlchemy ORM), `llm_race/db/queries.py` (list_benchmarks, compare_runs, timeseries), `llm_race/db/types.py` (dataclasses)
- Queries return dataclass objects with `datetime` fields — need JSON serialization for Chart.js
- `jinja2>=3.1` already in `requirements.txt`
- Web module is entirely empty: `server.py` is a 4-line stub, `templates/` and `static/` are empty
- No `__main__.py` in `web/` — needs creation
- Current package `__main__.py` points to bench CLI, unchanged
- Existing tests at `tests/test_queries.py`, `tests/test_models.py`, `tests/test_system.py`

### Metis Review

**Identified Gaps** (addressed):
- **JSON serialization of datetimes**: Metis flagged that `TimeseriesPoint` and `BenchmarkDetail` contain `datetime` objects. Resolved by adding a custom JSON encoder in server.py and ISO-format serialization in route handlers.
- **Pagination in UI**: `list_benchmarks()` returns paginated results. Resolved by adding prev/next navigation with page tracking in index.html and URL query params.
- **`__main__.py` conflict**: Current `__main__.py` runs bench CLI. Resolved by creating a separate `__main__.py` in `web/` subpackage — no changes to existing entry point.
- **Web config constants**: Added `WEB_PORT` and `WEB_HOST` to `llm_race/config/__init__.py`.
- **CSV export data format**: All benchmark fields + metric columns, ISO-formatted datetimes.

---

## Work Objectives

### Core Objective
Build a functional web viewer that reads from the existing SQLite database and renders benchmark data via Jinja2 templates with Chart.js visualizations.

### Concrete Deliverables
- `llm_race/web/server.py` — HTTP server
- `llm_race/web/__main__.py` — entry point
- `llm_race/web/templates/base.html` — layout
- `llm_race/web/templates/index.html` — list/filter
- `llm_race/web/templates/compare.html` — comparison
- `llm_race/web/templates/timeseries.html` — time-series
- `llm_race/web/static/style.css` — styles
- `tests/test_web.py` — TDD tests

### Definition of Done
- [ ] `python -m llm_race.web --port 8080` starts server and is reachable at `http://127.0.0.1:8080/`
- [ ] Homepage lists benchmarks with model/provider/machine/date filters
- [ ] Compare page accepts 2-4 run_ids, shows side-by-side metrics + overlaid Chart.js charts
- [ ] Timeseries page shows performance over time with Chart.js line chart
- [ ] `/export/csv?run_id=...` downloads a CSV file
- [ ] Dark theme is default, light theme toggleable and persisted (localStorage)
- [ ] Layout is mobile-responsive (tested at 375px width)
- [ ] `pytest tests/test_web.py -v` passes

### Must Have
- Python `http.server` (not Flask/FastAPI)
- Jinja2 server-rendered pages
- Chart.js from CDN for all charts
- Mobile-first responsive CSS, no Bootstrap
- Dark theme default with light theme toggle (CSS variables + localStorage)
- Per-request DB sessions (short-lived, auto-closed)
- TDD workflow — tests written before implementation per task

### Must NOT Have (Guardrails)
- No SPA framework (no React, Vue, etc.)
- No Flask, Django, FastAPI, or other heavy frameworks
- No Bootstrap, Tailwind, or CSS frameworks
- No authentication/authorization
- No rate limiting
- No WebSocket or live-updates
- No modification to existing bench CLI entry point
- No changes to DB models or queries (read-only from web)
- No raw prompt/response text exposure

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: TDD — each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR
- **Framework**: pytest
- **TDD per task**: Write test first, verify it fails, implement, verify it passes

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Backend/API**: Bash (curl) — Send HTTP requests, assert status codes + response body content
- **Frontend/UI**: Bash (curl) — Fetch HTML, verify expected strings in response (e.g., page title, table headers, chart containers)
- **Styling**: Bash (curl) for CSS delivery + manual visual check instructions for agent
- **Library/Module**: Bash (python -m pytest) — run TDD tests

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — 3 parallel tasks):
├── Task 1: Server skeleton + routing + Jinja2 + DB + config
├── Task 2: style.css (complete stylesheet)
└── Task 3: base.html (layout + theme toggle)

Wave 2 (Pages — 4 parallel tasks, depend on Wave 1):
├── Task 4: Index page (route + template + tests)
├── Task 5: Compare page (route + template + tests)
├── Task 6: Timeseries page (route + template + tests)
└── Task 7: CSV export (route + tests)

Wave FINAL (Integration — 1 task):
└── Task 8: Integration test suite + end-to-end QA verification

Critical Path: Task 1 → Tasks 4-7 → Task 8
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 2)
```

### Dependency Matrix

- **1**: — blocks 4, 5, 6, 7, 8
- **2**: — blocks 3 (inline styles optional), 8
- **3**: — blocks 4, 5, 6, 8
- **4**: 1, 3 — blocks 8
- **5**: 1, 3 — blocks 8
- **6**: 1, 3 — blocks 8
- **7**: 1 — blocks 8
- **8**: 1, 2, 3, 4, 5, 6, 7 — final

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

---

- [x] 1. Server skeleton — routing, Jinja2, DB init, config, entry point

  **What to do**:
  - Add `WEB_PORT = 8080` and `WEB_HOST = "127.0.0.1"` to `llm_race/config/__init__.py` (read from env vars with defaults)
  - Create `llm_race/web/server.py` with:
    - `Jinja2 Environment` setup with `FileSystemLoader` pointing to `templates/`
    - Custom JSON encoder for `datetime` → ISO string
    - `BenchmarkHTTPHandler(BaseHTTPRequestHandler)` with `do_GET()` that parses URL path, dispatches to route handlers
    - Route dispatch: `/` → `handle_index()`, `/compare` → `handle_compare()`, `/timeseries` → `handle_timeseries()`, `/export/csv` → `handle_csv_export()`
    - Static file serving for `/static/*` paths
    - 404 handler for unknown routes
    - `create_server(host, port)` factory function
    - `run_server(host, port)` entry that initializes DB and starts `HTTPServer`
    - Helper: `_get_db_session()` context manager for per-request sessions (auto-close)
    - Placeholder route handlers that return 501 Not Implemented (filled in later tasks)
  - Create `llm_race/web/__main__.py` with argparse (`--port`, `--host`, `--debug`), calls `run_server()`
  - Write TDD tests in `tests/test_web.py`:
    - Test server starts and responds on port
    - Test 404 for unknown routes
    - Test static file serving returns correct content-type
    - Test `/` returns 200 with expected HTML content
    - Test `/compare` returns 200
    - Test `/timeseries` returns 200
    - Test `/export/csv` returns 200
    - Test `/static/style.css` returns 200 with `text/css` content-type

  **Must NOT do**:
  - Don't implement full route handlers — just stubs that return 501
  - Don't import from non-existent modules yet
  - Don't modify existing `llm_race/__main__.py`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Server architecture with http.server + Jinja2 integration requires careful setup. Multiple concerns (routing, config, entry point, tests). High coordination.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - Most skills target React Native or device interaction — irrelevant here

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: 4, 5, 6, 7, 8
  - **Blocked By**: None (can start immediately)

  **References**:
  **Pattern References** (existing code to follow):
  - `llm_race/db/models.py:init_db()` — DB initialization pattern (lines 189-202)
  - `llm_race/config/__init__.py` — existing config pattern (env vars, path constants)

  **API/Type References** (contracts to implement against):
  - `llm_race/db/types.py:BenchmarkFilters` — query parameter structure for filters
  - `llm_race/db/types.py:PaginatedResult` — pagination structure from list_benchmarks
  - `llm_race/db/types.py:TimeseriesPoint` — contains datetime fields needing JSON serialization

  **Test References** (testing patterns to follow):
  - `tests/test_queries.py` — pytest structure, fixture patterns for DB, assertion style

  **External References**:
  - Official docs: Python `http.server` — `https://docs.python.org/3/library/http.server.html`
  - Official docs: Jinja2 API — `https://jinja.palletsprojects.com/en/3.1.x/api/`

  **WHY Each Reference Matters**:
  - `init_db()` pattern shows how to initialize DB engine + session factory — replicate in server startup
  - `BenchmarkFilters` defines the exact filter fields the UI needs to pass
  - `test_queries.py` shows the project's pytest conventions (session fixtures, assertion style)
  - Python http.server docs show how to extend `BaseHTTPRequestHandler` correctly
  - Jinja2 docs show `Environment(loader=FileSystemLoader(...))` setup pattern

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] Test file exists: `tests/test_web.py` with at least 7 tests
  - [ ] `pytest tests/test_web.py -v -k "server"` → PASS (at least 5 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Server starts and responds on root
    Tool: Bash (curl)
    Preconditions: No server running on port 8080
    Steps:
      1. Run: timeout 5 python -m llm_race.web --port 8080 &
         sleep 2
      2. Run: curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/
    Expected Result: HTTP status code is 200
    Failure Indicators: Connection refused, timeout, or non-200 status
    Evidence: .sisyphus/evidence/task-1-server-start.txt

  Scenario: 404 for unknown route
    Tool: Bash (curl)
    Preconditions: Server running on port 8080
    Steps:
      1. Run: curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/nonexistent
    Expected Result: HTTP status code is 404
    Failure Indicators: 200 or 500 status
    Evidence: .sisyphus/evidence/task-1-404.txt

  Scenario: Static file serving returns CSS with correct content-type
    Tool: Bash (curl)
    Preconditions: Server running on port 8080
    Steps:
      1. Run: curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/static/style.css
      2. Run: curl -s -I http://127.0.0.1:8080/static/style.css | grep -i "content-type"
    Expected Result: Status 200, Content-Type contains "text/css"
    Failure Indicators: 404, wrong content-type
    Evidence: .sisyphus/evidence/task-1-static-css.txt

  Scenario: Index route returns placeholder (501)
    Tool: Bash (curl)
    Preconditions: Server running on port 8080 (after Task 1, route is a stub)
    Steps:
      1. Run: curl -s http://127.0.0.1:8080/
    Expected Result: Response body contains "501" or handler exists (may return stub content)
    Failure Indicators: 500 server error
    Evidence: .sisyphus/evidence/task-1-index-placeholder.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-server-start.txt — HTTP status code
  - [ ] task-1-404.txt — HTTP status code
  - [ ] task-1-static-css.txt — status + Content-Type header
  - [ ] task-1-index-placeholder.txt — response body snippet

  **Commit**: YES (groups with none — first commit)
  - Message: `feat(web): add server skeleton with routing, Jinja2, and DB init`
  - Files: `llm_race/web/server.py`, `llm_race/web/__main__.py`, `llm_race/web/__init__.py`, `llm_race/config/__init__.py`, `tests/test_web.py`
  - Pre-commit: `pytest tests/test_web.py -v -k "server"`

---

- [x] 2. Stylesheet — style.css (mobile-first responsive, dark/light theme)

  **What to do**:
  - Create `llm_race/web/static/style.css` with:
    - CSS custom properties (variables) for light and dark themes
    - `:root` and `[data-theme="light"]` color schemes
    - Dark theme default (no `data-theme` = dark)
    - Mobile-first responsive design (breakpoint at 768px for tablet/desktop)
    - Base reset: box-sizing, margin/padding reset, smooth fonts
    - Body: background color from CSS variable, font stack system UI
    - Navigation bar styles (horizontal on desktop, hamburger/menu on mobile)
    - Card component for benchmark listings
    - Table styles (horizontal scroll on mobile, sticky header)
    - Form/input/filter styles (inline on desktop, stacked on mobile)
    - Button styles (primary, secondary, small)
    - Chart container (responsive, max-width)
    - Theme toggle button (positioned top-right)
    - Footer styles
    - Utility classes (`.text-muted`, `.text-right`, `.flex`, `.grid`)
    - Transitions for theme switching (smooth color changes)

  **Must NOT do**:
  - No CSS frameworks (no Bootstrap, Tailwind)
  - No JavaScript in CSS file
  - No external font loading (system font stack only)
  - No animation beyond theme transition

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Pure CSS work — mobile-first responsive design, theming, layout. Visual/styling domain.
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - All skills target React Native or specific frameworks — irrelevant for vanilla CSS

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: 8
  - **Blocked By**: None (can start immediately)

  **References**:
  **Pattern References**:
  - `llm_race/config/__init__.py` — for understanding project structure (no CSS patterns to follow)

  **External References**:
  - CSS custom properties: `https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties`
  - Mobile-first responsive: `https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries`
  - System font stack: `https://modernfontstacks.com/` (use "System UI" stack)

  **WHY Each Reference Matters**:
  - CSS custom properties are essential for the dark/light theme toggle via `data-theme` attribute
  - Media queries pattern for mobile-first breakpoints
  - System font stack gives clean look without loading external fonts

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CSS file is served with correct content
    Tool: Bash (curl)
    Preconditions: Server running on port 8080 (Task 1 complete)
    Steps:
      1. Run: curl -s -I http://127.0.0.1:8080/static/style.css
      2. Run: curl -s http://127.0.0.1:8080/static/style.css | head -20
    Expected Result: Content-Type text/css, response contains CSS variable definitions (`--bg` or `--color` or `data-theme`)
    Failure Indicators: 404, empty file, no CSS variable definitions
    Evidence: .sisyphus/evidence/task-2-css-served.txt

  Scenario: CSS includes both dark and light theme variables
    Tool: Bash (grep on file)
    Preconditions: style.css file exists
    Steps:
      1. Run: grep -c "data-theme" llm_race/web/static/style.css || grep -c ":root" llm_race/web/static/style.css
      2. Run: grep -c "@media" llm_race/web/static/style.css
    Expected Result: Both theme selectors present, at least one media query for responsive
    Failure Indicators: Missing theme support, no responsive breakpoints
    Evidence: .sisyphus/evidence/task-2-css-themes.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-css-served.txt — first 20 lines of CSS
  - [ ] task-2-css-themes.txt — grep results for theme/media query presence

  **Commit**: YES (groups with Task 3)
  - Message: `feat(web): add responsive CSS with dark/light theme`
  - Files: `llm_race/web/static/style.css`
  - Pre-commit: None (CSS-only, no test changes)

---

- [x] 3. Base template — base.html (layout, navigation, theme toggle)

  **What to do**:
  - Create `llm_race/web/templates/base.html` with Jinja2 blocks:
    - `<!DOCTYPE html>` with `<html>` with `data-theme` attribute (theme toggle)
    - `<head>` block: title, meta viewport (`width=device-width, initial-scale=1`), link to `/static/style.css`, Chart.js CDN (`https://cdn.jsdelivr.net/npm/chart.js`), extra head block
    - `<body>` with:
      - Navigation bar: "LLM Race" brand link, links to Home (`/`), Compare (`/compare`), Timeseries (`/timeseries`), Export CSV (`/export/csv`)
      - Theme toggle button (🌙/☀️) with JavaScript for:
        - Toggle `data-theme` attribute on `<html>` between `""` (dark) and `"light"`
        - Persist choice in `localStorage`
        - On page load, read `localStorage` and apply
      - `<main>` block for page content
      - `<footer>` with "LLM Race — Benchmark Performance Viewer"
    - Jinja2 blocks: `title`, `head_extra`, `content`, `scripts`
    - Include a `{% block scripts %}{% endblock %}` before `</body>` for page-specific JS

  **Must NOT do**:
  - No inline CSS (all in style.css)
  - No hardcoded text in Spanish (project is English)
  - No heavy JS libraries beyond Chart.js

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: HTML template with responsive nav, theme toggle JS, Jinja2 blocks — UI/structure work
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: 4, 5, 6, 8
  - **Blocked By**: Task 2 (but can proceed with placeholder styles — weak dependency)

  **References**:
  **External References**:
  - Jinja2 template docs: `https://jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance`
  - Chart.js CDN: `https://www.jsdelivr.com/package/npm/chart.js`

  **WHY Each Reference Matters**:
  - Jinja2 template inheritance: `{% extends "base.html" %}` is the core pattern for child templates
  - Chart.js CDN URL needed for script tag in base template

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] Test: template renders without errors with Jinja2
  - [ ] `python -c "from jinja2 import Environment, FileSystemLoader; env=Environment(loader=FileSystemLoader('llm_race/web/templates')); t=env.get_template('base.html'); print(t.render())"` succeeds

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Base template renders valid HTML
    Tool: Bash (python)
    Preconditions: base.html exists in templates/
    Steps:
      1. Run: python -c "
  from jinja2 import Environment, FileSystemLoader
  env = Environment(loader=FileSystemLoader('llm_race/web/templates'))
  t = env.get_template('base.html')
  html = t.render(title='Test')
  print('template_length:', len(html))
  print('has_doctype:', '<!DOCTYPE html>' in html)
  print('has_chartjs:', 'chart.js' in html.lower() or 'chart.js' in html)
  print('has_theme_toggle:', 'data-theme' in html or 'theme' in html)
  print('has_nav:', '<nav' in html or 'navbar' in html)
  print('has_content_block:', '{% block content' in open('llm_race/web/templates/base.html').read())
  "
    Expected Result: All checks pass (has_doctype, has_chartjs_script, has_theme_toggle, has_nav, has_content_block)
    Failure Indicators: Missing any required element
    Evidence: .sisyphus/evidence/task-3-base-template.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-base-template.txt — template verification output

  **Commit**: YES (groups with Task 2)
  - Message: `feat(web): add base Jinja2 template with theme toggle and Chart.js CDN`
  - Files: `llm_race/web/templates/base.html`
  - Pre-commit: python render check (see QA scenario)

---

- [x] 4. Index page — benchmark list with filters

  **What to do**:
  - In `llm_race/web/server.py`, implement `handle_index(self, params)`:
    - Parse query params into `BenchmarkFilters`: `model_name`, `provider_name`, `machine_hostname`, `date_start`, `date_end`, `status`, `workload_profile`, `prompt_size`
    - Parse pagination: `page`, `limit` (default page=1, limit=20)
    - Open DB session, call `list_benchmarks(session, filters, sort_by, sort_order, offset=(page-1)*limit, limit=limit)`
    - Compute pagination values: `prev_page`, `next_page`, `total_pages`, `has_prev`, `has_next`
    - Get unique filter options for dropdowns: query distinct model names, provider names, machine hostnames from DB
    - Render `index.html` with context: benchmarks (PaginatedResult), filters, pagination, filter_options
    - Return 200 with rendered HTML
  - Create `llm_race/web/templates/index.html` extending `base.html`:
    - `{% extends "base.html" %}`
    - Title: "Benchmarks — LLM Race"
    - Filter form (GET to `/`):
      - Model name: text input
      - Provider: dropdown (populated from filter_options)
      - Machine: dropdown
      - Date range: two date inputs (start, end)
      - Status: dropdown (running, completed, failed)
      - Workload profile: dropdown
      - Prompt size: dropdown
      - Submit and Reset buttons
    - Results table with columns: Run ID, Model, Provider, Machine, Workload, Concurrency, Throughput (TPS), E2E Mean (ms), Status, Started At
    - Table row clickable → links to compare page
    - Pagination: "Previous" / "Next" buttons, "Page N of M" display
    - Empty state: "No benchmarks found" message
  - Write TDD tests:
    - Test index page renders with no filters
    - Test filter by model_name works
    - Test pagination: page parameter works
    - Test empty DB shows "No benchmarks" message
    - Test filter form fields exist in HTML

  **Must NOT do**:
  - Don't expose raw prompt/response text
  - No authentication

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Server route handler + Jinja2 template + query integration + form handling. Multiple concerns.
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: 8
  - **Blocked By**: Tasks 1, 3

  **References**:
  **Pattern References**:
  - `llm_race/db/queries.py:list_benchmarks()` — the exact query function used (lines 32-107)
  - `llm_race/db/types.py:BenchmarkFilters` — dataclass to construct from query params

  **API/Type References**:
  - `llm_race/db/types.py:PaginatedResult` — has `items`, `total_count`, `offset`, `limit`
  - `llm_race/db/types.py:BenchmarkSummary` — fields available in each benchmark row

  **Test References**:
  - `tests/test_queries.py:test_list_benchmarks` — shows how to populate test DB data

  **WHY Each Reference Matters**:
  - `list_benchmarks()` signature: `(session, filters, sort_by, sort_order, offset, limit)` — must pass correct args
  - `BenchmarkFilters` frozen dataclass — construct from dict using `BenchmarkFilters(**kwargs)`
  - `PaginatedResult` pagination properties needed for prev/next navigation

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] `tests/test_web.py` has tests for index page (at least 5 tests)
  - [ ] `pytest tests/test_web.py -v -k "index"` -> PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Index page renders benchmark list
    Tool: Bash (curl)
    Preconditions: Server running, test DB with sample data
    Steps:
      1. Run: curl -s http://127.0.0.1:8080/
    Expected Result: HTML response with <table> or benchmark listing, status 200
    Failure Indicators: 500 error, empty response, "Not Implemented" message
    Evidence: .sisyphus/evidence/task-4-index-render.txt

  Scenario: Filter form fields exist
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s http://127.0.0.1:8080/ | grep -c "model_name\|provider\|machine\|date_start\|date_end"
    Expected Result: At least 3 filter input fields found
    Failure Indicators: No filter fields in HTML
    Evidence: .sisyphus/evidence/task-4-filters.txt

  Scenario: Pagination controls present
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s "http://127.0.0.1:8080/?page=1" | grep -ci "page\|prev\|next"
    Expected Result: At least one pagination control found
    Failure Indicators: No pagination HTML
    Evidence: .sisyphus/evidence/task-4-pagination.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-index-render.txt — first 100 chars of HTML response
  - [ ] task-4-filters.txt — count of filter fields
  - [ ] task-4-pagination.txt — evidence of pagination

  **Commit**: YES
  - Message: `feat(web): add index page with benchmark list and filters`
  - Files: `llm_race/web/server.py`, `llm_race/web/templates/index.html`, `tests/test_web.py`
  - Pre-commit: `pytest tests/test_web.py -v -k "index"`

---

- [x] 5. Compare page — side-by-side benchmark comparison with Chart.js

  **What to do**:
  - In `llm_race/web/server.py`, implement `handle_compare(self, params)`:
    - Parse `run_ids` from query string (comma-separated or multiple `run_id` params)
    - Validate: 2-4 run_ids required. If invalid, render error message.
    - Open DB session, call `compare_runs(session, run_ids)`
    - Build comparison data structure:
      - Metrics table: rows = metric name, columns = each run's value
      - Chart datasets: one dataset per run, labels = metric names
    - Serialize `datetime` objects to ISO strings for JSON
    - Render `compare.html` with context: runs (list of BenchmarkDetail), metrics_table, chart_data (JSON for Chart.js)
  - Create `llm_race/web/templates/compare.html` extending `base.html`:
    - Title: "Compare Runs — LLM Race"
    - Run selection form: text input for run IDs (comma-separated), or link from index page
    - Side-by-side metrics table:
      - Column 1: Metric name
      - Columns 2-5: Each run's value (with run_id/model_name as header)
    - Chart.js bar chart comparing key metrics across runs
    - Per-run details section (expandable): model info, machine info, timestamps
    - Error state: "Please select 2-4 runs to compare"
  - Write TDD tests:
    - Test compare page with valid run_ids returns 200
    - Test compare page with invalid run_ids shows error
    - Test compare page with 1 run_id shows validation error
    - Test metrics table renders correct metric names
    - Test chart data JSON is present in page

  **Must NOT do**:
  - Don't allow comparison with less than 2 or more than 4 runs
  - No modification to `compare_runs()` query

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex route handler + JSON serialization + Chart.js data preparation + template with charts
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7)
  - **Blocks**: 8
  - **Blocked By**: Tasks 1, 3

  **References**:
  **Pattern References**:
  - `llm_race/db/queries.py:compare_runs()` — lines 110-145, returns list of BenchmarkDetail
  - `llm_race/db/types.py:BenchmarkDetail` — full metrics + nested results

  **External References**:
  - Chart.js bar chart: `https://www.chartjs.org/docs/latest/charts/bar.html`
  - Chart.js line chart: `https://www.chartjs.org/docs/latest/charts/line.html`
  - JSON in Jinja2: `https://jinja.palletsprojects.com/en/3.1.x/templates/#tojson-filter`

  **WHY Each Reference Matters**:
  - `compare_runs()` returns ordered BenchmarkDetail list — use run_id/model_name as series labels
  - `tojson` filter in Jinja2 serializes Python objects to JS-safe JSON
  - Chart.js bar chart for side-by-side metric comparison

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] `tests/test_web.py` has tests for compare page (at least 4 tests)
  - [ ] `pytest tests/test_web.py -v -k "compare"` -> PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Compare page renders with chart container
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s "http://127.0.0.1:8080/compare?run_id=a,b" | grep -ci "<canvas\|chart-container\|chart_"
    Expected Result: At least one chart-related element found in HTML
    Failure Indicators: No chart container, 500 error
    Evidence: .sisyphus/evidence/task-5-chart-container.txt

  Scenario: Compare page shows validation error with 1 run_id
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s "http://127.0.0.1:8080/compare?run_id=abc-123" | grep -ci "2-4\|error\|invalid\|select"
    Expected Result: HTML contains validation message about needing 2-4 runs
    Failure Indicators: 500 error, empty page
    Evidence: .sisyphus/evidence/task-5-validation.txt
  ```

  **Evidence to Capture:**
  - [ ] task-5-chart-container.txt — chart element evidence
  - [ ] task-5-validation.txt — validation message evidence

  **Commit**: YES
  - Message: `feat(web): add compare page with Chart.js side-by-side metrics`
  - Files: `llm_race/web/server.py`, `llm_race/web/templates/compare.html`, `tests/test_web.py`
  - Pre-commit: `pytest tests/test_web.py -v -k "compare"`

---

- [x] 6. Timeseries page — performance over time with Chart.js

  **What to do**:
  - In `llm_race/web/server.py`, implement `handle_timeseries(self, params)`:
    - Parse query params: `model`, `provider`, `metric` (default: `throughput_tps`), `date_start`, `date_end`, `level` (default: `benchmark`)
    - Validate metric against allowed list (use whitelists from queries.py)
    - Open DB session, call `timeseries(session, model, provider, metric, date_start, date_end, level)`
    - Convert `TimeseriesPoint` datetimes to ISO strings for JSON
    - Compute available models/providers/metrics for filter dropdowns
    - Render `timeseries.html` with context: points (JSON), filters, metric_options, model_options, provider_options
  - Create `llm_race/web/templates/timeseries.html` extending `base.html`:
    - Title: "Timeseries — LLM Race"
    - Filter form (GET to `/timeseries`):
      - Model: dropdown (populated from model_options)
      - Provider: dropdown
      - Metric: dropdown with metric_options
      - Date range: start/end date inputs
      - Submit button
    - Chart.js line chart:
      - X-axis: date (started_at)
      - Y-axis: metric value
      - Tooltip showing exact value + run_id + date
    - Data table below chart
    - Empty state: "No data for selected filters"
  - Write TDD tests:
    - Test timeseries page renders with default params
    - Test filter by model works
    - Test invalid metric shows error
    - Test chart data JSON is present and valid JSON
    - Test points are in date order

  **Must NOT do**:
  - Don't expose individual result-level data in charts by default
  - No real-time updates

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Route handler + query integration + JSON data pipeline for Chart.js + filter form
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7)
  - **Blocks**: 8
  - **Blocked By**: Tasks 1, 3

  **References**:
  **Pattern References**:
  - `llm_race/db/queries.py:timeseries()` — lines 222-258, returns list of TimeseriesPoint
  - `llm_race/db/types.py:TimeseriesPoint` — dataclass with `date` (datetime), `value` (float), `run_id`, `label`

  **External References**:
  - Chart.js time series: `https://www.chartjs.org/docs/latest/charts/line.html`
  - Chart.js Time Axis: `https://www.chartjs.org/docs/latest/axes/cartesian/time.html`

  **WHY Each Reference Matters**:
  - `timeseries()` returns sorted-by-date points — direct input for Chart.js datasets
  - `TimeseriesPoint.date` is datetime — must ISO-format for JSON
  - Chart.js line chart with string dates on X axis works without date adapter

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] `tests/test_web.py` has tests for timeseries page (at least 4 tests)
  - [ ] `pytest tests/test_web.py -v -k "timeseries"` -> PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Timeseries page renders with chart container
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s "http://127.0.0.1:8080/timeseries" | grep -ci "<canvas\|chart-container\|timeseries-chart"
    Expected Result: At least one chart element found
    Failure Indicators: No chart container in HTML
    Evidence: .sisyphus/evidence/task-6-timeseries-render.txt

  Scenario: Timeseries page has filter form
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s "http://127.0.0.1:8080/timeseries" | grep -ci "model\|provider\|metric\|date_start\|date_end"
    Expected Result: At least 2 filter fields found
    Failure Indicators: No filter controls
    Evidence: .sisyphus/evidence/task-6-timeseries-filters.txt
  ```

  **Evidence to Capture:**
  - [ ] task-6-timeseries-render.txt — chart element evidence
  - [ ] task-6-timeseries-filters.txt — filter field evidence

  **Commit**: YES
  - Message: `feat(web): add timeseries page with Chart.js line chart`
  - Files: `llm_race/web/server.py`, `llm_race/web/templates/timeseries.html`, `tests/test_web.py`
  - Pre-commit: `pytest tests/test_web.py -v -k "timeseries"`

---

- [x] 7. CSV export route

  **What to do**:
  - In `llm_race/web/server.py`, implement `handle_csv_export(self, params)`:
    - Parse query params: `run_id` (optional, single run), or export all with filters (same as index filters)
    - If `run_id` provided: fetch single benchmark via `compare_runs()`, export its results
    - If filters provided: fetch benchmarks via `list_benchmarks()`, export summary
    - Build CSV content:
      - Headers: run_id, model_name, provider, hostname, workload, prompt_size, concurrency, started_at, completed_at, wall_clock_seconds, total_requests, successful, failed, throughput_tps, e2e_mean_ms, e2e_p50_ms, e2e_p90_ms, e2e_p99_ms, ttft_mean_ms, itl_mean_ms, status
      - Rows: one per benchmark, ISO-formatted datetimes
    - Set headers: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="benchmarks.csv"`
    - Return 200 with CSV body
  - Write TDD tests:
    - Test CSV export returns 200 with text/csv content-type
    - Test CSV export with run_id returns data for that run
    - Test CSV has correct headers
    - Test CSV with no filters exports all

  **Must NOT do**:
  - Don't include raw prompt/response text in CSV
  - Don't modify existing DB queries

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single route handler, CSV formatting, simple tests. Clear scope.
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: 8
  - **Blocked By**: Task 1

  **References**:
  **Pattern References**:
  - `llm_race/db/types.py:BenchmarkSummary` — fields to export as CSV columns

  **External References**:
  - Python csv module: `https://docs.python.org/3/library/csv.html`

  **WHY Each Reference Matters**:
  - Use `csv.writer` with `io.StringIO` for in-memory CSV generation
  - `BenchmarkSummary` fields map directly to CSV columns

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] `tests/test_web.py` has tests for CSV export (at least 3 tests)
  - [ ] `pytest tests/test_web.py -v -k "csv"` -> PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CSV export returns CSV with correct headers
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Run: curl -s -I http://127.0.0.1:8080/export/csv
      2. Run: curl -s http://127.0.0.1:8080/export/csv | head -3
    Expected Result: Content-Type is text/csv, first line contains CSV column headers
    Failure Indicators: Wrong content-type, empty response, HTML instead of CSV
    Evidence: .sisyphus/evidence/task-7-csv-headers.txt
  ```

  **Evidence to Capture:**
  - [ ] task-7-csv-headers.txt — Content-Type + first 3 lines

  **Commit**: YES
  - Message: `feat(web): add CSV export endpoint`
  - Files: `llm_race/web/server.py`, `tests/test_web.py`
  - Pre-commit: `pytest tests/test_web.py -v -k "csv"`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present results to user for explicit "okay" before completing.
> Do NOT auto-proceed. Wait for user's explicit approval.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest` + linter. Review all changed files for: empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together). Test edge cases: empty DB, invalid params, page beyond range.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **Task 1**: `feat(web): add server skeleton with routing, Jinja2, and DB init` — `llm_race/web/server.py`, `llm_race/web/__main__.py`, `llm_race/web/__init__.py`, `llm_race/config/__init__.py`, `tests/test_web.py`
- **Tasks 2-3**: `feat(web): add responsive CSS and base Jinja2 template` — `llm_race/web/static/style.css`, `llm_race/web/templates/base.html`
- **Task 4**: `feat(web): add index page with benchmark list and filters` — `llm_race/web/server.py`, `llm_race/web/templates/index.html`, `tests/test_web.py`
- **Task 5**: `feat(web): add compare page with Chart.js side-by-side metrics` — `llm_race/web/server.py`, `llm_race/web/templates/compare.html`, `tests/test_web.py`
- **Task 6**: `feat(web): add timeseries page with Chart.js line chart` — `llm_race/web/server.py`, `llm_race/web/templates/timeseries.html`, `tests/test_web.py`
- **Task 7**: `feat(web): add CSV export endpoint` — `llm_race/web/server.py`, `tests/test_web.py`

---

## Success Criteria

### Verification Commands
```bash
python -m llm_race.web --port 8080 &  # Start server
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/  # Expect: 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/compare  # Expect: 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/timeseries  # Expect: 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/export/csv  # Expect: 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/static/style.css  # Expect: 200
curl -s http://127.0.0.1:8080/ | grep -c "<!DOCTYPE html>"  # Expect: 1
pytest tests/test_web.py -v  # Expect: all pass
```

### Final Checklist
- [ ] `python -m llm_race.web` starts server on port 8080
- [ ] All 4 routes return 200
- [ ] Static files served correctly
- [ ] Dark theme default, light theme toggleable
- [ ] Mobile-responsive layout (test at 375px)
- [ ] TDD tests all pass
- [ ] No Bootstrap, no SPA framework used
- [ ] `jinja2` already in requirements.txt (no changes needed)

