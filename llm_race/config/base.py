"""Abstract provider interface for LLM Race.

Every LLM provider implements Provider.stream_complete() and returns
a dict with StreamResult fields (produced via asdict(StreamResult(...))).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

import httpx


@dataclass
class StreamResult:
    """Normalized metrics for a single streaming completion request."""

    status: str
    error_message: str | None
    ttft: float | None
    e2e_latency: float | None
    inter_token_latencies: list[float]
    completion_tokens: int
    tokens_per_second: float | None
    itl_mean: float | None
    itl_p50: float | None
    itl_p95: float | None
    itl_p99: float | None
    prompt_length: int


class Provider(ABC):
    """Abstract base for all LLM providers.

    Each subclass defines its own __init__ signature and implements
    stream_complete() which returns a dict matching StreamResult's fields.
    """

    timeout: int

    @abstractmethod
    async def stream_complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_p: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """Send a streaming completion and return normalized metrics.

        Returns:
            A dict with the same keys as StreamResult. Build via
            ``asdict(StreamResult(...))``.
        """
