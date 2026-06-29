"""Workload profiles for LLM benchmarking.

Each profile defines a set of concurrency levels and prompt lengths that
represent a realistic usage pattern. Profiles are registered in a global
dict and retrieved via ``get_workload()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from llm_race.config import DEFAULT_PROMPT_LENGTHS


@dataclass(frozen=True, kw_only=False)
class WorkloadProfile:
    """A reusable description of how to stress-test an LLM endpoint.

    Attributes:
        name: Unique identifier used in DB and CLI.
        description: Human-readable explanation of the workload.
        concurrency_levels: List of concurrent request counts to test.
        default_prompt_lengths: Prompt token lengths for this workload.
        behavior: Short description of the access pattern.
    """

    name: str
    description: str
    concurrency_levels: list[int]
    behavior: str
    default_prompt_lengths: list[int] = field(default_factory=lambda: list(DEFAULT_PROMPT_LENGTHS))


SINGLE_USER: Final = WorkloadProfile(
    name="single-user",
    description="Single request, measure raw latency",
    concurrency_levels=[1],
    default_prompt_lengths=[64, 4096],
    behavior="single request",
)

CHAT: Final = WorkloadProfile(
    name="chat",
    description="Conversational flow with short context exchanges",
    concurrency_levels=[1],
    default_prompt_lengths=[128],
    behavior="conversational (short user messages)",
)

MULTI_AGENT: Final = WorkloadProfile(
    name="multi-agent",
    description="Multiple independent agents running in parallel",
    concurrency_levels=[2, 8],
    default_prompt_lengths=[512, 2048],
    behavior="independent parallel agents (user queries + tool context)",
)

HIGH_THROUGHPUT: Final = WorkloadProfile(
    name="high-throughput",
    description="Many users hitting the endpoint simultaneously",
    concurrency_levels=[32, 64, 128],
    default_prompt_lengths=[64, 256, 1024],
    behavior="constant concurrent load",
)

STRESS: Final = WorkloadProfile(
    name="stress",
    description="Maximum concurrency until degradation",
    concurrency_levels=[256, 512],
    default_prompt_lengths=[1024, 4096],
    behavior="degradation testing",
)

WORKLOAD_REGISTRY: Final[dict[str, WorkloadProfile]] = {
    p.name: p
    for p in (SINGLE_USER, CHAT, MULTI_AGENT, HIGH_THROUGHPUT, STRESS)
}


def get_workload(name: str) -> WorkloadProfile:
    """Look up a workload profile by name.

    Raises:
        ValueError: If *name* is not a registered profile.
    """
    if name not in WORKLOAD_REGISTRY:
        raise ValueError(
            f"Unknown workload profile: {name!r}. "
            f"Valid profiles: {list(WORKLOAD_REGISTRY.keys())}"
        )
    return WORKLOAD_REGISTRY[name]