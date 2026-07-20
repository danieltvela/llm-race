"""Test fixtures and helper factories for db-queries test suite."""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from llm_race.db.models import (
    Base,
    Benchmark,
    Machine,
    Model,
    Result,
    init_db,
)
from llm_race.db.queries import compare_runs, list_benchmarks, timeseries
from llm_race.db.types import (
    BenchmarkDetail,
    BenchmarkFilters,
    BenchmarkSummary,
    PaginatedResult,
    ResultRow,
    TimeseriesPoint,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create a fresh SQLite database file for each test."""
    tmp = Path(tempfile.mktemp(suffix=".db"))
    engine, sf = init_db(tmp)
    session = sf()
    yield session
    session.close()
    engine.dispose()
    os.unlink(tmp)


@pytest.fixture
def query_session(db_session: Session) -> Session:
    """Populate *db_session* with reference data for query tests."""
    session: Session = db_session

    # --- Models ----------------------------------------------------------
    model_vllm = Model(
        slug="meta-llama/llama-3.1-8b/fp8",
        ai_lab="meta-llama",
        name="meta-llama/Llama-3.1-8B",
        quantization="fp8",
        provider_name="vllm",
        context_window=128_000,
    )
    session.add(model_vllm)
    session.flush()

    model_openai = Model(
        slug="openai/gpt-4o-mini/none",
        ai_lab="openai",
        name="gpt-4o-mini",
        quantization="none",
        provider_name="openai",
        context_window=128_000,
    )
    session.add(model_openai)
    session.flush()

    # --- Machines --------------------------------------------------------
    machine_1 = Machine(
        hostname="gpu-server-1",
        cpu="Intel Xeon Platinum 8380",
        gpu="NVIDIA A100-SXM4-80GB",
        gpu_count=8,
        ram_gb=512.0,
        os="Linux",
        os_version="Ubuntu 22.04",
        driver_version="535.129.03",
        python_version="3.11",
    )
    session.add(machine_1)
    session.flush()

    machine_2 = Machine(
        hostname="gpu-server-2",
        cpu="AMD EPYC 7763",
        gpu="NVIDIA H100 80GB HBM3",
        gpu_count=4,
        ram_gb=256.0,
        os="Linux",
        os_version="Ubuntu 24.04",
        driver_version="550.54.15",
        python_version="3.12",
    )
    session.add(machine_2)
    session.flush()

    # --- Benchmarks ------------------------------------------------------
    benchmarks: list[Benchmark] = []

    benchmarks.append(Benchmark(
        run_id=str(uuid.uuid4()),
        model_id=model_vllm.id,
        machine_id=machine_1.id,
        workload_profile="single-user",
        prompt_size="tiny",
        concurrency=1,
        max_tokens=256,
        temperature=0.0,
        top_p=1.0,
        started_at=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        total_requests=3,
        successful_requests=3,
        failed_requests=0,
        throughput_tps=120.5,
        status="completed",
    ))

    benchmarks.append(Benchmark(
        run_id=str(uuid.uuid4()),
        model_id=model_vllm.id,
        machine_id=machine_1.id,
        workload_profile="multi-agent",
        prompt_size="medium",
        concurrency=4,
        max_tokens=512,
        temperature=0.7,
        top_p=0.95,
        started_at=datetime(2026, 4, 15, 14, 30, 0, tzinfo=timezone.utc),
        total_requests=10,
        successful_requests=9,
        failed_requests=1,
        throughput_tps=85.3,
        status="completed",
    ))

    benchmarks.append(Benchmark(
        run_id=str(uuid.uuid4()),
        model_id=model_vllm.id,
        machine_id=machine_2.id,
        workload_profile="high-throughput",
        prompt_size="large",
        concurrency=16,
        max_tokens=1024,
        temperature=0.0,
        top_p=1.0,
        started_at=datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc),
        total_requests=50,
        successful_requests=48,
        failed_requests=2,
        throughput_tps=200.0,
        status="running",
    ))

    benchmarks.append(Benchmark(
        run_id=str(uuid.uuid4()),
        model_id=model_openai.id,
        machine_id=machine_2.id,
        workload_profile="single-user",
        prompt_size="small",
        concurrency=1,
        max_tokens=128,
        temperature=0.5,
        top_p=0.9,
        started_at=datetime(2026, 5, 20, 16, 0, 0, tzinfo=timezone.utc),
        total_requests=5,
        successful_requests=5,
        failed_requests=0,
        throughput_tps=45.2,
        status="completed",
    ))

    benchmarks.append(Benchmark(
        run_id=str(uuid.uuid4()),
        model_id=model_openai.id,
        machine_id=machine_1.id,
        workload_profile="chat",
        prompt_size="max",
        concurrency=8,
        max_tokens=2048,
        temperature=0.3,
        top_p=0.99,
        started_at=datetime(2026, 6, 10, 11, 15, 0, tzinfo=timezone.utc),
        total_requests=20,
        successful_requests=18,
        failed_requests=2,
        throughput_tps=30.1,
        status="failed",
    ))

    session.add_all(benchmarks)
    session.flush()

    # --- Results ---------------------------------------------------------
    results: list[Result] = []
    request_counter = 1

    for b in benchmarks:
        n_results = max(2, b.total_requests)
        for req_idx in range(n_results):
            results.append(Result(
                benchmark_id=b.id,
                request_id=request_counter,
                status="success" if req_idx < b.successful_requests else "error",
                error_message="timeout" if req_idx >= b.successful_requests else None,
                ttft_ms=round(10.0 + req_idx * 2.5, 2),
                e2e_latency_ms=round(100.0 + req_idx * 15.0, 2),
                prompt_tokens=50 + req_idx * 10,
                completion_tokens=20 + req_idx * 5,
                total_tokens=70 + req_idx * 15,
                tokens_per_second=round(45.0 + req_idx * 3.0, 2),
                itl_mean=round(5.0 + req_idx * 0.5, 2),
            ))
            request_counter += 1

    session.add_all(results)
    session.commit()

    session.query_session_data = {  # type: ignore[attr-defined]
        "models": [model_vllm, model_openai],
        "machines": [machine_1, machine_2],
        "benchmarks": benchmarks,
        "results": results,
    }

    return session


# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------

def create_model(
    session: Session,
    slug: str = "test-lab/test-model/none",
    ai_lab: str = "test-lab",
    name: str = "test-model",
    quantization: str | None = "none",
    provider_name: str = "vllm",
    context_window: int | None = 4096,
    extra: str | None = None,
) -> Model:
    """Create and return a Model record."""
    m = Model(
        slug=slug,
        ai_lab=ai_lab,
        name=name,
        quantization=quantization,
        extra=extra,
        provider_name=provider_name,
        context_window=context_window,
    )
    session.add(m)
    session.commit()
    return m


def create_machine(
    session: Session,
    hostname: str = "test-host",
    cpu: str | None = "Intel Xeon",
    gpu: str | None = "A100",
    gpu_count: int | None = 1,
    ram_gb: float | None = 128.0,
    os: str | None = "Linux",
    os_version: str | None = "22.04",
    driver_version: str | None = "535.0",
    python_version: str | None = "3.11",
) -> Machine:
    """Create and return a Machine record."""
    machine = Machine(
        hostname=hostname,
        cpu=cpu,
        gpu=gpu,
        gpu_count=gpu_count,
        ram_gb=ram_gb,
        os=os,
        os_version=os_version,
        driver_version=driver_version,
        python_version=python_version,
    )
    session.add(machine)
    session.commit()
    return machine


def create_benchmark(
    session: Session,
    model: Model,
    machine: Machine,
    run_id: str | None = None,
    workload_profile: str = "single-user",
    prompt_size: str = "medium",
    concurrency: int = 1,
    max_tokens: int = 256,
    temperature: float = 0.0,
    top_p: float = 1.0,
    status: str = "completed",
    started_at: datetime | None = None,
    total_requests: int = 1,
    successful_requests: int = 1,
    failed_requests: int = 0,
) -> Benchmark:
    """Create and return a Benchmark record."""
    b = Benchmark(
        run_id=run_id or str(uuid.uuid4()),
        model_id=model.id,
        machine_id=machine.id,
        workload_profile=workload_profile,
        prompt_size=prompt_size,
        concurrency=concurrency,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        started_at=started_at or datetime.now(timezone.utc),
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        status=status,
    )
    session.add(b)
    session.commit()
    return b


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def test_query_fixture_populates_data(query_session: Session) -> None:
    """Verify the query_session fixture creates the expected test data."""
    session = query_session
    assert session.query(Model).count() == 2
    assert session.query(Machine).count() == 2
    assert session.query(Benchmark).count() == 5
    assert session.query(Result).count() >= 10


class TestListBenchmarks:
    """TDD: list_benchmarks(query_session, ...)"""

    def test_list_all(self, query_session):
        """No filters returns all benchmarks."""
        result = list_benchmarks(query_session)
        assert result.total_count == 5
        assert len(result.items) == 5

    def test_filter_by_model(self, query_session):
        """Filter by model_name returns matching benchmarks."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(model_name="llama"))
        assert result.total_count > 0
        for item in result.items:
            assert "llama" in item.model_name.lower() or "llama" in item.model_slug.lower()

    def test_filter_by_provider(self, query_session):
        """Filter by provider_name."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(provider_name="openai"))
        assert result.total_count > 0
        for item in result.items:
            assert item.provider_name == "openai"

    def test_filter_by_machine(self, query_session):
        """Filter by machine_hostname."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(machine_hostname="gpu-server-2"))
        assert result.total_count > 0
        for item in result.items:
            assert item.hostname == "gpu-server-2"

    def test_filter_by_date_range(self, query_session):
        """Filter by date range."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(
            date_start=datetime(2026, 5, 1, tzinfo=timezone.utc)))
        assert result.total_count > 0
        for item in result.items:
            # Compare dates only to avoid naive/aware mismatch
            assert item.started_at.date() >= datetime(2026, 5, 1, tzinfo=timezone.utc).date()

    def test_filter_by_status(self, query_session):
        """Filter by benchmark status."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(status="running"))
        assert result.total_count > 0
        for item in result.items:
            assert item.status == "running"

    def test_multiple_filters(self, query_session):
        """Combine filters."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(
            provider_name="vllm", status="completed"))
        assert result.total_count > 0
        for item in result.items:
            assert item.provider_name == "vllm"
            assert item.status == "completed"

    def test_pagination_offset(self, query_session):
        """offset skips N records."""
        all_result = list_benchmarks(query_session, limit=50)
        offset_result = list_benchmarks(query_session, offset=2, limit=50)
        assert len(offset_result.items) == len(all_result.items) - 2

    def test_pagination_limit(self, query_session):
        """limit restricts records."""
        result = list_benchmarks(query_session, limit=2)
        assert len(result.items) <= 2

    def test_pagination_total_count(self, query_session):
        """total_count reflects unfiltered count."""
        result = list_benchmarks(query_session, limit=2)
        assert result.total_count == 5
        assert len(result.items) == 2

    def test_sort_by_default(self, query_session):
        """Default sort is started_at DESC."""
        result = list_benchmarks(query_session)
        dates = [item.started_at for item in result.items]
        assert dates == sorted(dates, reverse=True)

    def test_sort_by_custom_field(self, query_session):
        """Sort by throughput_tps ASC."""
        result = list_benchmarks(query_session, sort_by="throughput_tps", sort_order="asc")
        vals = [item.throughput_tps for item in result.items]
        vals = [v for v in vals if v is not None]
        if vals:
            assert vals == sorted(vals)

    def test_empty_result(self, query_session):
        """No match returns empty."""
        result = list_benchmarks(query_session, filters=BenchmarkFilters(model_name="DOES_NOT_EXIST"))
        assert result.total_count == 0
        assert result.items == []

    def test_invalid_sort_field(self, query_session):
        """Invalid sort_by raises ValueError."""
        with pytest.raises(ValueError):
            list_benchmarks(query_session, sort_by="not_a_column")


class TestCompareRuns:
    """TDD: compare_runs(query_session, run_ids)"""

    def test_compare_two_runs(self, query_session):
        """Pass 2 valid run_ids, returns 2 BenchmarkDetail items."""
        bms = query_session.execute(select(Benchmark).limit(2)).scalars().all()
        run_ids = [b.run_id for b in bms]
        result = compare_runs(query_session, run_ids)
        assert len(result) == 2
        assert result[0].run_id in run_ids
        assert result[1].run_id in run_ids

    def test_compare_three_runs(self, query_session):
        """Pass 3 valid run_ids."""
        bms = query_session.execute(select(Benchmark).limit(3)).scalars().all()
        run_ids = [b.run_id for b in bms]
        result = compare_runs(query_session, run_ids)
        assert len(result) == 3

    def test_compare_four_runs(self, query_session):
        """Pass 4 valid run_ids."""
        bms = query_session.execute(select(Benchmark).limit(4)).scalars().all()
        run_ids = [b.run_id for b in bms]
        result = compare_runs(query_session, run_ids)
        assert len(result) == 4

    def test_compare_includes_result_data(self, query_session):
        """Each BenchmarkDetail includes results list."""
        bms = query_session.execute(select(Benchmark).limit(2)).scalars().all()
        run_ids = [b.run_id for b in bms]
        result = compare_runs(query_session, run_ids)
        for detail in result:
            assert isinstance(detail.results, list)
            if detail.results:
                assert isinstance(detail.results[0], ResultRow)

    def test_compare_rejects_single_run(self, query_session):
        """ValueError if < 2 run_ids."""
        with pytest.raises(ValueError):
            compare_runs(query_session, ["only-one"])

    def test_compare_rejects_five_runs(self, query_session):
        """ValueError if > 4 run_ids."""
        with pytest.raises(ValueError):
            compare_runs(query_session, ["a", "b", "c", "d", "e"])

    def test_compare_fields_match_summary(self, query_session):
        """BenchmarkDetail includes all BenchmarkSummary fields."""
        bms = query_session.execute(select(Benchmark).limit(2)).scalars().all()
        run_ids = [b.run_id for b in bms]
        result = compare_runs(query_session, run_ids)
        detail = result[0]
        assert detail.model_name is not None
        assert detail.model_slug is not None
        assert detail.provider_name is not None
        assert detail.hostname is not None
        assert detail.status is not None
        assert detail.run_id == run_ids[0]


class TestTimeseries:
    """TDD: timeseries(query_session, ...)"""

    def test_timeseries_benchmark_level(self, query_session):
        """Returns points with per-benchmark metrics."""
        points = timeseries(query_session, metric="throughput_tps", level="benchmark")
        assert len(points) > 0
        for p in points:
            assert isinstance(p.date, datetime)
            assert isinstance(p.value, float)
            assert p.label == "throughput_tps"

    def test_timeseries_result_level(self, query_session):
        """Returns points with per-Result metrics."""
        points = timeseries(query_session, metric="tokens_per_second", level="result")
        assert len(points) > 0
        for p in points:
            assert isinstance(p.date, datetime)
            assert isinstance(p.value, float)
            assert p.run_id is not None

    def test_timeseries_filter_by_model(self, query_session):
        """Only returns benchmarks for matching model (slug or name)."""
        points = timeseries(query_session, model="gpt-4o-mini", metric="throughput_tps", level="benchmark")
        assert len(points) > 0

    def test_timeseries_filter_by_provider(self, query_session):
        """Only returns for matching provider."""
        vllm_count = len(timeseries(query_session, provider="vllm", metric="throughput_tps", level="benchmark"))
        openai_count = len(timeseries(query_session, provider="openai", metric="throughput_tps", level="benchmark"))
        assert vllm_count > 0
        assert openai_count > 0

    def test_timeseries_filter_by_date(self, query_session):
        """Respects date_start/date_end."""
        points = timeseries(
            query_session,
            date_start=datetime(2026, 5, 1, tzinfo=timezone.utc),
            metric="throughput_tps",
            level="benchmark",
        )
        for p in points:
            assert p.date >= datetime(2026, 5, 1, tzinfo=timezone.utc)

    def test_timeseries_empty_range(self, query_session):
        """Empty date range returns []."""
        points = timeseries(
            query_session,
            date_start=datetime(2099, 1, 1, tzinfo=timezone.utc),
            metric="throughput_tps",
            level="benchmark",
        )
        assert points == []

    def test_timeseries_sort_by_date_asc(self, query_session):
        """Results ordered by date ASC."""
        points = timeseries(query_session, metric="throughput_tps", level="benchmark")
        dates = [p.date for p in points]
        assert dates == sorted(dates)

    def test_timeseries_invalid_metric(self, query_session):
        """Invalid metric raises ValueError."""
        with pytest.raises(ValueError):
            timeseries(query_session, metric="not_a_column")

    def test_timeseries_invalid_level(self, query_session):
        """Invalid level raises ValueError."""
        with pytest.raises(ValueError):
            timeseries(query_session, level="invalid")