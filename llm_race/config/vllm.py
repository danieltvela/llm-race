"""VLLM provider — OpenAI-compatible chat completions API.

vLLM exposes an API that mirrors the OpenAI chat format with a few
extensions (e.g. ``stream_options`` for correct token accounting in
streaming mode, ``reasoning`` field for Qwen3-style models).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict
from typing import Any

import httpx

from llm_race.config.base import Provider, StreamResult
from llm_race.utils.sse import iter_sse_events
from llm_race.utils.timing import compute_itl_stats


class VLLMProvider(Provider):
    """Provider for vLLM OpenAI-compatible endpoints.

    Args:
        base_url: Root URL of the vLLM server (e.g. ``http://localhost:8000/v1``).
        api_key: Optional API key (Bearer token).
        timeout: Default HTTP request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str | None = None, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def stream_complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_p: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """Send a streaming chat completion via the vLLM API.

        Returns a dict with the same keys as ``StreamResult``.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        prompt_length = sum(len(str(m.get("content", "")).split()) for m in messages)
        start = time.monotonic()
        ttft: float | None = None
        prev_token_time: float | None = None
        inter_token_times: list[float] = []
        completion_tokens = 0

        async def _do_stream(cl: httpx.AsyncClient) -> None:
            nonlocal ttft, prev_token_time, inter_token_times, completion_tokens
            async with cl.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    await response.aread()
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

                async for chunk in iter_sse_events(response):
                    # Extract usage first — it may arrive on a chunk with empty
                    # choices (vLLM final usage frame).
                    usage = chunk.get("usage")
                    if usage:
                        completion_tokens = usage.get("completion_tokens", completion_tokens)
                        if not chunk.get("choices"):
                            continue

                    choices = chunk.get("choices")
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    has_content = delta.get("content") or delta.get("reasoning")

                    if has_content:
                        now = time.monotonic()
                        if ttft is None:
                            ttft = now - start
                            prev_token_time = now
                        else:
                            inter_token_times.append(now - (prev_token_time or now))
                            prev_token_time = now
                        completion_tokens += 1

        try:
            if client is not None:
                await _do_stream(client)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as cl:
                    await _do_stream(cl)
        except (asyncio.TimeoutError, httpx.TimeoutException):
            status = "error"
            error_message = "Timeout"
        except RuntimeError as exc:
            status = "error"
            error_message = str(exc)[:200]
        except Exception as exc:
            status = "error"
            error_message = str(exc)[:200]
        else:
            status = "success"
            error_message = None

        e2e = time.monotonic() - start
        itl_stats = compute_itl_stats(inter_token_times)
        tps: float | None = None
        if e2e > 0 and completion_tokens > 0:
            tps = completion_tokens / e2e

        return asdict(StreamResult(
            status=status,
            error_message=error_message,
            ttft=ttft,
            e2e_latency=e2e,
            inter_token_latencies=list(inter_token_times),
            completion_tokens=completion_tokens,
            tokens_per_second=tps,
            itl_mean=itl_stats["mean"],
            itl_p50=itl_stats["p50"],
            itl_p95=itl_stats["p95"],
            itl_p99=itl_stats["p99"],
            prompt_length=prompt_length,
        ))
