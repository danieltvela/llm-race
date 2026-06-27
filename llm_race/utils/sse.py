"""Shared SSE (Server-Sent Events) parser for OpenAI-compatible providers.

Providers that speak the OpenAI streaming protocol (vLLM, OpenAI, Together,
Fireworks, etc.) produce ``data: {...}`` lines delimited by blank lines.
This module provides a single reusable generator so each provider doesn't
duplicate the parsing boilerplate.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


async def iter_sse_events(response: httpx.Response) -> AsyncIterator[dict]:
    """Yield parsed JSON chunks from a streaming SSE response.

    Skips keep-alive (empty) lines and lines without the ``data: `` prefix.
    Stops when the ``[DONE]`` sentinel is received, after which the caller
    should stop reading.

    Args:
        response: An active ``httpx.Response`` opened with ``cl.stream(...)``.

    Yields:
        ``dict`` — the JSON body of each ``data: {...}`` event.
    """
    async for line in response.aiter_lines():
        line = line.strip()
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            yield json.loads(data_str)
        except json.JSONDecodeError:
            continue
