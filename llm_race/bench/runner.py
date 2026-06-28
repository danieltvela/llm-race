"""Benchmark orchestration for LLM Race.

The runner is provider-agnostic — it accepts any ``Provider`` subclass
and calls ``stream_complete()`` concurrently per scenario.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx

from llm_race.bench.prompts import SYSTEM_PROMPT, generate_prompt
from llm_race.config import DEFAULT_MEASURED_ITERATIONS, DEFAULT_WARMUP_ITERATIONS
from llm_race.config.base import Provider
from llm_race.utils.reporter import format_table, save_csv, save_json
from llm_race.utils.timing import compute_itl_stats, compute_latency_stats

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Per-request metrics collected after a single streaming completion."""

    request_id: int
    prompt_length: int
    concurrency_level: int
    status: str
    error_message: Optional[str] = None
    ttft: Optional[float] = None
    e2e_latency: Optional[float] = None
    inter_token_latencies: list[float] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: Optional[float] = None


@dataclass
class ScenarioResult:
    """Aggregated metrics for a (concurrency, prompt_length) pair."""

    concurrency: int
    prompt_length: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    e2e_mean: float = 0.0
    e2e_p50: float = 0.0
    e2e_p95: float = 0.0
    e2e_p99: float = 0.0
    e2e_max: float = 0.0
    ttft_mean: float = 0.0
    ttft_p50: float = 0.0
    ttft_p95: float = 0.0
    ttft_p99: float = 0.0
    throughput_rps: float = 0.0
    throughput_tps: float = 0.0
    itl_mean: float = 0.0
    itl_p50: float = 0.0
    itl_p95: float = 0.0
    wall_clock_seconds: float = 0.0


async def run_scenario(
    provider: Provider,
    model: str,
    concurrency: int,
    prompt_length: int,
    max_tokens: int,
    temperature: float,
    top_p: float,
    limits: httpx.Limits | None = None,
    warmup_iterations: int = DEFAULT_WARMUP_ITERATIONS,
    measured_iterations: int = DEFAULT_MEASURED_ITERATIONS,
) -> list[RequestMetrics]:
    """Execute warmup then measured iterations of parallel streaming requests.

    Args:
        provider: Any ``Provider`` subclass.
        model: Model identifier (e.g. ``"Qwen3.6-35B-A3B-FP8"``).
        concurrency: Number of simultaneous requests per batch.
        prompt_length: Target prompt token count.
        max_tokens: Max completion tokens per request.
        temperature: Sampling temperature.
        top_p: Nucleus sampling threshold.
        limits: Optional ``httpx.Limits`` for connection pooling.
        warmup_iterations: Number of warmup batches to run and discard.
        measured_iterations: Number of measured batches to run and collect.

    Returns:
        List of ``RequestMetrics`` from all measured batches.
    """
    prompt = generate_prompt(prompt_length)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    logger.info(
        "Starting scenario concurrency=%d prompt_length=%d warmup=%d measured=%d",
        concurrency,
        prompt_length,
        warmup_iterations,
        measured_iterations,
    )

    if measured_iterations == 0:
        logger.warning("measured_iterations is 0, returning empty results")
        return []

    async def _run_batch(client: httpx.AsyncClient) -> list[RequestMetrics]:
        coros = [
            provider.stream_complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                client=client,
            )
            for _ in range(concurrency)
        ]
        raw_results = await asyncio.gather(*coros, return_exceptions=True)

        metrics_list: list[RequestMetrics] = []
        for request_id, result in enumerate(raw_results):
            if isinstance(result, BaseException):
                metrics_list.append(
                    RequestMetrics(
                        request_id=request_id,
                        prompt_length=prompt_length,
                        concurrency_level=concurrency,
                        status="error",
                        error_message=str(result)[:200],
                    )
                )
                continue

            e2e = result.get("e2e_latency")
            completion_tokens = result.get("completion_tokens", 0)
            tokens_per_second: float | None = result.get("tokens_per_second")
            if tokens_per_second is None and e2e and e2e > 0:
                tokens_per_second = completion_tokens / e2e

            metrics = RequestMetrics(
                request_id=request_id,
                prompt_length=prompt_length,
                concurrency_level=concurrency,
                status=result.get("status", "error"),
                error_message=result.get("error_message"),
                ttft=result.get("ttft"),
                e2e_latency=e2e,
                inter_token_latencies=list(result.get("inter_token_latencies", [])),
                prompt_tokens=result.get("prompt_length", 0),
                completion_tokens=completion_tokens,
                total_tokens=result.get("prompt_length", 0) + completion_tokens,
                tokens_per_second=tokens_per_second,
            )
            metrics_list.append(metrics)

        return metrics_list

    async def _run_all(client: httpx.AsyncClient) -> list[RequestMetrics]:
        for i in range(warmup_iterations):
            batch = await _run_batch(client)
            failed = [m for m in batch if m.status == "error"]
            for m in failed:
                logger.warning("Request failed during warmup: %s", m.error_message)
            logger.info("Warmup iteration %d/%d complete", i + 1, warmup_iterations)

        all_metrics: list[RequestMetrics] = []
        for i in range(measured_iterations):
            batch = await _run_batch(client)
            for j, m in enumerate(batch):
                m.request_id = len(all_metrics) + j
            all_metrics.extend(batch)
            logger.info("Measured iteration %d/%d complete", i + 1, measured_iterations)

        return all_metrics

    if limits is not None:
        async with httpx.AsyncClient(limits=limits, timeout=provider.timeout) as client:
            metrics = await _run_all(client)
    else:
        async with httpx.AsyncClient() as client:
            metrics = await _run_all(client)

    logger.info(
        "Scenario completed concurrency=%d prompt_length=%d success=%d/%d (warmup=%d measured=%d)",
        concurrency,
        prompt_length,
        sum(1 for m in metrics if m.status == "success"),
        len(metrics),
        warmup_iterations,
        measured_iterations,
    )
    return metrics


def _build_scenario_result(
    metrics: list[RequestMetrics],
    concurrency: int,
    prompt_length: int,
    wall_clock_seconds: float,
) -> ScenarioResult:
    """Aggregate per-request metrics into a single ``ScenarioResult``."""
    success = [m for m in metrics if m.status == "success"]
    failed = [m for m in metrics if m.status == "error"]

    result = ScenarioResult(
        concurrency=concurrency,
        prompt_length=prompt_length,
        total_requests=len(metrics),
        successful_requests=len(success),
        failed_requests=len(failed),
        wall_clock_seconds=wall_clock_seconds,
    )

    if success:
        e2e_stats = compute_latency_stats(
            [m.e2e_latency for m in success if m.e2e_latency is not None]
        )
        ttft_stats = compute_latency_stats(
            [m.ttft for m in success if m.ttft is not None]
        )
        itl_stats = compute_itl_stats(
            [itl for m in success for itl in m.inter_token_latencies]
        )

        result.e2e_mean = e2e_stats["mean"]
        result.e2e_p50 = e2e_stats["p50"]
        result.e2e_p95 = e2e_stats["p95"]
        result.e2e_p99 = e2e_stats["p99"]
        result.e2e_max = e2e_stats["max"]

        result.ttft_mean = ttft_stats["mean"]
        result.ttft_p50 = ttft_stats["p50"]
        result.ttft_p95 = ttft_stats["p95"]
        result.ttft_p99 = ttft_stats["p99"]

        result.throughput_rps = (
            len(success) / wall_clock_seconds if wall_clock_seconds > 0 else 0.0
        )
        result.throughput_tps = (
            sum(m.completion_tokens for m in success) / wall_clock_seconds
            if wall_clock_seconds > 0
            else 0.0
        )

        result.itl_mean = itl_stats["mean"] or 0.0
        result.itl_p50 = itl_stats["p50"] or 0.0
        result.itl_p95 = itl_stats["p95"] or 0.0

    return result


async def run_benchmarks(
    provider: Provider,
    model: str,
    concurrency: list[int],
    prompt_lengths: list[int],
    max_tokens: int,
    temperature: float = 0.0,
    top_p: float = 1.0,
    output: str | None = None,
    workload_profile: str | None = None,
    warmup_iterations: int = DEFAULT_WARMUP_ITERATIONS,
    measured_iterations: int = DEFAULT_MEASURED_ITERATIONS,
) -> list[ScenarioResult]:
    """Run the full benchmark suite across all concurrency × prompt combinations.

    Args:
        provider: Any ``Provider`` subclass.
        model: Model identifier.
        concurrency: List of concurrency levels to test.
        prompt_lengths: List of prompt token counts to test.
        max_tokens: Max completion tokens per request.
        temperature: Sampling temperature.
        top_p: Nucleus sampling threshold.
        output: Optional CSV output path.
        warmup_iterations: Number of warmup batches per scenario.
        measured_iterations: Number of measured batches per scenario.

    Returns:
        List of ``ScenarioResult``, one per combination.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 80)
    logger.info("LLM Race Benchmark")
    logger.info("=" * 80)
    logger.info("  Provider:       %s", type(provider).__name__)
    logger.info("  Model:          %s", model)
    logger.info("  Concurrency:    %s", concurrency)
    logger.info("  Prompt lengths: %s", prompt_lengths)
    logger.info("  Max tokens:     %d", max_tokens)
    logger.info("  Warmup iters:   %d", warmup_iterations)
    logger.info("  Measured iters: %d", measured_iterations)
    if workload_profile:
        logger.info("  Workload profile: %s", workload_profile)
    logger.info("=" * 80)

    all_results: list[ScenarioResult] = []
    for prompt_len in prompt_lengths:
        for conc in concurrency:
            wall_start = time.monotonic()
            metrics = await run_scenario(
                provider=provider,
                model=model,
                concurrency=conc,
                prompt_length=prompt_len,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                warmup_iterations=warmup_iterations,
                measured_iterations=measured_iterations,
            )
            wall_elapsed = time.monotonic() - wall_start

            scenario = _build_scenario_result(metrics, conc, prompt_len, wall_elapsed)
            all_results.append(scenario)

    print("\n" + format_table(all_results))

    if output is None:
        output = f"benchmark_{ts}.csv"
    save_csv(all_results, output)
    logger.info("Results saved to %s", output)

    save_json(all_results, f"benchmark_{ts}.json")

    return all_results
