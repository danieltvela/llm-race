"""SQLAlchemy 2.0 ORM models for benchmark data."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Engine,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.orm.session import Session

from llm_race.config import DB_PATH

logger = logging.getLogger(__name__)


def uuid4_string() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Model(Base):
    """Represents an LLM model (name, version, quantization, provider)."""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantization: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            "quantization",
            "provider_name",
            name="uq_model",
        ),
    )

    benchmarks: Mapped[list[Benchmark]] = relationship(
        back_populates="model", lazy="selectin"
    )


class Machine(Base):
    """Hardware specs for a benchmarking machine."""

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gpu: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gpu_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ram_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    driver_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    python_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("hostname", name="uq_machine"),
    )

    benchmarks: Mapped[list[Benchmark]] = relationship(
        back_populates="machine", lazy="selectin"
    )


class Benchmark(Base):
    """A single benchmark run with full metrics."""

    __tablename__ = "benchmarks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=uuid4_string, index=True
    )
    model_id: Mapped[int] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), nullable=False
    )
    workload_profile: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_size: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    prompt_text_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    top_p: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    wall_clock_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_requests: Mapped[int] = mapped_column(default=0)
    successful_requests: Mapped[int] = mapped_column(default=0)
    failed_requests: Mapped[int] = mapped_column(default=0)
    throughput_rps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    throughput_tps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e2e_mean_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e2e_p50_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e2e_p90_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e2e_p99_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ttft_mean_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ttft_p50_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ttft_p90_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ttft_p99_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_mean_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_p50_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_p90_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_p99_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_per_token: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_p50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_p90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_p99: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    model: Mapped[Model] = relationship(back_populates="benchmarks")
    machine: Mapped[Machine] = relationship(back_populates="benchmarks")
    results: Mapped[list[Result]] = relationship(
        back_populates="benchmark", cascade="all, delete-orphan", lazy="selectin"
    )


class Result(Base):
    """Per-request result inside a benchmark run."""

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    benchmark_id: Mapped[int] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ttft_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    e2e_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    tokens_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_p50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_p90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itl_p99: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_per_token: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "benchmark_id",
            "request_id",
            name="uq_result_benchmark_request",
        ),
    )

    benchmark: Mapped[Benchmark] = relationship(back_populates="results")


def init_db(db_path: str | Path = DB_PATH) -> tuple[Engine, sessionmaker[Session]]:
    """Initialize the database, creating tables if they don't exist.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A tuple of (engine, session_factory).
    """
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_wal(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    logger.info("Database initialized at %s", db_path)
    return engine, session_factory