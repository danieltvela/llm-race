"""Database persistence for benchmark results.

Saves aggregated (ScenarioResult) and per-request (RequestMetrics)
data to SQLite via SQLAlchemy ORM.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from llm_race.bench.runner import RequestMetrics, ScenarioResult
from llm_race.db.models import Machine, Model, Benchmark, Result
from llm_race.utils.slug import parse_slug

logger = logging.getLogger(__name__)


def _to_ms(seconds: float | None) -> float | None:
    """Convert seconds to milliseconds, rounded to 2 decimals."""
    if seconds is None:
        return None
    return round(seconds * 1000, 2)


def save_benchmark_run(
    session: Session,
    *,
    run_id: str,
    provider_type: str,
    model_slug: str,
    workload_profile: str | None,
    system_info: dict[str, Any],
    max_tokens: int,
    temperature: float,
    top_p: float,
    scenarios: list[tuple[ScenarioResult, list[RequestMetrics], datetime]],
    notes: str = "",
    launch_script: str = "",
) -> list[int]:
    """Persist benchmark results to the database.

    Args:
        session: SQLAlchemy session.
        run_id: Unique run identifier (UUID4 string).
        provider_type: Provider name (e.g. "openai", "anthropic").
        model_slug: Model slug identifier (e.g. "qwen/qwen3-8b/none").
        workload_profile: Optional workload profile name.
        system_info: Dict from SystemInfo.to_dict() with machine specs.
        max_tokens: Maximum generation tokens.
        temperature: Sampling temperature.
        top_p: Top-p sampling value.
        scenarios: List of (ScenarioResult, list[RequestMetrics], started_at)
            triples — one per (concurrency, prompt_length) combination.
        notes: Optional free-form notes attached to the benchmark run.
        launch_script: Optional launch script content attached to the benchmark run.

    Returns:
        List of created Benchmark row IDs.
    """
    if not scenarios:
        return []

    # Step 1 — Find or create Model record.
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
            provider_name=provider_type,
        )
        session.add(model_record)
        session.flush()

    # Step 2 — Find or create Machine record.
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

    # Step 3 — Create Benchmark rows for each scenario.
    benchmark_ids: list[int] = []
    for scenario, per_request_metrics, started_at in scenarios:
        benchmark = Benchmark(
            run_id=run_id,
            model_id=model_record.id,
            machine_id=machine_record.id,
            workload_profile=workload_profile or "",
            prompt_size=str(scenario.prompt_length),
            prompt_token_count=scenario.prompt_length,
            concurrency=scenario.concurrency,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            started_at=started_at,
            wall_clock_seconds=scenario.wall_clock_seconds,
            total_requests=scenario.total_requests,
            successful_requests=scenario.successful_requests,
            failed_requests=scenario.failed_requests,
            throughput_rps=scenario.throughput_rps,
            throughput_tps=scenario.throughput_tps,
            e2e_mean_ms=_to_ms(scenario.e2e_mean),
            e2e_p50_ms=_to_ms(scenario.e2e_p50),
            e2e_p90_ms=_to_ms(scenario.e2e_p95),
            e2e_p99_ms=_to_ms(scenario.e2e_p99),
            ttft_mean_ms=_to_ms(scenario.ttft_mean),
            ttft_p50_ms=_to_ms(scenario.ttft_p50),
            ttft_p90_ms=_to_ms(scenario.ttft_p95),
            ttft_p99_ms=_to_ms(scenario.ttft_p99),
            itl_mean_ms=_to_ms(scenario.itl_mean),
            itl_p50_ms=_to_ms(scenario.itl_p50),
            itl_p90_ms=_to_ms(scenario.itl_p95),
            pp_mean=(
                round(scenario.pp_mean, 2) if scenario.pp_mean else None
            ),
            pp_p50=(
                round(scenario.pp_p50, 2) if scenario.pp_p50 else None
            ),
            pp_p90=(
                round(scenario.pp_p95, 2) if scenario.pp_p95 else None
            ),
            pp_p99=(
                round(scenario.pp_p99, 2) if scenario.pp_p99 else None
            ),
            status=(
                "success" if scenario.failed_requests == 0 else (
                    "partial" if scenario.successful_requests > 0 else "error"
                )
            ),
            notes=notes,
            launch_script=launch_script,
        )
        session.add(benchmark)
        session.flush()
        benchmark_ids.append(benchmark.id)

        # Step 4 — Create Result rows for each request metric.
        for metrics in per_request_metrics:
            itl_mean = (
                statistics.mean(metrics.inter_token_latencies)
                if metrics.inter_token_latencies
                else None
            )
            result = Result(
                benchmark_id=benchmark.id,
                request_id=metrics.request_id,
                status=metrics.status,
                error_message=metrics.error_message,
                ttft_ms=_to_ms(metrics.ttft),
                e2e_latency_ms=_to_ms(metrics.e2e_latency),
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
                tokens_per_second=metrics.tokens_per_second,
                pp=(
                    round(metrics.pp, 2) if metrics.pp else None
                ),
                itl_mean=_to_ms(itl_mean),
            )
            session.add(result)

    # Step 5 — Commit.
    try:
        session.commit()
        logger.info("Saved %d benchmark rows to DB", len(scenarios))
    except Exception:
        session.rollback()
        logger.warning("Failed to save benchmark results to DB", exc_info=True)
        return []

    return benchmark_ids