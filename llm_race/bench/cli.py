"""CLI entry point for the benchmark runner."""

import argparse
import asyncio
import logging
import uuid

from llm_race.bench.runner import run_benchmarks
from llm_race.bench.workloads import WORKLOAD_REGISTRY, get_workload
from llm_race.config import (
    DEFAULT_BASE_URL,
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MEASURED_ITERATIONS,
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LENGTHS,
    DEFAULT_PROVIDER,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_WARMUP_ITERATIONS,
    create_provider,
)
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
    run_parser.add_argument("--model", default=DEFAULT_MODEL)
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

    args = parser.parse_args()
    logger = logging.getLogger(__name__)

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

    # Note: --force-detect is accepted but currently a no-op.
    # System info is collected fresh each run; caching will be added
    # when needed to avoid repeated nvidia-smi calls.

    asyncio.run(
        run_benchmarks(
            provider=provider,
            model=args.model,
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
        )
    )


if __name__ == "__main__":
    main()
