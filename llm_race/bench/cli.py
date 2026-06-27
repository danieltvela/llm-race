"""CLI entry point for the benchmark runner."""

import argparse
import asyncio

from llm_race.bench.runner import run_benchmarks
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

    args = parser.parse_args()

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
            concurrency=args.concurrency,
            prompt_lengths=args.prompt_lengths,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            output=args.output,
        )
    )


if __name__ == "__main__":
    main()
