"""CLI entry point for the benchmark runner."""

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from llm_race.bench.runner import run_benchmarks
from llm_race.bench.workloads import WORKLOAD_REGISTRY, get_workload
from llm_race.config import (
    DB_PATH,
    DEFAULT_BASE_URL,
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MEASURED_ITERATIONS,
    DEFAULT_MODEL_SLUG,
    DEFAULT_PROVIDER,
    DEFAULT_PROMPT_LENGTHS,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_WARMUP_ITERATIONS,
    create_provider,
)
from llm_race.db.models import Benchmark, Machine, Model, init_db
from llm_race.utils.slug import build_slug, parse_slug, validate_slug
from llm_race.utils.system import collect_system_info


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Race — benchmark runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a benchmark suite")
    run_parser.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        help="Provider type (vllm, openai, anthropic, ollama, …) [default: %(default)s]",
    )
    run_parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run_parser.add_argument(
        "--benchmark-type",
        choices=["speed", "swebench"],
        default="speed",
        help="Benchmark type to run [default: %(default)s]",
    )

    # Model identification: --slug or individual flags
    model_group = run_parser.add_mutually_exclusive_group()
    model_group.add_argument(
        "--slug",
        default=None,
        help="Model slug (e.g. qwen/qwen3-8b/none)",
    )
    model_group.add_argument(
        "--ai-lab",
        default=None,
        help="AI lab / organization (e.g. qwen, meta, google). Implies --name and --quantization.",
    )
    run_parser.add_argument(
        "--name",
        default=None,
        help="Model name (e.g. qwen3-8b, llama-3.2-3b). Used with --ai-lab.",
    )
    run_parser.add_argument(
        "--quantization",
        default=None,
        help="Quantization type (e.g. fp8, int8, none). Used with --ai-lab.",
    )
    run_parser.add_argument(
        "--extra",
        default=None,
        help="Optional extra modifier (e.g. agent-bench). Used with --ai-lab.",
    )

    run_parser.add_argument(
        "--concurrency", type=int, nargs="+", default=DEFAULT_CONCURRENCY
    )
    run_parser.add_argument(
        "--prompt-lengths", type=int, nargs="+", default=DEFAULT_PROMPT_LENGTHS
    )
    run_parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    run_parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    run_parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    run_parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT)
    run_parser.add_argument("-o", "--output", default=None, help="CSV output path")
    run_parser.add_argument(
        "--workload",
        choices=list(WORKLOAD_REGISTRY.keys()),
        default=None,
        help="Workload profile (overrides --concurrency and --prompt-lengths). Choices: %(choices)s",
    )
    run_parser.add_argument(
        "--warmup-iterations",
        type=int,
        default=DEFAULT_WARMUP_ITERATIONS,
        help="Warmup iterations per scenario (default: %(default)s)",
    )
    run_parser.add_argument(
        "--measured-iterations",
        type=int,
        default=DEFAULT_MEASURED_ITERATIONS,
        help="Measured iterations per scenario (default: %(default)s)",
    )
    run_parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip saving results to the database",
    )
    run_parser.add_argument(
        "--force-detect",
        action="store_true",
        help="Re-collect machine info even if cached (not yet cached)",
    )
    run_parser.add_argument(
        "--preset",
        default=None,
        help="Load preset config (use --list-presets to see available)",
    )
    run_parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List all available presets and exit",
    )
    run_parser.add_argument(
        "--notes",
        default="",
        help="Free-form notes attached to the benchmark run",
    )
    run_parser.add_argument(
        "--launch-script",
        default=None,
        help="Path to a launch script file to store with the benchmark",
    )

    # SWE-bench specific options
    swebench_group = run_parser.add_argument_group("SWE-bench options")
    swebench_group.add_argument(
        "--swebench-subset",
        default="lite",
        help="SWE-bench subset (lite, verified, full) or dataset path [default: lite]",
    )
    swebench_group.add_argument(
        "--swebench-split",
        default="dev",
        help="Dataset split [default: dev]",
    )
    swebench_group.add_argument(
        "--swebench-workers",
        type=int,
        default=1,
        help="Number of parallel workers [default: 1]",
    )
    swebench_group.add_argument(
        "--swebench-instances",
        default=None,
        help="Slice specification (e.g. '0:5' for first 5 instances) or 'all'",
    )
    swebench_group.add_argument(
        "--swebench-environment",
        default="docker",
        choices=["docker", "singularity", "local"],
        help="Environment type [default: docker]",
    )

    # Import subcommand
    import_parser = subparsers.add_parser("import", help="Import benchmark results into the database")
    import_parser.add_argument("--run-id", required=True, help="UUID of the benchmark run to update")
    import_parser.add_argument("--output-dir", required=True, help="Directory containing mini-swe-agent output (preds.json)")
    import_parser.add_argument("--db", default=str(DB_PATH), help="Path to the database file")

    args = parser.parse_args()

    # Handle import subcommand
    if args.command == "import":
        from llm_race.bench.swebench_importer import import_swebench_results
        success = import_swebench_results(args.run_id, args.output_dir, args.db)
        if success:
            print(f"Results imported successfully for run {args.run_id}")
        else:
            print(f"Failed to import results for run {args.run_id}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle --list-presets: print and exit immediately.
    if args.list_presets:
        from llm_race.config.presets import list_presets as _list_presets
        presets = _list_presets()
        for p in presets:
            print(f"{p['key']}: {p['name']} ({p['slug']})")
        return

    # Handle --preset: load and merge with explicit CLI flags.
    model_slug: str | None = None
    model_api_name: str | None = None

    if args.preset:
        try:
            from llm_race.config import list_presets as _list_all
            from llm_race.config.presets import load_preset
            preset = load_preset(args.preset)
        except KeyError:
            print(f"Error: unknown preset {args.preset!r}. Available presets:")
            for p in _list_all():
                print(f"  {p['key']}: {p['name']} ({p['slug']})")
            sys.exit(1)
        # Preset acts as defaults; explicit CLI flags override.
        def _is_default(val: str | None, default: str) -> bool:
            return val is None or val == default

        if _is_default(args.provider, DEFAULT_PROVIDER) and "provider" in preset:
            args.provider = preset["provider"]
        if not model_slug and "slug" in preset:
            model_slug = preset["slug"]
        if not model_api_name and "model_api_name" in preset:
            model_api_name = preset["model_api_name"]
        if _is_default(args.base_url, DEFAULT_BASE_URL) and "base_url" in preset:
            args.base_url = preset["base_url"]

    # Resolve model slug from --slug or individual flags
    if model_slug is None:
        if args.slug:
            model_slug = args.slug
        elif args.ai_lab or args.name or args.quantization:
            # Individual flags provided — all three are required
            if not (args.ai_lab and args.name and args.quantization):
                print("Error: --ai-lab, --name, and --quantization must all be specified together.")
                sys.exit(1)
            model_slug = build_slug(args.ai_lab, args.name, args.quantization, args.extra)
            model_api_name = args.name
        else:
            model_slug = DEFAULT_MODEL_SLUG
            model_api_name = parse_slug(model_slug)["name"]

    assert model_slug is not None, "Model slug must be resolved"

    # Validate slug
    if not validate_slug(model_slug):
        print(f"Error: invalid model slug: {model_slug!r}")
        print("Expected format: {ai_lab}/{name}/{quantization}[/extra]")
        sys.exit(1)

    # Resolve API model name from slug if not already set by preset
    if model_api_name is None:
        model_api_name = parse_slug(model_slug)["name"]

    logger = logging.getLogger(__name__)

    assert model_api_name is not None, "Model API name must be resolved"

    # ── SWE-bench benchmark type ──────────────────────────────────────
    if args.benchmark_type == "swebench":
        _handle_swebench_run(args, model_slug, logger)
        return

    # ── Speed benchmark (default) ─────────────────────────────────────
    # Resolve concurrency and prompt_lengths from workload profile if set.
    if args.workload:
        profile = get_workload(args.workload)
        logger.info("Using workload profile: %s (%s)", profile.name, profile.description)
        concurrency = profile.concurrency_levels
        prompt_lengths = profile.default_prompt_lengths
    else:
        concurrency = args.concurrency
        prompt_lengths = args.prompt_lengths

    # Pass provider-specific kwargs. For vLLM only base-url and timeout
    # are relevant; other providers will need different extras in the future.
    provider_kwargs: dict = {"timeout": args.timeout}
    if args.base_url:
        provider_kwargs["base_url"] = args.base_url

    provider = create_provider(args.provider, **provider_kwargs)

    run_id = str(uuid.uuid4())
    if args.no_db:
        system_info = None
        provider_type = None
        effective_run_id = None
    else:
        system_info = collect_system_info().to_dict()
        provider_type = args.provider
        effective_run_id = run_id

    # Read launch script content from file if provided.
    launch_script_content = ""
    if args.launch_script:
        try:
            launch_script_content = Path(args.launch_script).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Error: could not read launch script file: {exc}")
            sys.exit(1)

    asyncio.run(
        run_benchmarks(
            provider=provider,
            model_slug=model_slug,
            model_api_name=model_api_name,
            concurrency=concurrency,
            prompt_lengths=prompt_lengths,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            output=args.output,
            workload_profile=args.workload,
            warmup_iterations=args.warmup_iterations,
            measured_iterations=args.measured_iterations,
            run_id=effective_run_id,
            system_info=system_info,
            provider_type=provider_type,
            notes=args.notes,
            launch_script=launch_script_content,
        )
    )


def _handle_swebench_run(
    args: argparse.Namespace,
    model_slug: str,
    logger: logging.Logger,
) -> None:
    """Generate a launch script and save a pending SWE-bench benchmark row."""
    from llm_race.bench.swebench_runner import generate_swebench_launch_script

    run_id = str(uuid.uuid4())
    parsed = parse_slug(model_slug)
    swebench_model_name = f"{parsed['ai_lab']}/{parsed['name']}"

    # Determine base_url to pass to launch script
    base_url = args.base_url if args.base_url != DEFAULT_BASE_URL else None

    # Generate launch script
    launch_script_content = generate_swebench_launch_script(
        model_slug=model_slug,
        base_url=base_url,
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
    print(f"Launch script written to: {script_path}")

    # Save pending benchmark row to DB
    if args.no_db:
        print(f"Skipping DB save (--no-db). Run the launch script manually:")
        print(f"  bash {script_path}")
        return

    system_info = collect_system_info().to_dict()

    engine, session_factory = init_db()
    with session_factory() as session:
        # Find or create Model
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

    print(f"Pending SWE-bench run saved to DB with run_id: {run_id}")
    print(f"Execute the launch script to run the benchmark:")
    print(f"  bash {script_path}")


if __name__ == "__main__":
    main()