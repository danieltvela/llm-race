# decisions — db-queries test scaffolding

## Choices made
1. **`query_session` extends `db_session`** — Uses dependency injection (`query_session(db_session)`) so it inherits the fresh DB file pattern, then populates it with reference data.
2. **Factory defaults match `_create_minimal_*` helpers** — Same field names and defaults for consistency with existing test_models.py patterns.
3. **`create_result` auto-increments `request_id`** — Falls back to `benchmark.results[-1].request_id + 1` if no results exist yet, defaulting to 1.
4. **Reference data stored on session** — `session.query_session_data` dict holds lists of created models, machines, benchmarks, and results for easy test assertions.
5. **Timezone-aware datetimes** — All `started_at` values use `datetime(..., tzinfo=timezone.utc)` per project convention, even though models default to naive `datetime.utcnow()`.