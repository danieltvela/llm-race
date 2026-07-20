# Model Slug Identification Refactor

## Context
- Origin: Direct user instruction
- Summary: Replace the flat model identification (current `name` + `version` + `quantization` + `provider_name`) with a structured slug-based system. Each model is uniquely identified by a slug composed of `ai_lab`, `name`, `quantization`, and an optional `extra`. Every benchmark run must specify this slug. If a model with that slug already exists, the benchmark is added to it; otherwise, a new model record is created.
- Assumptions made:
  - The `name` field within the slug doubles as the API model string sent to providers (e.g., `"Qwen3-8B"` for vLLM, `"llama3.2"` for Ollama).
  - Slug format: `{ai_lab}/{name}/{quantization}` or `{ai_lab}/{name}/{quantization}/{extra}` (all lowercase, non-alphanumeric chars in name/extra replaced with `-`).
  - CLI accepts both `--slug` (composite) and individual `--ai-lab`, `--name`, `--quantization`, `--extra` flags. They are mutually exclusive; `--slug` takes precedence.
  - No migration — old `benchmarks.db` data is discarded (breaking schema change on a dev tool).
  - The existing `version` column is dropped (was always NULL; superseded by the new structured fields).
  - The `provider_name` field stays on the Model (a model may be served by different providers, each is a different DB record — slug + provider_name together could be thought of as the deployment identity, but the slug alone is the model identity for the benchmark system).

---

## Phase 1: Slug utility module

Create a new module that handles slug generation, validation, and parsing.

- [ ] Step 1.1: Create `llm_race/utils/slug.py`
  - File(s): `llm_race/utils/slug.py` (new file)
  - Change: Create a module with these functions:
    - `build_slug(ai_lab: str, name: str, quantization: str, extra: str | None = None) -> str`
      - Lowercase all inputs.
      - For `ai_lab`, `name`, `quantization`: replace any character not in `[a-z0-9]` with `-`, collapse consecutive `-`, trim leading/trailing `-`.
      - For `extra` (optional): same normalization as above.
      - Format: `f"{ai_lab}/{name}/{quantization}"` or `f"{ai_lab}/{name}/{quantization}/{extra}"` if extra is provided and non-empty.
      - Raise `ValueError` if any of `ai_lab`, `name`, or `quantization` is empty after normalization.
    - `parse_slug(slug: str) -> dict[str, str | None]`
      - Split by `/`. Must yield 3 or 4 parts.
      - Return `{"ai_lab": ..., "name": ..., "quantization": ..., "extra": ...}` (extra is `None` if 3 parts).
      - Raise `ValueError` if slug has fewer than 3 or more than 4 parts, or any required part is empty.
    - `validate_slug(slug: str) -> bool`
      - Returns True if slug parses correctly (3 or 4 non-empty parts), False otherwise.
  - Acceptance criteria: All functions behave as specified. Unit tests will be added in Phase 9.

---

## Phase 2: Update database models

Modify the SQLAlchemy ORM Model class and the raw schema DDL.

- [ ] Step 2.1: Update `Model` class in `llm_race/db/models.py`
  - File(s): `llm_race/db/models.py`
  - Change:
    - Add new columns to the `Model` class:
      - `slug: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)`
      - `ai_lab: Mapped[str] = mapped_column(String(100), nullable=False)`
      - `extra: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)`
    - Keep existing columns: `id`, `name`, `quantization`, `provider_name`, `context_window`, `created_at`.
    - Remove the `version` column entirely (`Mapped[Optional[str]] = mapped_column(String(50), nullable=True)`).
    - Replace the `__table_args__` UniqueConstraint from `(name, version, quantization, provider_name)` to a single unique constraint on `slug` (SQLAlchemy handles this via the `unique=True` on the `slug` column, so the explicit `UniqueConstraint` tuple is no longer needed — remove it).
  - Acceptance criteria: `python -c "from llm_race.db.models import Model; print(Model.__table__.columns.keys())"` shows the new columns and no `version`.

- [ ] Step 2.2: Update `llm_race/db/schema.sql`
  - File(s): `llm_race/db/schema.sql`
  - Change: Update the `models` table DDL:
    - Add `slug VARCHAR(500) NOT NULL` before `name`.
    - Add `ai_lab VARCHAR(100) NOT NULL` after `slug`.
    - Add `extra VARCHAR(100)` after `quantization`.
    - Remove `version VARCHAR(50)`.
    - Replace `UNIQUE(name, version, quantization, provider_name)` with `UNIQUE(slug)`.
  - Acceptance criteria: The SQL file matches the ORM model structure. Review visually.

---

## Phase 3: Update data layer types

Modify the dataclasses used for query results and filters.

- [ ] Step 3.1: Update `ModelSummary` in `llm_race/db/types.py`
  - File(s): `llm_race/db/types.py`
  - Change:
    - Add fields: `slug: str`, `ai_lab: str`, `extra: str | None`.
    - Remove field: `version: str | None`.
  - Acceptance criteria: `python -c "from llm_race.db.types import ModelSummary; print([f.name for f in __import__('dataclasses').fields(ModelSummary)])"` shows the new fields and no `version`.

- [ ] Step 3.2: Update `BenchmarkFilters` in `llm_race/db/types.py`
  - File(s): `llm_race/db/types.py`
  - Change:
    - Add field: `slug: str | None = None` (for exact slug match filter).
    - The existing `model_name` field stays (renamed conceptually to filter by `Model.name`, which remains as the API model string for search).
    - Add field: `ai_lab: str | None = None` (for lab filtering).
  - Acceptance criteria: New fields are available and default to `None`.

- [ ] Step 3.3: Update `BenchmarkSummary`, `BenchmarkDetail`, `BenchmarkGroupSummary` in `llm_race/db/types.py`
  - File(s): `llm_race/db/types.py`
  - Change:
    - Add field `model_slug: str` to `BenchmarkSummary`, `BenchmarkDetail`, and `BenchmarkGroupSummary`.
    - Add field `ai_lab: str` to all three (optional for now, keeps backward compat with existing display patterns).
  - Acceptance criteria: All three dataclasses have `model_slug: str` field (position after `model_name`).

---

## Phase 4: Update the data saver (find-or-create logic)

- [ ] Step 4.1: Update `save_benchmark_run()` signature and logic in `llm_race/db/saver.py`
  - File(s): `llm_race/db/saver.py`
  - Change:
    - Replace the `model_name: str` parameter with `model_slug: str`.
    - Import `parse_slug` from `llm_race.utils.slug`.
    - In the find-or-create Model logic (lines 68-83):
      - First, parse the slug: `parsed = parse_slug(model_slug)`.
      - Query for an existing Model by **slug** (exact match): `select(Model).where(Model.slug == model_slug)`.
      - If not found, create a new Model with the parsed fields:
        ```python
        Model(
            slug=model_slug,
            ai_lab=parsed["ai_lab"],
            name=parsed["name"],        # API model string
            quantization=parsed["quantization"],
            extra=parsed.get("extra"),
            provider_name=provider_type,
        )
        ```
      - Remove the old query that matches on `(name, version, quantization, provider_name)`.
    - Update the docstring to reflect the new parameter.
  - Acceptance criteria: Two calls with the same slug only create one Model row. Two calls with different slugs create separate rows. A call with a new slug for the same provider creates a new row.

---

## Phase 5: Update CLI

- [ ] Step 5.1: Add slug arguments to `llm_race/bench/cli.py`
  - File(s): `llm_race/bench/cli.py`
  - Change:
    - Remove the `--model` argument from `run_parser`.
    - Add a mutually exclusive group (using `argparse` mutually exclusive group) with:
      - `--slug`: Accept the composite slug string (e.g., `qwen/qwen3-8b/none`).
      - `--ai-lab`, `--name`, `--quantization`: Three required strings (when using individual flags).
      - `--extra`: Optional fourth string, only valid when using individual flags.
    - Import `build_slug` and `validate_slug` from `llm_race.utils.slug`.
    - After argument parsing: if `--slug` was provided, validate it. If individual flags were provided, build the slug with `build_slug(args.ai_lab, args.name, args.quantization, args.extra)`. Store the result in a `model_slug` variable.
    - Pass `model_slug` to `run_benchmarks()` instead of `args.model`.
    - For the provider API call, pass `parsed["name"]` (the API model string) from the slug parsed components. The actual provider model name is extracted from the slug's `name` component.
    - Update the `--preset` logic (lines 112-131) to work with slug: preset overrides should apply to slug components, not a flat model string. If preset provides a `slug`, use it to set `model_slug`.
    - Remove `DEFAULT_MODEL` import and replace with `DEFAULT_MODEL_SLUG` (see Step 6.1).
    - Remove `LLM_RACE_MODEL` env var reference; replace with `LLM_RACE_MODEL_SLUG`.
  - Acceptance criteria: `python -m llm_race.bench.cli run --help` shows the new slug arguments and no `--model` argument.

- [ ] Step 5.2: Update the runner signature in `llm_race/bench/runner.py`
  - File(s): `llm_race/bench/runner.py`
  - Change:
    - In `run_benchmarks()`: replace the `model: str` parameter with `model_slug: str` and `model_api_name: str`.
      - `model_slug` is the composite slug (e.g., `qwen/qwen3-8b/none`) — used for DB persistence.
      - `model_api_name` is the actual model string to send to the provider API (e.g., `Qwen3-8B`) — extracted from the slug's `name` component or provided separately.
    - In `run_scenario()`: keep the `model: str` parameter (it receives the API model name for provider calls). No change needed here.
    - When calling `save_benchmark_run()`, pass `model_slug=model_slug` instead of `model_name=model`.
    - Update log messages to show both slug and API name where relevant.
  - Acceptance criteria: Runner still works correctly: provider receives the API model name, DB receives the slug. 

---

## Phase 6: Update config defaults

- [ ] Step 6.1: Update `llm_race/config/__init__.py`
  - File(s): `llm_race/config/__init__.py`
  - Change:
    - Remove `DEFAULT_MODEL = os.environ.get("LLM_RACE_MODEL", "Qwen3-8B")`.
    - Add `DEFAULT_MODEL_SLUG = os.environ.get("LLM_RACE_MODEL_SLUG", "qwen/qwen3-8b/none")`.
    - Add `DEFAULT_AI_LAB = os.environ.get("LLM_RACE_AI_LAB", "qwen")`.
    - Add `DEFAULT_MODEL_NAME = os.environ.get("LLM_RACE_MODEL_NAME", "qwen3-8b")`.
    - Add `DEFAULT_QUANTIZATION = os.environ.get("LLM_RACE_QUANTIZATION", "none")`.
    - Re-export the new defaults.
  - Acceptance criteria: `from llm_race.config import DEFAULT_MODEL_SLUG; print(DEFAULT_MODEL_SLUG)` works.

- [ ] Step 6.2: Update `.env.example`
  - File(s): `.env.example`
  - Change: Replace `LLM_RACE_MODEL=Qwen3-8B` with the new env vars: `LLM_RACE_MODEL_SLUG`, `LLM_RACE_AI_LAB`, `LLM_RACE_MODEL_NAME`, `LLM_RACE_QUANTIZATION`.
  - Acceptance criteria: File reflects the new configuration.

---

## Phase 7: Update presets

- [ ] Step 7.1: Update `llm_race/config/presets.json`
  - File(s): `llm_race/config/presets.json`
  - Change: For every preset entry:
    - Replace the `"model"` field (flat string) with a `"slug"` field (composite string).
    - Add decomposed fields: `"ai_lab"`, `"name"` (API model name), `"quantization"`, `"extra"` (optional, omit if none).
    - Example for Qwen3-8B on vLLM:
      ```json
      {
          "name": "Qwen3-8B on vLLM",
          "key": "qwen3-8b-vllm",
          "provider": "vllm",
          "slug": "qwen/qwen3-8b/none",
          "ai_lab": "qwen",
          "model_api_name": "Qwen3-8B",
          "quantization": "none",
          "base_url": "http://localhost:8000/v1",
          "api_key_env": "VLLM_API_KEY",
          "description": "..."
      }
      ```
    - Note: The `name` in the slug is normalized (lowercase, dashed). The `model_api_name` field preserves the original casing for the provider API call. Add this as a new required field.
    - Update all 10 presets accordingly.
  - Acceptance criteria: All presets have `slug`, `ai_lab`, `model_api_name`, `quantization`. No preset has the old flat `model` field.

- [ ] Step 7.2: Update `llm_race/config/presets.py`
  - File(s): `llm_race/config/presets.py`
  - Change:
    - Update required fields check from `("key", "name", "provider", "model")` to `("key", "name", "provider", "slug", "ai_lab", "model_api_name", "quantization")`.
    - Update the `load_preset()` docstring.
  - Acceptance criteria: Loading a preset with missing new required fields logs a warning.

---

## Phase 8: Update CLI preset integration

- [ ] Step 8.1: Update preset merging logic in `llm_race/bench/cli.py`
  - File(s): `llm_race/bench/cli.py`
  - Change:
    - When `--preset` is specified, the preset's `slug` field sets `model_slug` (if `--slug` was not explicitly provided).
    - The preset's `model_api_name` field becomes the API model name for provider calls.
    - The preset's `provider` and `base_url` still work as before.
    - Update `_is_default` logic to check against the new defaults (`DEFAULT_MODEL_SLUG` etc.).
    - Update `--list-presets` output to display slug: `print(f"{p['key']}: {p['name']} ({p['slug']})")`.
  - Acceptance criteria: `python -m llm_race.bench.cli run --list-presets` shows slugs. `--preset qwen3-8b-vllm --no-db --help` works.

---

## Phase 9: Update web viewer

- [ ] Step 9.1: Update model listing in `llm_race/web/server.py`
  - File(s): `llm_race/web/server.py`
  - Change:
    - In `handle_models()`: update `list_models()` call — the query function already returns `ModelSummary` which now has `slug` and `ai_lab`. No signature change needed in the caller.
    - Update `model_options` dropdown populations (in `handle_index()` and `handle_timeseries()`) to query `Model.slug` distinct instead of `Model.name` distinct, for slug-based model filtering.
    - In `handle_model_benchmarks()`: the model is still looked up by `model_id` (integer PK), no change needed. The template will display the new slug fields.
  - Acceptance criteria: Web server starts without errors. `/models` page loads. `/` page loads.

- [ ] Step 9.2: Update `llm_race/web/templates/models.html`
  - File(s): `llm_race/web/templates/models.html`
  - Change:
    - Add a "Slug" column to the table between "Model" and "Provider", displaying `m.slug` as a `<code>` element.
    - The existing "Model" column now shows `m.name` (the API model name). Keep it.
    - Remove the "Version" column (since `version` field is dropped).
    - Add an "AI Lab" column showing `m.ai_lab`.
    - Update the search input placeholder to "Search by slug or name...".
  - Acceptance criteria: The models page renders with the new columns correctly. No errors.

- [ ] Step 9.3: Update `llm_race/web/templates/model_benchmarks.html`
  - File(s): `llm_race/web/templates/model_benchmarks.html`
  - Change:
    - The `<h1>` should show the model slug as the title (e.g., `model.slug`).
    - The `<div class="run-meta">` should show: `ai_lab`, `name` (API name), `quantization`, `extra` (if present), and `provider_name`.
    - Remove references to `model.version`.
  - Acceptance criteria: Model detail page shows slug prominently and metadata correctly.

- [ ] Step 9.4: Update `llm_race/web/templates/index.html`
  - File(s): `llm_race/web/templates/index.html`
  - Change:
    - The model filter input (named `model_name`) should remain but its label changes to "Model (name/slug)". The underlying filter still does a LIKE on `Model.name` for text search.
    - Add a new filter `<select>` for "AI Lab" that queries distinct `Model.ai_lab` values (populated from server).
    - The "Model" column in the benchmark table should show both `b.model_name` and a small `<code>b.model_slug</code>` below it.
  - Acceptance criteria: Index page filters work. Model column shows slug under the name.

- [ ] Step 9.5: Update `llm_race/web/templates/compare.html`
  - File(s): `llm_race/web/templates/compare.html`
  - Change:
    - In the comparison table headers, show the slug (`run.model_slug`) alongside the model name.
    - In the `<details>` sections, show `ai_lab` and `quantization` from the run.
  - Acceptance criteria: Compare view shows slug information.

- [ ] Step 9.6: Update `llm_race/web/templates/run_detail.html`
  - File(s): `llm_race/web/templates/run_detail.html`
  - Change:
    - The `<h1>` should show the slug as the title.
    - The `<div class="run-meta">` should show `model_slug` instead of or alongside `model_name`.
  - Acceptance criteria: Run detail page shows slug prominently.

- [ ] Step 9.7: Update `llm_race/web/templates/timeseries.html`
  - File(s): `llm_race/web/templates/timeseries.html`
  - Change:
    - The model filter dropdown should show slugs.
    - The `model_options` passed from the server should now be slugs instead of names (updated in Step 9.1).
  - Acceptance criteria: Timeseries model filter shows slugs.

---

## Phase 10: Update queries

- [ ] Step 10.1: Update `list_models()` in `llm_race/db/queries.py`
  - File(s): `llm_race/db/queries.py`
  - Change:
    - Add `slug`, `ai_lab`, `extra` to the SELECT clause.
    - Remove `version` from SELECT.
    - Update the `group_by` clause to include the new columns instead of `version`.
    - Update the `search` filter to also match against `Model.slug` and `Model.ai_lab`: `Model.slug.ilike(f"%{search}%") | Model.name.ilike(f"%{search}%") | Model.ai_lab.ilike(f"%{search}%")`.
    - Update the `ModelSummary` constructor calls to pass the new fields.
    - Add an optional `ai_lab: str | None = None` parameter for filtering by AI lab (exact match on `Model.ai_lab`).
  - Acceptance criteria: `list_models(session)` returns models with slug and ai_lab populated. Search by slug works.

- [ ] Step 10.2: Update benchmark queries in `llm_race/db/queries.py`
  - File(s): `llm_race/db/queries.py`
  - Change:
    - In `_benchmark_to_summary()` and `_benchmark_to_detail()`: add `model_slug=b.model.slug if b.model else ""` and `ai_lab=b.model.ai_lab if b.model else ""`.
    - In `_row_to_group_summary()`: add `model_slug` and `ai_lab` to the constructor call. Add `Model.slug`, `Model.ai_lab` to the GROUP BY SELECT clause.
    - In `list_benchmarks()`: add filter support for `filters.slug` (exact match on `Model.slug`) and `filters.ai_lab` (exact match on `Model.ai_lab`).
    - In `list_benchmark_groups()`: same — add filter support for `filters.slug` and `filters.ai_lab`.
    - In `timeseries()` and internal helpers: update filter by model to also search by slug: `(Model.slug.ilike(f"%{model}%")) | (Model.name.ilike(f"%{model}%"))` when a model filter string is provided.
  - Acceptance criteria: Queries compile and return data with the new fields. Filtering by slug works.

---

## Phase 11: Update tests

- [ ] Step 11.1: Add tests for the slug utility module
  - File(s): `tests/test_slug.py` (new file)
  - Change: Write pytest tests for `build_slug`, `parse_slug`, `validate_slug`:
    - `test_build_slug_basic`: `build_slug("Qwen", "Qwen3-8B", "none")` → `"qwen/qwen3-8b/none"`.
    - `test_build_slug_with_extra`: `build_slug("google", "Gemma-4-26B", "none", "agent-bench")` → `"google/gemma-4-26b/none/agent-bench"`.
    - `test_build_slug_special_chars`: `build_slug("AI Lab!", "Model@2.0", "FP 8")` → `"ai-lab/model-2-0/fp-8"`.
    - `test_build_slug_empty_raises`: Empty ai_lab, name, or quantization raises ValueError.
    - `test_parse_slug_3_parts`: `parse_slug("qwen/qwen3-8b/none")` returns dict with extra=None.
    - `test_parse_slug_4_parts`: `parse_slug("a/b/c/d")` returns dict with extra="d".
    - `test_parse_slug_invalid`: 2 parts or 5 parts raises ValueError.
    - `test_validate_slug_valid`: Returns True.
    - `test_validate_slug_invalid`: Returns False.
  - Acceptance criteria: `python -m pytest tests/test_slug.py -v` passes.

- [ ] Step 11.2: Update `tests/test_models.py`
  - File(s): `tests/test_models.py`
  - Change:
    - In `_create_minimal_model()`: replace `name="test-model"`, `version="1.0"`, `quantization="FP8"` with `slug="test-lab/test-model/none"`, `ai_lab="test-lab"`, `name="test-model"`, `quantization="none"`. Remove `version`.
    - In `test_create_model()`: update assertions to check new fields (`slug`, `ai_lab`, `extra`) and remove `version` assertions.
    - In `test_model_unique_constraint()`: change to test duplicate `slug` instead of duplicate `(name, version, quantization, provider_name)`.
    - Remove any `version` references from other test assertions.
    - The `Model` constructor calls across the file must include `slug` and `ai_lab`.
  - Acceptance criteria: `python -m pytest tests/test_models.py -v` passes.

- [ ] Step 11.3: Update `tests/test_db_saver.py`
  - File(s): `tests/test_db_saver.py`
  - Change:
    - In `test_save_single_scenario()`: replace `model_name="test-model"` with `model_slug="test-lab/test-model/none"`.
    - In `test_save_multiple_scenarios()`: same change.
    - In `test_find_or_create_model()`: update to test find-or-create by slug. Create two save calls with the same slug, verify only one Model row.
    - In other saver tests: replace `model_name=` with `model_slug=`.
  - Acceptance criteria: `python -m pytest tests/test_db_saver.py -v` passes.

- [ ] Step 11.4: Update `tests/test_queries.py`
  - File(s): `tests/test_queries.py`
  - Change:
    - In the `query_session` fixture:
      - Update Model creation: add `slug`, `ai_lab`, remove `version`.
        - `model_vllm`: `slug="meta-llama/llama-3.1-8b/fp8"`, `ai_lab="meta-llama"`, `name="meta-llama/Llama-3.1-8B"`, `quantization="fp8"`.
        - `model_openai`: `slug="openai/gpt-4o-mini/none"`, `ai_lab="openai"`, `name="gpt-4o-mini"`, `quantization="none"`.
    - In `create_model()` helper: update signature to include `slug`, `ai_lab`, `extra`; remove `version`.
    - In `test_filter_by_model()`: test filtering by slug pattern (LIKE match on slug).
    - In `test_multiple_filters()`: add test for `filters.ai_lab`.
    - In `TestTimeseries`: update model filter tests to use slug patterns.
  - Acceptance criteria: `python -m pytest tests/test_queries.py -v` passes.

- [ ] Step 11.5: Update `tests/test_presets.py`
  - File(s): `tests/test_presets.py`
  - Change:
    - In `test_load_preset_known_key()`: check for `preset["slug"]` instead of `preset["model"]`.
    - In `test_list_presets_each_has_required_fields()`: update required fields to `("key", "name", "provider", "slug", "ai_lab", "model_api_name", "quantization")`.
    - In `test_all_models_are_string()`: rename to `test_all_slugs_are_string()` and check `preset["slug"]`.
    - In `test_cli_list_presets_output()`: update assertion to check for slug strings.
    - Update import of `list_presets` if needed.
  - Acceptance criteria: `python -m pytest tests/test_presets.py -v` passes.

- [ ] Step 11.6: Update `tests/test_providers.py`
  - File(s): `tests/test_providers.py`
  - Change: No structural changes needed (providers don't care about slugs). But verify tests still pass — the provider tests use hardcoded model strings like `"test-model"` and those remain valid as API model names.
  - Acceptance criteria: `python -m pytest tests/test_providers.py -v` passes (may need minor test expectation updates if any test references Model ORM).

- [ ] Step 11.7: Update `tests/test_web.py`
  - File(s): `tests/test_web.py`
  - Change: If any integration tests create models directly, update to use the new fields (`slug`, `ai_lab`). The web tests may need updating to reflect new template content.
  - Acceptance criteria: `python -m pytest tests/test_web.py -v` passes.

---

## Phase 12: Integration verification

- [ ] Step 12.1: Delete old database and run a full benchmark
  - File(s): N/A (manual action)
  - Change: 
    - Run `rm -f llm_race/data/benchmarks.db` to remove the old schema.
    - Run `python -m llm_race.bench.cli run --slug qwen/qwen3-8b/none --no-db` (dry run, no DB save). Verify the benchmark runs and the CLI accepts the new slug argument.
    - Run `python -m llm_race.bench.cli run --slug qwen/qwen3-8b/none` (with DB save). Verify the benchmark completes and data is persisted.
    - Start the web server with `python -m llm_race.web` and verify the new model appears with its slug in `/models`, `/`, and `/timeseries`.
  - Acceptance criteria: Full pipeline works end-to-end: CLI → runner → DB → web viewer.

- [ ] Step 12.2: Run the full test suite
  - File(s): N/A
  - Change: Execute `python -m pytest tests/ -v` and ensure all tests pass.
  - Acceptance criteria: Zero test failures.
