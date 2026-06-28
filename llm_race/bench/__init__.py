"""Benchmark runner package. Workload profiles are in ``workloads``."""

from llm_race.bench.workloads import (
    WorkloadProfile,
    WORKLOAD_REGISTRY,
    get_workload,
    SINGLE_USER,
    CHAT,
    MULTI_AGENT,
    HIGH_THROUGHPUT,
    STRESS,
)

__all__ = [
    "WorkloadProfile",
    "WORKLOAD_REGISTRY",
    "get_workload",
    "SINGLE_USER",
    "CHAT",
    "MULTI_AGENT",
    "HIGH_THROUGHPUT",
    "STRESS",
]