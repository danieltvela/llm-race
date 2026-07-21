# Add mini-SWE-agent (SWE-bench) benchmark type

## Context
- Origin: direct user instruction
- Summary: Extend llm-race to support different benchmark types beyond the current speed benchmarks. The first new benchmark type is mini-SWE-agent (https://github.com/swe-agent/mini-swe-agent), which evaluates coding ability via the SWE-bench dataset. The CLI must generate a self-contained launch script that installs mini-SWE-agent if needed, runs the benchmark, and imports results back into the database.
- Proposed branch: N/A (direct instruction, no Gitea issue)
- Base branch: N/A
- Assumptions made:
  - Benchmark results are stored in the existing `benchmarks` table (adding `benchmark_type` + swebench-specific columns). Non-relevant columns remain NULL.
  - Execution is launch-script-only (no inline execution) because mini-SWE-agent takes hours and requires Docker.
  - The model slug (e.g. `openai/gpt-4o/none`) is reused to derive the litellm model name for mini-SWE-agent: `{ai_lab}/{name}` (e.g. `openai/gpt-4o`).
  - The `--base-url` flag is reused to set a custom API base URL for the model (e.g. `http://localhost:8000/v1` for vLLM).
  - Docker must be available on the machine running the launch script (documented but not enforced).

---

## Phase 1: Database schema — add benchmark_type and swebench columns

- [x] Step 1.1: Add `benchmark_type` column and swebench-specific columns to the `Benchmark` ORM model
  - File(s): `llm_race/db/models.py`
  - Change:
    1. After line 110 (`workload_profile`), add:
       ```python
       benchmark_type: Mapped[str] = mapped_column(String(50), nullable=False, default="speed")
       ```
    2. After line 139 (`pp_p99`), add these new optional columns:
       ```python
       # SWE-bench specific metrics
       resolved_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
       total_instances: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
       resolve_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
       avg_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
       avg_steps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
       avg_wall_time_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
       swebench_subset: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
       swebench_split: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
       swebench_model_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
       ```
  - Acceptance criteria: `python -c "from llm_race.db.models import init_db; init_db()"` runs without error and the new columns exist in the SQLite database. Existing rows have `benchmark_type = 'speed'` and NULL in the new columns.

- [x] Step 1.2: Add `benchmark_type` to dataclass types
  - File(s): `llm_race/db/types.py`
  - Change:
    1. In `BenchmarkGroupSummary` (after `workload_profile`), add:
       ```python
       benchmark_type: str
       resolve_rate: float | None
       total_instances: int | None
       swebench_subset: str | None
       swebench_split: str | None
       ```
    2. In `BenchmarkSummary`, add:
       ```python
       benchmark_type: str
       ```
    3. In `BenchmarkFilters`, add:
       ```python
       benchmark_type: str | None = None
       ```
  - Acceptance criteria: The file imports cleanly with `python -c "from llm_race.db.types import BenchmarkGroupSummary, BenchmarkSummary, BenchmarkFilters"`.

---

## Phase 2: CLI — benchmark-type flag and swebench arguments

- [x] Step 2.1: Add `--benchmark-type` argument and swebench-specific args to the `run` subcommand
  - File(s): `llm_race/bench/cli.py`
  - Change:
    1. After line 41 (`--base-url`), add:
       ```python
       run_parser.add_argument(
           "--benchmark-type",
           choices=["speed", "swebench"],
           default="speed",
           help="Benchmark type to run [default: %(default)s]",
       )
       ```
    2. After line 127 (`--launch-script`), add a swebench argument group:
       ```python
       swebench_group = run_parser.add_argument_group("SWE-bench options")
       swebench_group.add_argument("--swebench-subset", default="lite",
           help="SWE-bench subset (lite, verified, full) or dataset path [default: lite]")
       swebench_group.add_argument("--swebench-split", default="dev",
           help="Dataset split [default: dev]")
       swebench_group.add_argument("--swebench-workers", type=int, default=1,
           help="Number of parallel workers [default: 1]")
       swebench_group.add_argument("--swebench-instances", default=None,
           help="Slice specification (e.g. '0:5' for first 5 instances) or 'all'")
       swebench_group.add_argument("--swebench-environment", default="docker",
           choices=["docker", "singularity", "local"],
           help="Environment type [default: docker]")
       ```
  - Acceptance criteria: `python -m llm_race run --help` shows the new `--benchmark-type` option and the SWE-bench options group.

- [x] Step 2.2: Add `import` subcommand for importing swebench results back into the DB
  - File(s): `llm_race/bench/cli.py`
  - Change:
    1. After line 33 (`subparsers.add_parser("run", ...)`), add:
       ```python
       import_parser = subparsers.add_parser("import", help="Import benchmark results into the database")
       import_parser.add_argument("--run-id", required=True, help="UUID of the benchmark run to update")
       import_parser.add_argument("--output-dir", required=True, help="Directory containing mini-swe-agent output (preds.json)")
       import_parser.add_argument("--db", default=str(DB_PATH), help="Path to the database file")
       ```
    2. In the `main()` function, after the existing `if args.list_presets:` block (line 133), add an `if args.command == "import":` branch that calls `import_swebench_results(args.run_id, args.output_dir, args.db)` (the function created in Phase 4).
  - Acceptance criteria: `python -m llm_race import --help` shows the import subcommand with all arguments.

- [x] Step 2.3: Dispatch swebench benchmark type in the `run` command flow
  - File(s): `llm_race/bench/cli.py`
  - Change:
    - In the `main()` function, after all argument resolution (around line 230, before the `launch_script_content` block), add:
      ```python
      if args.benchmark_type == "swebench":
          from llm_race.bench.swebench_runner import generate_swebench_launch_script
          launch_script_content = generate_swebench_launch_script(
              model_slug=model_slug,
              base_url=args.base_url if args.base_url != DEFAULT_BASE_URL else None,
              subset=args.swebench_subset,
              split=args.swebench_split,
              workers=args.swebench_workers,
              instances=args.swebench_instances,
              environment=args.swebench_environment,
              run_id=run_id,
              db_path=str(DB_PATH),
          )
          # Save the launch script to a file for user convenience
          script_path = Path(f"launch_swebench_{run_id[:8]}.sh")
          script_path.write_text(launch_script_content)
          script_path.chmod(0o755)
          logger.info("Launch script written to %s", script_path)
          # Fall through to save the pending benchmark run to DB
          # (the existing run_benchmarks call will be replaced by a direct DB save)
          # ... (see next step for the swebench-specific DB logic)
      ```
    - The swebench branch should NOT call `run_benchmarks()` (the speed runner). Instead, it should directly save a placeholder benchmark to the DB with status="running" and the launch script attached.
  - Acceptance criteria: Running `python -m llm_race run --benchmark-type swebench --slug openai/gpt-4o/none --swebench-subset lite --swebench-instances 0:2` generates a launch script file and prints its path. No speed benchmarks are executed.

- [x] Step 2.4: Save a "pending" swebench Benchmark row to the DB when benchmark-type is swebench
  - File(s): `llm_race/bench/cli.py`
  - Change:
    - In the swebench branch (from step 2.3), after generating the launch script, directly call the DB to save a placeholder Benchmark row:
      ```python
      if not args.no_db and run_id is not None:
          from llm_race.db.models import init_db, Model, Machine, Benchmark
          engine, session_factory = init_db()
          with session_factory() as session:
              # Find or create Model (same logic as saver.py)
              parsed = parse_slug(model_slug)
              model_record = session.execute(
                  select(Model).where(Model.slug == model_slug)
              ).scalar_one_or_none()
              if model_record is None:
                  model_record = Model(
                      slug=model_slug,
                      ai_lab=parsed["ai_lab"],
                      name=parsed["name"],
                      quantization=parsed["quantization"],
                      extra=parsed.get("extra"),
                      provider_name=args.provider or "litellm",
                  )
                  session.add(model_record)
                  session.flush()
              # Find or create Machine
              machine_record = session.execute(
                  select(Machine).where(Machine.hostname == system_info["hostname"])
              ).scalar_one_or_none()
              if machine_record is None:
                  machine_kwargs = {k: system_info.get(k) for k in (
                      "hostname", "cpu", "gpu", "gpu_count", "ram_gb",
                      "os", "os_version", "driver_version", "python_version",
                  )}
                  machine_record = Machine(**machine_kwargs)
                  session.add(machine_record)
                  session.flush()
              # Create pending Benchmark row
              swebench_model_name = f"{parsed['ai_lab']}/{parsed['name']}"
              benchmark = Benchmark(
                  run_id=run_id,
                  model_id=model_record.id,
                  machine_id=machine_record.id,
                  benchmark_type="swebench",
                  workload_profile="swebench",
                  prompt_size="n/a",
                  concurrency=1,
                  max_tokens=0,
                  temperature=0.0,
                  top_p=1.0,
                  started_at=datetime.utcnow(),
                  status="running",
                  notes=args.notes,
                  launch_script=launch_script_content,
                  swebench_subset=args.swebench_subset,
                  swebench_split=args.swebench_split,
                  swebench_model_name=swebench_model_name,
              )
              session.add(benchmark)
              session.commit()
              logger.info("Pending swebench run saved to DB with run_id=%s", run_id)
      ```
  - Acceptance criteria: After running the swebench CLI command, `sqlite3 data/benchmarks.db "SELECT benchmark_type, status, swebench_subset FROM benchmarks WHERE benchmark_type='swebench'"` shows a row with `swebench|running|lite`.

---

## Phase 3: Launch script generation

- [x] Step 3.1: Create `bench/swebench_runner.py` — launch script generator
  - File(s): `llm_race/bench/swebench_runner.py` (new file)
  - Change: Create a function `generate_swebench_launch_script(...)` that returns a bash script string. The script must:
    1. Shebang `#!/usr/bin/env bash` with `set -euo pipefail`
    2. Check if `mini-swe-agent` is installed via `python -c "import minisweagent" 2>/dev/null`. If not, run `pip install mini-swe-agent` (use `pip3` fallback if `pip` not found).
    3. Print a header with the run_id and model info.
    4. Build the `mini-extra swebench` command with these arguments:
       - `--model <swebench_model_name>` (derived from slug: `{ai_lab}/{name}`)
       - `--subset <subset>` (from `--swebench-subset`, default `lite`)
       - `--split <split>` (from `--swebench-split`, default `dev`)
       - `--workers <workers>` (from `--swebench-workers`, default 1)
       - `--output <output_dir>` (auto-generated: `/tmp/swebench_<run_id[:8]>`)
       - If `--swebench-instances` is set and != "all": `--slice <instances>`
       - If `--swebench-environment` != "docker": `--environment-class <env>`
       - If `base_url` is provided: `--config model.model_kwargs.api_base=<base_url>`
    5. After mini-swe-agent completes, run the import command:
       ```bash
       python -m llm_race import --run-id <run_id> --output-dir <output_dir>
       ```
    6. Print a summary: "Benchmark complete. Results imported with run_id: <run_id>"
    7. Print a URL to view results: "View at: http://127.0.0.1:8080/run/<run_id>"
  - Function signature:
    ```python
    def generate_swebench_launch_script(
        model_slug: str,
        base_url: str | None,
        subset: str,
        split: str,
        workers: int,
        instances: str | None,
        environment: str,
        run_id: str,
        db_path: str,
    ) -> str:
    ```
  - Acceptance criteria: Calling `generate_swebench_launch_script("openai/gpt-4o/none", None, "lite", "dev", 1, "0:2", "docker", str(uuid.uuid4()), "data/benchmarks.db")` returns a bash script string that contains `pip install mini-swe-agent`, `mini-extra swebench --model openai/gpt-4o --subset lite --split dev --workers 1 --slice 0:2`, and `python -m llm_race import --run-id`.

---

## Phase 4: Results import — parse swebench output and store in DB

- [x] Step 4.1: Create `bench/swebench_importer.py` — parse preds.json and trajectory files
  - File(s): `llm_race/bench/swebench_importer.py` (new file)
  - Change: Create a function `import_swebench_results(run_id, output_dir, db_path)` that:
    1. Reads `preds.json` from `output_dir` (maps instance_id → {model_name_or_path, instance_id, model_patch}).
    2. Counts total instances (number of keys in preds.json).
    3. Counts resolved instances (those with a non-empty `model_patch` field).
    4. Computes `resolve_rate = resolved_count / total_instances * 100` (as a percentage 0-100).
    5. (Optional, if trajectory files exist) Reads each `{instance_id}/{instance_id}.traj.json` to extract `info.exit_status`, cost info (if available), and step count. Tries `n_calls` or `steps` field for step count.
    6. Opens the DB, finds the Benchmark row with matching `run_id` and `benchmark_type = "swebench"`.
    7. Updates the Benchmark row:
       - `resolved_count`, `total_instances`, `resolve_rate`
       - `avg_cost_usd` (mean of per-instance costs, or None)
       - `avg_steps` (mean of per-instance steps, or None)
       - `avg_wall_time_s` (mean of per-instance wall times, or None)
       - `status = "success"` (or "partial" if some failed)
       - `completed_at = datetime.utcnow()`
    8. (Optional) Populates per-instance data in the `results` table, reusing existing columns where possible (e.g., `status`, `error_message`).
    9. Commits the transaction.
  - Function signature:
    ```python
    def import_swebench_results(
        run_id: str,
        output_dir: str | Path,
        db_path: str | Path = DB_PATH,
    ) -> bool:
    ```
    Returns True on success, False on failure.
  - Acceptance criteria:
    - Unit test: `test_import_swebench_results` with a mock `preds.json` containing 3 instances (2 resolved, 1 failed). Verifies Benchmark row is updated with `resolved_count=2`, `total_instances=3`, `resolve_rate≈66.67`, `status="partial"`.
    - Integration test (manual): After running a real mini-swe-agent benchmark on 2 instances, `python -m llm_race import --run-id <id> --output-dir <dir>` updates the DB correctly.

- [x] Step 4.2: Wire the `import` subcommand in CLI to call `import_swebench_results`
  - File(s): `llm_race/bench/cli.py`
  - Change: In the `if args.command == "import":` branch (added in step 2.2), call:
    ```python
    from llm_race.bench.swebench_importer import import_swebench_results
    success = import_swebench_results(args.run_id, args.output_dir, args.db)
    if success:
        print(f"Results imported successfully for run {args.run_id}")
    else:
        print(f"Failed to import results for run {args.run_id}", file=sys.stderr)
        sys.exit(1)
    ```
  - Acceptance criteria: `python -m llm_race import --run-id <valid-id> --output-dir /tmp/test_swebench` works end-to-end.

---

## Phase 5: Web viewer — show benchmark type and swebench metrics

- [x] Step 5.1: Update `get_model_benchmarks()` query to include `benchmark_type` and swebench columns
  - File(s): `llm_race/db/queries.py`
  - Change:
    1. In the `get_model_benchmarks()` function (around line 681), add to the `select()` call:
       ```python
       Benchmark.benchmark_type,
       func.max(Benchmark.resolve_rate).label("resolve_rate"),
       func.max(Benchmark.total_instances).label("total_instances"),
       func.min(Benchmark.swebench_subset).label("swebench_subset"),
       func.min(Benchmark.swebench_split).label("swebench_split"),
       ```
    2. Add these columns to the `group_by()` clause (line 704-712).
    3. Update `_row_to_group_summary()` (helper function near line 160-195) to populate the new `BenchmarkGroupSummary` fields from the query row.
    4. Add `benchmark_type` to the `_SORT_WHITELIST` set (near line 410-430) so users can sort by it.
  - Acceptance criteria: The `model_benchmarks.html` page renders without error when there are swebench benchmarks in the DB. The template receives `benchmark_type`, `resolve_rate`, `total_instances`, `swebench_subset`, and `swebench_split` fields.

- [x] Step 5.2: Update `model_benchmarks.html` template to show benchmark type and swebench metrics
  - File(s): `llm_race/web/templates/model_benchmarks.html`
  - Change:
    1. After the "Workload" column (line 35), add a new table header `<th>Type</th>`.
    2. In each row (line 56), add `<td>{{ b.benchmark_type }}</td>` after the workload_profile cell.
    3. For swebench rows (`b.benchmark_type == 'swebench'`), conditionally replace the PP, TGS, TTFT columns with swebench-specific metrics:
       - Instead of PP (tok/s): show `{{ "%.1f%%"|format(b.resolve_rate) if b.resolve_rate else '-' }}`
       - Instead of TGS (tok/s): show `{{ b.total_instances if b.total_instances else '-' }}` (labeled "Instances")
       - Instead of TTFT (ms): show `{{ b.swebench_subset or '-' }}` (labeled "Subset")
    4. The column headers should also change conditionally, OR add separate columns for swebench:
       - Approach: add 3 new columns after the existing metrics columns, shown only when any row has `benchmark_type == 'swebench'`. Use a Jinja2 check at the top: `{% set has_swebench = benchmarks | selectattr('benchmark_type', 'equalto', 'swebench') | list | length > 0 %}`.
       - New columns: Resolve Rate, Instances, Subset.
    5. Keep existing speed columns (PP, TGS, TTFT) but show `-` for swebench rows (they're naturally None).
  - Acceptance criteria: The model detail page shows both speed and swebench benchmark runs in the same table. Swebench rows show resolve rate, instance count, and subset. Speed rows continue to show PP, TGS, TTFT.

- [x] Step 5.3: Update `run_detail.html` template for swebench runs
  - File(s): `llm_race/web/templates/run_detail.html`
  - Change:
    1. At the top of the content block, check if the first benchmark has `benchmark_type == 'swebench'`.
    2. If yes: render a swebench-specific detail view instead of the speed metrics table.
       - Show: Run ID, Model, Subset, Split, Environment (from launch_script or new column), Resolved/Total instances, Resolve rate %, Avg cost, Avg steps, Avg wall time.
       - If per-instance data is stored in the `results` table, show a table of instances with: Instance ID, Status, Steps, Cost, Wall Time.
    3. If no (speed benchmark): keep the existing speed metrics table unchanged.
    4. The launch script section (lines 34-38) should always show if present.
  - Acceptance criteria: Visiting `/run/<swebench-run-id>` shows swebench-specific metrics (resolve rate, instances, subset) instead of speed metrics (concurrency, prompt size, PP, TGS, TTFT).

- [x] Step 5.4: Update `handle_model_benchmarks()` in server.py to pass benchmark_type info
  - File(s): `llm_race/web/server.py`
  - Change: No code changes needed in the handler itself, but verify that the `BenchmarkGroupSummary` objects from `get_model_benchmarks()` now contain the new fields (`benchmark_type`, `resolve_rate`, etc.) and that the template can access them as `b.benchmark_type`, etc.
  - Acceptance criteria: The model detail page renders without errors and shows the new data.

---

## Phase 6: Query layer — update list_benchmark_groups and related queries

- [x] Step 6.1: Update `list_benchmark_groups()` to include `benchmark_type` filtering
  - File(s): `llm_race/db/queries.py`
  - Change:
    1. In `list_benchmark_groups()` (around line 400-530), add `benchmark_type` to the `select()` and `group_by()` clauses.
    2. Add `benchmark_type` filter support in the `BenchmarkFilters` handling: if `filters.benchmark_type` is set, add `.where(Benchmark.benchmark_type == filters.benchmark_type)`.
    3. Update `_row_to_group_summary()` (the one used by list_benchmark_groups, around line 160-195) to populate the new fields.
  - Acceptance criteria: The index page (`/`) can filter by `?benchmark_type=swebench` and shows only swebench benchmarks.

- [x] Step 6.2: Update `get_run_benchmarks()` for swebench detail
  - File(s): `llm_race/db/queries.py`
  - Change:
    1. In `get_run_benchmarks()` (around line 540-600), ensure the query includes `Benchmark.benchmark_type` and all new swebench columns.
    2. Update `_row_to_benchmark_detail()` (around line 480-520) to include the new fields.
  - Acceptance criteria: The run detail page receives all swebench-specific columns in the benchmark objects.

---

## Phase 7: Testing

- [x] Step 7.1: Unit tests for launch script generation
  - File(s): `tests/test_swebench_runner.py` (new file)
  - Change: Test `generate_swebench_launch_script()`:
    1. Verify the generated script contains `pip install mini-swe-agent`.
    2. Verify it contains the correct `mini-extra swebench` command with expected arguments.
    3. Verify it contains the `python -m llm_race import` command.
    4. Verify the script is valid bash (shellcheck or manual review of syntax).
    5. Verify the script handles optional parameters (base_url, instances slice).
  - Acceptance criteria: `python -m pytest tests/test_swebench_runner.py -v` passes.

- [x] Step 7.2: Unit tests for swebench results import
  - File(s): `tests/test_swebench_importer.py` (new file)
  - Change: Test `import_swebench_results()`:
    1. Create a temporary directory with a mock `preds.json` (2 resolved, 1 unresolved).
    2. Create a temporary SQLite DB with a pending Benchmark row.
    3. Call `import_swebench_results()` and verify the Benchmark row is updated correctly.
    4. Test edge cases: empty preds.json (0 instances), all resolved, all failed.
    5. Test that invalid run_id returns False.
  - Acceptance criteria: `python -m pytest tests/test_swebench_importer.py -v` passes.

- [x] Step 7.3: Unit tests for CLI swebench arguments
  - File(s): `tests/test_cli.py` (new file)
  - Change: Test argparse parsing:
    1. `--benchmark-type swebench` sets the correct value.
    2. `--swebench-subset verified --swebench-split test --swebench-workers 4` are parsed correctly.
    3. Default values are correct.
  - Acceptance criteria: `python -m pytest tests/test_cli.py -v` passes.

- [x] Step 7.4: Unit tests for DB schema changes
  - File(s): `tests/test_models.py`
  - Change: Add tests:
    1. Create a Benchmark with `benchmark_type="swebench"` and verify it persists and retrieves correctly.
    2. Verify that existing speed benchmarks still work (backward compatibility).
    3. Verify swebench-specific columns accept NULL.
  - Acceptance criteria: `python -m pytest tests/test_models.py -v` passes.

- [x] Step 7.5: Unit tests for web viewer swebench rendering
  - File(s): `tests/test_web.py`
  - Change: Add tests:
    1. Verify `/model/<id>` page renders correctly when the model has swebench benchmarks (mock the DB).
    2. Verify `/run/<swebench_run_id>` page renders swebench-specific content instead of speed metrics.
    3. Verify the index page can filter by `benchmark_type`.
  - Acceptance criteria: `python -m pytest tests/test_web.py -v` passes.

---

## Phase 8: Documentation and final verification

- [x] Step 8.1: Update AGENTS.md with swebench benchmark instructions
  - File(s): `AGENTS.md`
  - Change: Add a section under "Benchmark runner conventions" explaining the swebench benchmark type, required dependencies (Docker, mini-swe-agent), and example commands.
  - Acceptance criteria: A new developer can read AGENTS.md and understand how to run a swebench benchmark.

- [x] Step 8.2: End-to-end manual verification
  - Manual steps:
    1. Run `python -m llm_race run --benchmark-type swebench --slug openai/gpt-4o/none --swebench-subset lite --swebench-instances 0:2` and verify:
       - A launch script file is created and is executable.
       - A pending Benchmark row with `benchmark_type="swebench"` and `status="running"` exists in the DB.
    2. Execute the launch script and verify:
       - mini-swe-agent is installed (or already present).
       - The swebench evaluation runs on 2 instances.
       - The import command runs and updates the DB (status becomes "success" or "partial").
    3. Start the web viewer: `python -m llm_race.web` and verify:
       - The model detail page (`/model/<id>`) shows the swebench run with resolve rate and instance count.
       - The run detail page (`/run/<id>`) shows swebench-specific metrics.
    4. Run a normal speed benchmark to verify backward compatibility:
       - `python -m llm_race run --slug openai/gpt-4o/none --concurrency 1 --prompt-lengths 64` works unchanged.
  - Acceptance criteria: All manual steps pass without errors.

- [x] Step 8.3: Run all existing tests to verify no regressions
  - Manual step: `python -m pytest tests/ -v`
  - Acceptance criteria: All existing tests pass (no regressions from schema/type changes).
