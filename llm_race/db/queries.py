"""Named database queries for LLM Race."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, overload

from sqlalchemy import Select, asc, case, desc, func, select
from sqlalchemy.orm import Session, selectinload

from llm_race.db.models import Benchmark, Machine, Model, Result
from llm_race.db.types import (
    BenchmarkDetail,
    BenchmarkFilters,
    BenchmarkGroupSummary,
    BenchmarkSummary,
    PaginatedResult,
    ResultRow,
    TimeseriesPoint,
)

# Whitelist of allowed sort columns
_SORT_WHITELIST = {
    "started_at", "completed_at", "throughput_tps", "throughput_rps",
    "e2e_mean_ms", "e2e_p50_ms", "e2e_p90_ms", "e2e_p99_ms",
    "ttft_mean_ms", "ttft_p50_ms", "ttft_p90_ms", "ttft_p99_ms",
    "itl_mean_ms", "itl_p50_ms", "itl_p90_ms", "itl_p99_ms",
    "wall_clock_seconds", "total_requests", "successful_requests",
    "failed_requests", "concurrency", "status",
    "pp_mean", "pp_p50", "pp_p90", "pp_p99",
}


def list_benchmarks(
    session: Session,
    filters: BenchmarkFilters | None = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    offset: int = 0,
    limit: int = 20,
) -> PaginatedResult[BenchmarkSummary]:
    """List benchmarks with optional filters, sorting, and pagination.

    Args:
        session: SQLAlchemy ORM session.
        filters: Optional BenchmarkFilters to filter results.
        sort_by: Column name to sort by (must be in _SORT_WHITELIST).
        sort_order: "asc" or "desc".
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        PaginatedResult of BenchmarkSummary items.

    Raises:
        ValueError: If sort_by is not in _SORT_WHITELIST.
    """
    if sort_by not in _SORT_WHITELIST:
        raise ValueError(f"Invalid sort_by: {sort_by}. Allowed: {sorted(_SORT_WHITELIST)}")

    # Build base query with joins
    query = (
        select(Benchmark)
        .join(Model, Benchmark.model_id == Model.id)
        .join(Machine, Benchmark.machine_id == Machine.id)
    )

    # Apply filters
    if filters:
        if filters.model_name:
            query = query.where(Model.name.ilike(f"%{filters.model_name}%"))
        if filters.provider_name:
            query = query.where(Model.provider_name == filters.provider_name)
        if filters.machine_hostname:
            query = query.where(Machine.hostname == filters.machine_hostname)
        if filters.date_start:
            query = query.where(Benchmark.started_at >= filters.date_start)
        if filters.date_end:
            query = query.where(Benchmark.started_at <= filters.date_end)
        if filters.status:
            query = query.where(Benchmark.status == filters.status)
        if filters.workload_profile:
            query = query.where(Benchmark.workload_profile == filters.workload_profile)
        if filters.prompt_size:
            query = query.where(Benchmark.prompt_size == filters.prompt_size)

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = session.execute(count_query).scalar() or 0

    # Apply sorting
    sort_column = getattr(Benchmark, sort_by)
    order_fn = desc if sort_order.lower() == "desc" else asc
    query = query.order_by(order_fn(sort_column))

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute and map
    rows = session.execute(query).scalars().unique().all()

    items = [_benchmark_to_summary(b) for b in rows]

    return PaginatedResult(
        items=items,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


def compare_runs(
    session: Session,
    run_ids: list[str],
) -> list[BenchmarkDetail]:
    """Fetch detailed metrics for 2-4 specific runs for side-by-side comparison.

    Args:
        session: SQLAlchemy ORM session.
        run_ids: List of 2-4 benchmark run_id UUID strings.

    Returns:
        List of BenchmarkDetail with nested per-request results.

    Raises:
        ValueError: If run_ids has fewer than 2 or more than 4 items.
    """
    if len(run_ids) < 2:
        raise ValueError(f"compare_runs requires at least 2 run_ids, got {len(run_ids)}")
    if len(run_ids) > 4:
        raise ValueError(f"compare_runs accepts at most 4 run_ids, got {len(run_ids)}")

    query = (
        select(Benchmark)
        .options(selectinload(Benchmark.results))
        .options(selectinload(Benchmark.model))
        .options(selectinload(Benchmark.machine))
        .where(Benchmark.run_id.in_(run_ids))
    )

    rows = session.execute(query).scalars().unique().all()

    # Preserve input order
    run_id_to_benchmark = {b.run_id: b for b in rows}
    ordered = [run_id_to_benchmark[rid] for rid in run_ids if rid in run_id_to_benchmark]

    return [_benchmark_to_detail(b) for b in ordered]


def _benchmark_to_detail(b: Benchmark) -> BenchmarkDetail:
    """Map a Benchmark ORM row to a BenchmarkDetail dataclass with nested results."""
    return BenchmarkDetail(
        id=b.id,
        run_id=b.run_id,
        model_name=b.model.name if b.model else "",
        provider_name=b.model.provider_name if b.model else "",
        hostname=b.machine.hostname if b.machine else "",
        workload_profile=b.workload_profile,
        prompt_size=b.prompt_size,
        concurrency=b.concurrency,
        started_at=b.started_at,
        completed_at=b.completed_at,
        wall_clock_seconds=b.wall_clock_seconds,
        total_requests=b.total_requests,
        successful_requests=b.successful_requests,
        failed_requests=b.failed_requests,
        throughput_tps=b.throughput_tps,
        pp_mean=b.pp_mean,
        ttft_mean_ms=b.ttft_mean_ms,
        e2e_mean_ms=b.e2e_mean_ms,
        status=b.status,
        notes=b.notes,
        launch_script=b.launch_script,
        # Extended fields (BenchmarkDetail-specific, beyond BenchmarkSummary)
        throughput_rps=b.throughput_rps,
        e2e_p50_ms=b.e2e_p50_ms,
        e2e_p90_ms=b.e2e_p90_ms,
        e2e_p99_ms=b.e2e_p99_ms,
        ttft_p50_ms=b.ttft_p50_ms,
        ttft_p90_ms=b.ttft_p90_ms,
        ttft_p99_ms=b.ttft_p99_ms,
        pp_p50=b.pp_p50,
        pp_p90=b.pp_p90,
        pp_p99=b.pp_p99,
        itl_mean_ms=b.itl_mean_ms,
        itl_p50_ms=b.itl_p50_ms,
        itl_p90_ms=b.itl_p90_ms,
        itl_p99_ms=b.itl_p99_ms,
        cost_per_token=b.cost_per_token,
        error_message=b.error_message,
        results=[_result_to_row(r) for r in (b.results or [])],
    )


def _result_to_row(r) -> ResultRow:
    """Map a Result ORM row to a ResultRow dataclass."""
    return ResultRow(
        request_id=r.request_id,
        status=r.status,
        error_message=r.error_message,
        ttft_ms=r.ttft_ms,
        e2e_latency_ms=r.e2e_latency_ms,
        prompt_tokens=r.prompt_tokens,
        completion_tokens=r.completion_tokens,
        total_tokens=r.total_tokens,
        tokens_per_second=r.tokens_per_second,
        pp=r.pp,
        itl_mean=r.itl_mean,
    )


# Whitelist of valid metric columns at benchmark level
_BENCHMARK_METRICS = {
    "throughput_tps", "throughput_rps",
    "e2e_mean_ms", "e2e_p50_ms", "e2e_p90_ms", "e2e_p99_ms",
    "ttft_mean_ms", "ttft_p50_ms", "ttft_p90_ms", "ttft_p99_ms",
    "pp_mean", "pp_p50", "pp_p90", "pp_p99",
    "itl_mean_ms", "itl_p50_ms", "itl_p90_ms", "itl_p99_ms",
    "wall_clock_seconds", "total_requests", "successful_requests",
    "failed_requests",
}

# Whitelist of valid metric columns at result level
_RESULT_METRICS = {
    "ttft_ms", "e2e_latency_ms", "prompt_tokens", "completion_tokens",
    "total_tokens", "tokens_per_second", "pp", "itl_mean",
}

_VALID_LEVELS = {"benchmark", "result"}


def timeseries(
    session: Session,
    model: str | None = None,
    provider: str | None = None,
    metric: str = "throughput_tps",
    date_start: datetime | None = None,
    date_end: datetime | None = None,
    level: str = "benchmark",
) -> list[TimeseriesPoint]:
    """Get performance data over time for charting.

    Args:
        session: SQLAlchemy ORM session.
        model: Optional model name filter (LIKE match).
        provider: Optional provider name filter (exact match).
        metric: Metric column name (must be in the appropriate whitelist).
        date_start: Optional start date filter.
        date_end: Optional end date filter.
        level: "benchmark" for Benchmark-level metrics, "result" for Result-level.

    Returns:
        List of TimeseriesPoint ordered by date ASC.

    Raises:
        ValueError: If metric or level is invalid.
    """
    if level not in _VALID_LEVELS:
        raise ValueError(f"Invalid level: {level}. Valid: {sorted(_VALID_LEVELS)}")
    if level == "benchmark" and metric not in _BENCHMARK_METRICS:
        raise ValueError(f"Invalid benchmark metric: {metric}. Valid: {sorted(_BENCHMARK_METRICS)}")
    if level == "result" and metric not in _RESULT_METRICS:
        raise ValueError(f"Invalid result metric: {metric}. Valid: {sorted(_RESULT_METRICS)}")

    if level == "benchmark":
        return _timeseries_benchmark(session, model, provider, metric, date_start, date_end)
    else:
        return _timeseries_result(session, model, provider, metric, date_start, date_end)


def _timeseries_benchmark(
    session: Session,
    model: str | None,
    provider: str | None,
    metric: str,
    date_start: datetime | None,
    date_end: datetime | None,
) -> list[TimeseriesPoint]:
    """Timeseries at Benchmark summary level."""
    query = (
        select(Benchmark, Model.name, Model.provider_name)
        .join(Model, Benchmark.model_id == Model.id)
    )

    if model:
        query = query.where(Model.name.ilike(f"%{model}%"))
    if provider:
        query = query.where(Model.provider_name == provider)
    if date_start:
        query = query.where(Benchmark.started_at >= date_start)
    if date_end:
        query = query.where(Benchmark.started_at <= date_end)

    metric_col = getattr(Benchmark, metric)
    query = query.where(metric_col.isnot(None))

    query = query.order_by(asc(Benchmark.started_at))

    rows = session.execute(query).all()

    return [
        TimeseriesPoint(
            date=_ensure_aware(row.Benchmark.started_at),
            value=float(getattr(row.Benchmark, metric)),
            run_id=row.Benchmark.run_id,
            label=metric,
        )
        for row in rows
    ]


def _timeseries_result(
    session: Session,
    model: str | None,
    provider: str | None,
    metric: str,
    date_start: datetime | None,
    date_end: datetime | None,
) -> list[TimeseriesPoint]:
    """Timeseries at individual Result level."""
    query = (
        select(Result, Benchmark.started_at, Benchmark.run_id, Model.name, Model.provider_name)
        .join(Benchmark, Result.benchmark_id == Benchmark.id)
        .join(Model, Benchmark.model_id == Model.id)
    )

    if model:
        query = query.where(Model.name.ilike(f"%{model}%"))
    if provider:
        query = query.where(Model.provider_name == provider)
    if date_start:
        query = query.where(Result.created_at >= date_start)
    if date_end:
        query = query.where(Result.created_at <= date_end)

    metric_col = getattr(Result, metric)
    query = query.where(metric_col.isnot(None))
    query = query.order_by(asc(Result.created_at))

    rows = session.execute(query).all()

    return [
        TimeseriesPoint(
            date=_ensure_aware(row[1]),
            value=float(getattr(row[0], metric)),
            run_id=row[2],
            label=metric,
        )
        for row in rows
    ]


@overload
def _ensure_aware(dt: datetime) -> datetime: ...


@overload
def _ensure_aware(dt: None) -> None: ...


def _ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def list_benchmark_groups(
    session: Session,
    filters: BenchmarkFilters | None = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    offset: int = 0,
    limit: int = 20,
) -> PaginatedResult[BenchmarkGroupSummary]:
    """List benchmarks grouped by run_id — one row per ``python3`` invocation.

    Each group represents a single CLI run and aggregates the individual
    (concurrency × prompt_size) scenarios into a summary row.
    """
    if sort_by not in _SORT_WHITELIST:
        raise ValueError(f"Invalid sort_by: {sort_by}. Allowed: {sorted(_SORT_WHITELIST)}")

    priority = case(
        (Benchmark.status == "running", 4),
        (Benchmark.status == "error", 3),
        (Benchmark.status == "partial", 2),
        else_=1,
    )
    group_status = case(
        (func.max(priority) == 4, "running"),
        (func.max(priority) == 3, "error"),
        (func.max(priority) == 2, "partial"),
        else_="success",
    )

    query = (
        select(
            Benchmark.run_id,
            Model.name.label("model_name"),
            Model.provider_name,
            Machine.hostname,
            Benchmark.workload_profile,
            func.count(Benchmark.id).label("scenario_count"),
            func.min(Benchmark.started_at).label("started_at"),
            func.max(Benchmark.completed_at).label("completed_at"),
            func.max(Benchmark.throughput_tps).label("best_throughput_tps"),
            func.max(Benchmark.pp_mean).label("best_pp"),
            func.avg(Benchmark.ttft_mean_ms).label("avg_ttft_mean_ms"),
            func.avg(Benchmark.e2e_mean_ms).label("avg_e2e_mean_ms"),
            group_status.label("status"),
            func.min(Benchmark.notes).label("notes"),
            func.min(Benchmark.launch_script).label("launch_script"),
        )
        .join(Model, Benchmark.model_id == Model.id)
        .join(Machine, Benchmark.machine_id == Machine.id)
        .group_by(Benchmark.run_id, Model.name, Model.provider_name, Machine.hostname, Benchmark.workload_profile)
    )

    if filters:
        if filters.model_name:
            query = query.where(Model.name.ilike(f"%{filters.model_name}%"))
        if filters.provider_name:
            query = query.where(Model.provider_name == filters.provider_name)
        if filters.machine_hostname:
            query = query.where(Machine.hostname == filters.machine_hostname)
        if filters.date_start:
            query = query.where(Benchmark.started_at >= filters.date_start)
        if filters.date_end:
            query = query.where(Benchmark.started_at <= filters.date_end)
        if filters.workload_profile:
            query = query.where(Benchmark.workload_profile == filters.workload_profile)
        if filters.prompt_size:
            query = query.having(
                func.sum(case((Benchmark.prompt_size == filters.prompt_size, 1), else_=0)) > 0
            )

    count_q = select(func.count()).select_from(query.subquery())
    total_count = session.execute(count_q).scalar() or 0

    if sort_by == "status":
        query = query.order_by(
            desc(group_status) if sort_order.lower() == "desc" else asc(group_status)
        )
    elif sort_by == "started_at":
        query = query.order_by(
            desc(func.min(Benchmark.started_at)) if sort_order.lower() == "desc" else asc(func.min(Benchmark.started_at))
        )
    elif sort_by == "completed_at":
        query = query.order_by(
            desc(func.max(Benchmark.completed_at)) if sort_order.lower() == "desc" else asc(func.max(Benchmark.completed_at))
        )
    elif sort_by == "throughput_tps":
        query = query.order_by(
            desc(func.max(Benchmark.throughput_tps)) if sort_order.lower() == "desc" else asc(func.max(Benchmark.throughput_tps))
        )
    elif sort_by == "e2e_mean_ms":
        query = query.order_by(
            desc(func.avg(Benchmark.e2e_mean_ms)) if sort_order.lower() == "desc" else asc(func.avg(Benchmark.e2e_mean_ms))
        )
    else:
        col = getattr(Benchmark, sort_by)
        agg = func.max(col)
        query = query.order_by(desc(agg) if sort_order.lower() == "desc" else asc(agg))

    query = query.offset(offset).limit(limit)
    rows = session.execute(query).all()

    items = [_row_to_group_summary(r) for r in rows]
    return PaginatedResult(items=items, total_count=total_count, offset=offset, limit=limit)


def _row_to_group_summary(r) -> BenchmarkGroupSummary:
    """Map a GROUP BY result row to a BenchmarkGroupSummary."""
    return BenchmarkGroupSummary(
        run_id=r.run_id,
        model_name=r.model_name,
        provider_name=r.provider_name,
        hostname=r.hostname,
        workload_profile=r.workload_profile or "",
        scenario_count=r.scenario_count,
        started_at=_ensure_aware(r.started_at),
        completed_at=_ensure_aware(r.completed_at),
        best_throughput_tps=r.best_throughput_tps,
        best_pp=r.best_pp,
        avg_ttft_mean_ms=(
            round(float(r.avg_ttft_mean_ms), 2) if r.avg_ttft_mean_ms is not None else None
        ),
        avg_e2e_mean_ms=(
            round(float(r.avg_e2e_mean_ms), 2) if r.avg_e2e_mean_ms is not None else None
        ),
        status=r.status,
        notes=r.notes or "",
        launch_script=r.launch_script or "",
    )


def get_run_benchmarks(
    session: Session,
    run_id: str,
) -> list[BenchmarkDetail]:
    """Fetch all individual Benchmark rows within a run_id group with full metrics."""
    query = (
        select(Benchmark)
        .options(selectinload(Benchmark.results))
        .options(selectinload(Benchmark.model))
        .options(selectinload(Benchmark.machine))
        .where(Benchmark.run_id == run_id)
        .order_by(asc(Benchmark.concurrency), asc(Benchmark.prompt_size))
    )
    rows = session.execute(query).scalars().unique().all()
    return [_benchmark_to_detail(b) for b in rows]


def _benchmark_to_summary(b: Benchmark) -> BenchmarkSummary:
    """Map a Benchmark ORM row to a BenchmarkSummary dataclass."""
    return BenchmarkSummary(
        id=b.id,
        run_id=b.run_id,
        model_name=b.model.name if b.model else "",
        provider_name=b.model.provider_name if b.model else "",
        hostname=b.machine.hostname if b.machine else "",
        workload_profile=b.workload_profile,
        prompt_size=b.prompt_size,
        concurrency=b.concurrency,
        started_at=b.started_at,
        completed_at=b.completed_at,
        wall_clock_seconds=b.wall_clock_seconds,
        total_requests=b.total_requests,
        successful_requests=b.successful_requests,
        failed_requests=b.failed_requests,
        throughput_tps=b.throughput_tps,
        pp_mean=b.pp_mean,
        ttft_mean_ms=b.ttft_mean_ms,
        e2e_mean_ms=b.e2e_mean_ms,
        status=b.status,
        notes=b.notes,
        launch_script=b.launch_script,
    )
