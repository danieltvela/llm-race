"""Unit tests for the database models."""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from llm_race.db.models import (
    Base,
    Benchmark,
    Machine,
    Model,
    Result,
    init_db,
)


@pytest.fixture
def db_session():
    """Create a fresh in-memory database for each test."""
    tmp = Path(tempfile.mktemp(suffix=".db"))
    engine, sf = init_db(tmp)
    session = sf()
    yield session
    session.close()
    engine.dispose()
    os.unlink(tmp)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_minimal_model(session: object) -> Model:
    """Create and return a minimal Model record."""
    m = Model(
        name="test-model",
        version="1.0",
        quantization="FP8",
        provider_name="vllm",
        context_window=4096,
    )
    session.add(m)
    session.commit()
    return m


def _create_minimal_machine(session: object) -> Machine:
    """Create and return a minimal Machine record."""
    machine = Machine(
        hostname="test-host",
        cpu="Intel Xeon",
        gpu="A100",
        gpu_count=1,
        ram_gb=128.0,
        os="macOS",
        os_version="14.0",
        driver_version="12.0",
        python_version="3.11",
    )
    session.add(machine)
    session.commit()
    return machine


def _create_minimal_benchmark(
    session: object,
    model: Model,
    machine: Machine,
    run_id: str | None = None,
) -> Benchmark:
    """Create and return a minimal Benchmark record."""
    b = Benchmark(
        run_id=run_id or str(uuid.uuid4()),
        model_id=model.id,
        machine_id=machine.id,
        workload_profile="single-user",
        prompt_size="medium",
        concurrency=1,
        max_tokens=256,
        temperature=0.0,
        top_p=1.0,
        started_at=datetime.utcnow(),
        total_requests=1,
        successful_requests=1,
        failed_requests=0,
        status="completed",
    )
    session.add(b)
    session.commit()
    return b


# ---------------------------------------------------------------------------
# Tests: init_db
# ---------------------------------------------------------------------------

def test_init_db_creates_tables(db_session) -> None:
    """Verify all 4 tables are created."""
    inspector = inspect(db_session.get_bind())
    tables = set(inspector.get_table_names())
    assert tables == {"models", "machines", "benchmarks", "results"}


# ---------------------------------------------------------------------------
# Tests: Model
# ---------------------------------------------------------------------------

def test_create_model(db_session) -> None:
    """Create and verify a Model record."""
    model = Model(
        name="test-model",
        version="1.0",
        quantization="FP8",
        provider_name="vllm",
        context_window=4096,
    )
    db_session.add(model)
    db_session.commit()

    assert model.id is not None
    assert model.name == "test-model"
    assert model.version == "1.0"
    assert model.quantization == "FP8"
    assert model.provider_name == "vllm"
    assert model.context_window == 4096
    assert model.created_at is not None


def test_model_unique_constraint(db_session) -> None:
    """Verify duplicate Model raises IntegrityError."""
    data = dict(
        name="dup",
        version="1",
        quantization="FP8",
        provider_name="test",
    )
    db_session.add(Model(**data))
    db_session.commit()

    db_session.add(Model(**data))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests: Machine
# ---------------------------------------------------------------------------

def test_create_machine(db_session) -> None:
    """Create and verify a Machine record."""
    machine = Machine(
        hostname="test-host",
        cpu="Intel Xeon",
        gpu="A100",
        gpu_count=1,
        ram_gb=128.0,
        os="macOS",
        os_version="14.0",
        driver_version="12.0",
        python_version="3.11",
    )
    db_session.add(machine)
    db_session.commit()

    assert machine.id is not None
    assert machine.hostname == "test-host"
    assert machine.cpu == "Intel Xeon"
    assert machine.gpu == "A100"
    assert machine.gpu_count == 1
    assert machine.ram_gb == 128.0
    assert machine.created_at is not None


def test_machine_unique_constraint(db_session) -> None:
    """Verify duplicate hostname raises IntegrityError."""
    db_session.add(Machine(hostname="dup-host"))
    db_session.commit()

    db_session.add(Machine(hostname="dup-host"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Tests: Benchmark
# ---------------------------------------------------------------------------

def test_create_benchmark(db_session) -> None:
    """Create a Benchmark with FK to Model and Machine."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    run_id = str(uuid.uuid4())

    benchmark = _create_minimal_benchmark(db_session, model, machine, run_id)

    assert benchmark.id is not None
    assert benchmark.run_id == run_id
    assert benchmark.model_id == model.id
    assert benchmark.machine_id == machine.id
    assert benchmark.workload_profile == "single-user"
    assert benchmark.prompt_size == "medium"
    assert benchmark.concurrency == 1
    assert benchmark.max_tokens == 256
    assert benchmark.temperature == 0.0
    assert benchmark.top_p == 1.0
    assert benchmark.started_at is not None
    assert benchmark.total_requests == 1
    assert benchmark.successful_requests == 1
    assert benchmark.failed_requests == 0
    assert benchmark.status == "completed"


def test_benchmark_run_id_uuid(db_session) -> None:
    """Verify run_id is a valid UUID4 string when auto-generated."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)

    benchmark = Benchmark(
        model_id=model.id,
        machine_id=machine.id,
        workload_profile="single-user",
        prompt_size="medium",
        concurrency=1,
        max_tokens=256,
        temperature=0.0,
        top_p=1.0,
        started_at=datetime.utcnow(),
    )
    db_session.add(benchmark)
    db_session.commit()

    # Validate it parses as UUID4
    parsed = uuid.UUID(benchmark.run_id, version=4)
    assert str(parsed) == benchmark.run_id


def test_benchmark_defaults(db_session) -> None:
    """Verify default values (status='running', total_requests=0, etc.)."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)

    benchmark = Benchmark(
        model_id=model.id,
        machine_id=machine.id,
        workload_profile="single-user",
        prompt_size="medium",
        concurrency=1,
        max_tokens=256,
        temperature=0.0,
        top_p=1.0,
        started_at=datetime.utcnow(),
    )
    db_session.add(benchmark)
    db_session.commit()

    assert benchmark.status == "running"
    assert benchmark.total_requests == 0
    assert benchmark.successful_requests == 0
    assert benchmark.failed_requests == 0
    assert benchmark.completed_at is None
    assert benchmark.wall_clock_seconds is None
    assert benchmark.throughput_rps is None
    assert benchmark.throughput_tps is None
    assert benchmark.e2e_mean_ms is None
    assert benchmark.error_message is None
    assert benchmark.created_at is not None


# ---------------------------------------------------------------------------
# Tests: Result
# ---------------------------------------------------------------------------

def test_create_result(db_session) -> None:
    """Create a Result with FK to Benchmark."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    benchmark = _create_minimal_benchmark(db_session, model, machine)

    result = Result(
        benchmark_id=benchmark.id,
        request_id=1,
        status="success",
        ttft_ms=10.5,
        e2e_latency_ms=150.0,
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        tokens_per_second=1333.33,
        itl_mean=0.75,
        itl_p50=0.70,
        itl_p90=1.20,
        itl_p99=2.50,
        cost_per_token=0.00001,
    )
    db_session.add(result)
    db_session.commit()

    assert result.id is not None
    assert result.benchmark_id == benchmark.id
    assert result.request_id == 1
    assert result.status == "success"
    assert result.ttft_ms == 10.5
    assert result.e2e_latency_ms == 150.0
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 200
    assert result.total_tokens == 300
    assert result.tokens_per_second == 1333.33
    assert result.created_at is not None


def test_result_unique_constraint(db_session) -> None:
    """Verify duplicate (benchmark_id, request_id) raises IntegrityError."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    benchmark = _create_minimal_benchmark(db_session, model, machine)

    db_session.add(Result(
        benchmark_id=benchmark.id,
        request_id=1,
        status="success",
    ))
    db_session.commit()

    db_session.add(Result(
        benchmark_id=benchmark.id,
        request_id=1,
        status="success",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_result_defaults(db_session) -> None:
    """Verify Result default values (prompt_tokens=0, etc.)."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    benchmark = _create_minimal_benchmark(db_session, model, machine)

    result = Result(
        benchmark_id=benchmark.id,
        request_id=42,
        status="success",
    )
    db_session.add(result)
    db_session.commit()

    assert result.request_id == 42
    assert result.status == "success"
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0
    assert result.total_tokens == 0
    assert result.ttft_ms is None
    assert result.e2e_latency_ms is None
    assert result.tokens_per_second is None
    assert result.itl_mean is None
    assert result.itl_p50 is None
    assert result.itl_p90 is None
    assert result.itl_p99 is None
    assert result.error_message is None
    assert result.cost_per_token is None
    assert result.created_at is not None


# ---------------------------------------------------------------------------
# Tests: Relationships
# ---------------------------------------------------------------------------

def test_model_benchmark_relationship(db_session) -> None:
    """Verify Model.benchmarks back_populates."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    _create_minimal_benchmark(db_session, model, machine)
    _create_minimal_benchmark(db_session, model, machine)

    # Refresh to ensure relationship is loaded
    db_session.refresh(model)
    assert len(model.benchmarks) == 2
    assert all(b.model_id == model.id for b in model.benchmarks)


def test_machine_benchmark_relationship(db_session) -> None:
    """Verify Machine.benchmarks back_populates."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    _create_minimal_benchmark(db_session, model, machine)
    _create_minimal_benchmark(db_session, model, machine)

    db_session.refresh(machine)
    assert len(machine.benchmarks) == 2
    assert all(b.machine_id == machine.id for b in machine.benchmarks)


def test_benchmark_result_relationship(db_session) -> None:
    """Verify Benchmark.results back_populates."""
    model = _create_minimal_model(db_session)
    machine = _create_minimal_machine(db_session)
    benchmark = _create_minimal_benchmark(db_session, model, machine)

    db_session.add(Result(
        benchmark_id=benchmark.id,
        request_id=1,
        status="success",
    ))
    db_session.add(Result(
        benchmark_id=benchmark.id,
        request_id=2,
        status="success",
    ))
    db_session.add(Result(
        benchmark_id=benchmark.id,
        request_id=3,
        status="error",
        error_message="timeout",
    ))
    db_session.commit()

    db_session.refresh(benchmark)
    assert len(benchmark.results) == 3
    assert all(r.benchmark_id == benchmark.id for r in benchmark.results)
    assert any(r.status == "error" for r in benchmark.results)
