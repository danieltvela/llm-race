"""Query result dataclasses for llm-race database."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkFilters:
    """Filters for querying benchmarks."""

    model_name: str | None = None
    provider_name: str | None = None
    machine_hostname: str | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    status: str | None = None
    workload_profile: str | None = None
    prompt_size: str | None = None


@dataclass(frozen=True)
class BenchmarkSummary:
    """Summary view of a benchmark run (from joined Model + Machine)."""

    id: int
    run_id: str
    model_name: str
    provider_name: str
    hostname: str
    workload_profile: str
    prompt_size: str
    concurrency: int
    started_at: datetime
    completed_at: datetime | None
    wall_clock_seconds: float | None
    total_requests: int
    successful_requests: int
    failed_requests: int
    throughput_tps: float | None
    e2e_mean_ms: float | None
    status: str


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
class TimeseriesPoint:
    """Single time-series data point."""

    date: datetime
    value: float
    run_id: str
    label: str