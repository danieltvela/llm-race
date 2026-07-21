"""Query result dataclasses for llm-race database."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkGroupSummary:
    """Aggregated view of all benchmarks sharing the same run_id (one python3 run)."""

    run_id: str
    model_name: str
    model_slug: str
    ai_lab: str
    provider_name: str
    hostname: str
    workload_profile: str
    benchmark_type: str
    scenario_count: int
    started_at: datetime
    completed_at: datetime | None
    best_throughput_tps: float | None
    best_pp: float | None
    avg_ttft_mean_ms: float | None
    avg_e2e_mean_ms: float | None
    resolve_rate: float | None
    total_instances: int | None
    swebench_subset: str | None
    swebench_split: str | None
    status: str
    notes: str
    launch_script: str


@dataclass(frozen=True)
class BenchmarkFilters:
    """Filters for querying benchmarks."""

    model_name: str | None = None
    slug: str | None = None
    ai_lab: str | None = None
    provider_name: str | None = None
    machine_hostname: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    status: str | None = None
    workload_profile: str | None = None
    benchmark_type: str | None = None
    prompt_size: str | None = None


@dataclass(frozen=True)
class BenchmarkSummary:
    """Summary view of a benchmark run (from joined Model + Machine)."""

    id: int
    run_id: str
    model_name: str
    model_slug: str
    ai_lab: str
    provider_name: str
    hostname: str
    workload_profile: str
    benchmark_type: str
    prompt_size: str
    concurrency: int
    started_at: datetime
    completed_at: datetime | None
    wall_clock_seconds: float | None
    total_requests: int
    successful_requests: int
    failed_requests: int
    throughput_tps: float | None
    pp_mean: float | None
    ttft_mean_ms: float | None
    e2e_mean_ms: float | None
    status: str
    notes: str
    launch_script: str


@dataclass(frozen=True)
class ResultRow:
    """Per-request result entry."""

    request_id: int
    status: str
    error_message: str | None
    ttft_ms: float | None
    e2e_latency_ms: float | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tokens_per_second: float | None
    pp: float | None
    itl_mean: float | None


@dataclass(frozen=True)
class BenchmarkDetail(BenchmarkSummary):
    """Full benchmark detail including nested results."""

    throughput_rps: float | None
    e2e_p50_ms: float | None
    e2e_p90_ms: float | None
    e2e_p99_ms: float | None
    ttft_mean_ms: float | None
    ttft_p50_ms: float | None
    ttft_p90_ms: float | None
    ttft_p99_ms: float | None
    pp_mean: float | None
    pp_p50: float | None
    pp_p90: float | None
    pp_p99: float | None
    itl_mean_ms: float | None
    itl_p50_ms: float | None
    itl_p90_ms: float | None
    itl_p99_ms: float | None
    cost_per_token: float | None
    error_message: str | None
    results: list[ResultRow] = field(default_factory=list)


@dataclass(frozen=True)
class PaginatedResult(Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total_count: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ModelSummary:
    """Summary view of a model with benchmark count."""

    id: int
    slug: str
    ai_lab: str
    name: str
    quantization: str | None
    extra: str | None
    provider_name: str
    context_window: int | None
    benchmark_count: int


@dataclass(frozen=True)
class TimeseriesPoint:
    """Single time-series data point."""

    date: datetime
    value: float
    run_id: str
    label: str