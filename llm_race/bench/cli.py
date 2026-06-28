"""CLI entry point for the benchmark runner."""

import argparse
import asyncio
import logging

from llm_race.bench.runner import run_benchmarks
from llm_race.bench.workloads import WORKLOAD_REGISTRY, get_workload
from llm_race.config import (
    DEFAULT_BASE_URL,
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_PROMPT_LENGTHS,
    DEFAULT_PROVIDER,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    create_provider,
)


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
        )
    )


if __name__ == "__main__":
    main()
