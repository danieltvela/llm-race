# Learnings — Web Viewer

## F4 Scope Fidelity Check (2026-06-28)

- The plan assumed the DB layer was already fully implemented, but the git history shows `llm_race/db/models.py` and `llm_race/db/schema.sql` were stubs before this work. Implementing them was a necessary prerequisite for the web viewer to function.
- Task-level decomposition was followed closely: Task 1 used proper 501 placeholders for route handlers before Tasks 4-7 filled them in.
- TDD workflow produced 23 passing tests in `tests/test_web.py` covering routing, static files, filters, pagination, compare, timeseries, and CSV export.
- Static file serving works for GET; `HEAD` requests return 501 because `BaseHTTPRequestHandler` does not implement `do_HEAD` in this server.
