"""Unit tests for llm_race/db/saver.py."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from llm_race.bench.runner import RequestMetrics, ScenarioResult
from llm_race.db.models import Base, Machine, Model, Benchmark, Result
from llm_race.db.saver import save_benchmark_run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    """Create an in-memory SQLite session with all tables."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


@pytest.fixture
def system_info() -> dict:
    """Minimal system info dict matching SystemInfo.to_dict() keys."""
    return {
        "hostname": "test-host",
        "cpu": "Apple M3",
        "gpu": "Apple M3",
        "gpu_count": 1,
        "ram_gb": 16.0,
        "os": "Darwin",
        "os_version": "24.0",
        "driver_version": None,
        "python_version": "3.12.0",
    }


@pytest.fixture
def scenario_result() -> ScenarioResult:
    return ScenarioResult(
        concurrency=1,
        prompt_length=512,
        total_requests=3,
        successful_requests=3,
        failed_requests=0,
        e2e_mean=0.5,
        e2e_p50=0.4,
        e2e_p95=0.6,
        e2e_p99=0.7,
        e2e_max=0.8,
        ttft_mean=0.1,
        ttft_p50=0.09,
        ttft_p95=0.15,
        ttft_p99=0.18,
        throughput_rps=6.0,
        throughput_tps=120.0,
        itl_mean=0.02,
        itl_p50=0.015,
        itl_p95=0.03,
        wall_clock_seconds=0.5,
    )


@pytest.fixture
def request_metrics_list() -> list[RequestMetrics]:
    return [
        RequestMetrics(
            request_id=0,
            prompt_length=512,
            concurrency_level=1,
            status="success",
            ttft=0.1,
            e2e_latency=0.4,
            inter_token_latencies=[0.01, 0.02, 0.015],
            prompt_tokens=512,
            completion_tokens=100,
            total_tokens=612,
            tokens_per_second=250.0,
        ),
        RequestMetrics(
            request_id=1,
            prompt_length=512,
            concurrency_level=1,
            status="success",
            ttft=0.12,
            e2e_latency=0.6,
            inter_token_latencies=[0.025, 0.018, 0.03],
            prompt_tokens=512,
            completion_tokens=200,
            total_tokens=712,
            tokens_per_second=333.33,
        ),
    ]


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_save_single_scenario(session, system_info, scenario_result, request_metrics_list):
    """Verify a single scenario is saved with correct field mapping."""
    now = datetime.utcnow()
    scenarios = [(scenario_result, request_metrics_list, now)]

    result = save_benchmark_run(
        session=session,
        run_id="test-run-001",
        provider_type="test_provider",
        model_name="test-model",
        workload_profile="single-user",
        system_info=system_info,
        max_tokens=512,
        temperature=0.7,
        top_p=0.9,
        scenarios=scenarios,
    )

    # Check Benchmark row
    benchmarks = session.execute(select(Benchmark)).scalars().all()
    assert len(benchmarks) == 1
    b = benchmarks[0]
    assert b.run_id == "test-run-001"
    assert b.concurrency == 1
    assert b.prompt_size == "512"
    assert b.prompt_token_count == 512
    assert b.status == "success"
    assert b.workload_profile == "single-user"
    assert b.total_requests == 3
    assert b.successful_requests == 3
    assert b.failed_requests == 0
    assert b.e2e_mean_ms == 500.0  # 0.5s * 1000

    # Check Result rows
    results = session.execute(select(Result)).scalars().all()
    assert len(results) == 2
    assert results[0].request_id == 0
    assert results[1].request_id == 1
    assert results[0].ttft_ms == 100.0  # 0.1s * 1000

    # Check return value
    assert result == [b.id]


def test_save_multiple_scenarios(session, system_info, scenario_result, request_metrics_list):
    """Verify multiple scenarios create separate Benchmark rows."""
    now = datetime.utcnow()
    sc1 = ScenarioResult(concurrency=1, prompt_length=512, total_requests=2,
                          successful_requests=2, failed_requests=0,
                          e2e_mean=0.3, throughput_rps=6.0, throughput_tps=60.0,
                          wall_clock_seconds=0.5)
    sc2 = ScenarioResult(concurrency=8, prompt_length=1024, total_requests=16,
                          successful_requests=14, failed_requests=2,
                          e2e_mean=1.2, throughput_rps=12.0, throughput_tps=120.0,
                          wall_clock_seconds=0.3)

    scenarios = [
        (sc1, request_metrics_list, now),
        (sc2, request_metrics_list, now),
    ]

    result = save_benchmark_run(
        session=session,
        run_id="test-run-002",
        provider_type="test_provider",
        model_name="test-model",
        workload_profile=None,
        system_info=system_info,
        max_tokens=256,
        temperature=0.0,
        top_p=1.0,
        scenarios=scenarios,
    )

    benchmarks = session.execute(select(Benchmark).order_by(Benchmark.concurrency)).scalars().all()
    assert len(benchmarks) == 2
    assert benchmarks[0].concurrency == 1
    assert benchmarks[0].prompt_size == "512"
    assert benchmarks[1].concurrency == 8
    assert benchmarks[1].prompt_size == "1024"
    assert benchmarks[1].status == "partial"
    assert len(result) == 2


def test_find_or_create_model(session, system_info, scenario_result, request_metrics_list):
    """Verify model find-or-create prevents duplicates."""
    now = datetime.utcnow()
    scenarios = [(scenario_result, request_metrics_list, now)]

    # First call
    save_benchmark_run(session=session, run_id="run-1", provider_type="vllm",
        model_name="gpt-3.5", workload_profile=None, system_info=system_info,
        max_tokens=256, temperature=0.0, top_p=1.0, scenarios=scenarios)

    # Second call with same model/provider
    save_benchmark_run(session=session, run_id="run-2", provider_type="vllm",
        model_name="gpt-3.5", workload_profile=None, system_info=system_info,
        max_tokens=256, temperature=0.0, top_p=1.0, scenarios=scenarios)

    models = session.execute(select(Model)).scalars().all()
    assert len(models) == 1
    assert models[0].name == "gpt-3.5"
    assert models[0].provider_name == "vllm"


def test_find_or_create_machine(session, system_info, scenario_result, request_metrics_list):
    """Verify machine find-or-create prevents duplicates."""
    now = datetime.utcnow()
    scenarios = [(scenario_result, request_metrics_list, now)]

    # First call
    save_benchmark_run(session=session, run_id="run-1", provider_type="vllm",
        model_name="test", workload_profile=None, system_info=system_info,
        max_tokens=256, temperature=0.0, top_p=1.0, scenarios=scenarios)

    # Second call with same hostname
    save_benchmark_run(session=session, run_id="run-2", provider_type="vllm",
        model_name="test", workload_profile=None, system_info=system_info,
        max_tokens=256, temperature=0.0, top_p=1.0, scenarios=scenarios)

    machines = session.execute(select(Machine)).scalars().all()
    assert len(machines) == 1
    assert machines[0].hostname == "test-host"


def test_empty_scenarios(session, system_info):
    """Verify empty scenarios produce no rows."""
    result = save_benchmark_run(
        session=session, run_id="empty", provider_type="test",
        model_name="test", workload_profile=None, system_info=system_info,
        max_tokens=256, temperature=0.0, top_p=1.0, scenarios=[],
    )
    assert result == []
    assert session.execute(select(Benchmark)).scalars().all() == []
    assert session.execute(select(Result)).scalars().all() == []


def test_db_failure_handling(session, system_info, scenario_result, request_metrics_list):
    """Verify DB failure is caught and does not crash."""
    now = datetime.utcnow()
    scenarios = [(scenario_result, request_metrics_list, now)]

    with patch.object(session, "commit", side_effect=RuntimeError("mock db failure")):
        result = save_benchmark_run(
            session=session, run_id="fail-test", provider_type="test",
            model_name="test", workload_profile=None, system_info=system_info,
            max_tokens=256, temperature=0.0, top_p=1.0, scenarios=scenarios,
        )
    assert result == []