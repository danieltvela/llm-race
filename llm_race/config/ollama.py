"""Ollama provider — OpenAI-compatible chat completions API.

Ollama exposes an OpenAI-compatible ``/v1/chat/completions`` endpoint.
Unlike vLLM, Ollama does **not** return ``usage`` in streaming mode and
may omit it in non-streaming mode depending on configuration.  We therefore
count completion tokens client-side by splitting generated content on
whitespace as a fallback.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict
from typing import Any

import httpx

from llm_race.config.base import Provider, StreamResult
from llm_race.utils.sse import iter_sse_events
from llm_race.utils.timing import compute_itl_stats


class OllamaProvider(Provider):
    """Provider for Ollama OpenAI-compatible endpoints.

    Args:
        base_url: Root URL of the Ollama server (default ``http://localhost:11434/v1``).
        api_key: Optional API key. Falls back to ``OLLAMA_API_KEY`` env var.
        timeout: Default HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")
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
        """Send a streaming chat completion via the Ollama API.

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
                    choices = chunk.get("choices")
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content") or ""
                    reasoning = delta.get("reasoning") or ""
                    text = content + reasoning

                    if text:
                        now = time.monotonic()
                        if ttft is None:
                            ttft = now - start
                            prev_token_time = now
                        else:
                            inter_token_times.append(now - (prev_token_time or now))
                            prev_token_time = now
                        completion_tokens += len(text.split())

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

        return asdict(
            StreamResult(
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
            )
        )

    async def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_p: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """Send a non-streaming chat completion via the Ollama API.

        Returns a dict with the same keys as ``StreamResult``.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        prompt_length = sum(len(str(m.get("content", "")).split()) for m in messages)
        start = time.monotonic()
        completion_tokens = 0

        try:
            if client is not None:
                response = await client.post(url, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as cl:
                    response = await cl.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

            data = response.json()
            usage = data.get("usage")
            if usage:
                completion_tokens = usage.get("completion_tokens", 0)
            else:
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    text = msg.get("content", "") or msg.get("reasoning", "")
                    completion_tokens = len(text.split())
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
        tps: float | None = None
        if e2e > 0 and completion_tokens > 0:
            tps = completion_tokens / e2e

        return asdict(
            StreamResult(
                status=status,
                error_message=error_message,
                ttft=None,
                e2e_latency=e2e,
                inter_token_latencies=[],
                completion_tokens=completion_tokens,
                tokens_per_second=tps,
                itl_mean=None,
                itl_p50=None,
                itl_p95=None,
                itl_p99=None,
                prompt_length=prompt_length,
            )
        )
