"""Unit tests for VLLMProvider.complete() and OllamaProvider."""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from llm_race.config.ollama import OllamaProvider
from llm_race.config.vllm import VLLMProvider
from llm_race.config.mlx_lm import MLXLMProvider
from llm_race.config.lm_studio import LMStudioProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    """Build a MagicMock that mimics httpx.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.text = text
    return mock


# ---------------------------------------------------------------------------
# Tests: complete()
# ---------------------------------------------------------------------------

class TestVLLMProvider:
    """Tests for VLLMProvider.complete()."""

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        """Mock a 200 response with valid JSON; verify StreamResult shape."""
        provider = VLLMProvider(base_url="http://localhost:8000/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "Hello world"}}],
                "usage": {"completion_tokens": 42},
            },
        ))

        result = await provider.complete(
            model="test-model",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=64,
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["completion_tokens"] == 42
        assert result["ttft"] is None
        assert result["inter_token_latencies"] == []
        assert result["itl_mean"] is None
        assert result["itl_p50"] is None
        assert result["itl_p95"] is None
        assert result["itl_p99"] is None
        assert result["e2e_latency"] > 0
        assert result["tokens_per_second"] > 0
        assert result["prompt_length"] > 0

        # Verify the POST call was correct
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == "http://localhost:8000/v1/chat/completions"
        call_json = call_kwargs[1]["json"]
        assert call_json["model"] == "test-model"
        assert "stream" not in call_json  # no stream key for non-streaming

    @pytest.mark.asyncio
    async def test_complete_http_error(self) -> None:
        """Mock a 400 response; verify status == 'error'."""
        provider = VLLMProvider(base_url="http://localhost:8000/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=400,
            json_data={"error": {"message": "Bad model"}},
            text="Bad model",
        ))

        result = await provider.complete(
            model="bad-model",
            messages=[{"role": "user", "content": "test"}],
            client=mock_client,
        )

        assert result["status"] == "error"
        assert result["error_message"] is not None
        assert "HTTP 400" in result["error_message"]

    @pytest.mark.asyncio
    async def test_complete_timeout(self) -> None:
        """Simulate asyncio.TimeoutError; verify status == 'error' and message."""
        provider = VLLMProvider(base_url="http://localhost:8000/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=asyncio.TimeoutError("timed out"))

        result = await provider.complete(
            model="slow-model",
            messages=[{"role": "user", "content": "test"}],
            client=mock_client,
        )

        assert result["status"] == "error"
        assert result["error_message"] == "Timeout"

    @pytest.mark.asyncio
    async def test_complete_api_key_from_env(self) -> None:
        """When api_key param is omitted, headers should not include Authorization."""
        # Without api_key — no Authorization header
        provider_no_key = VLLMProvider(base_url="http://localhost:8000/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=200,
            json_data={"usage": {"completion_tokens": 1}},
        ))

        await provider_no_key.complete(
            model="test",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs[1]["headers"]
        assert "Authorization" not in headers

        # With api_key — Authorization header present
        provider_with_key = VLLMProvider(
            base_url="http://localhost:8000/v1",
            api_key="sk-test-key-123",
        )

        mock_client2 = MagicMock()
        mock_client2.post = AsyncMock(return_value=_make_mock_response(
            status_code=200,
            json_data={"usage": {"completion_tokens": 1}},
        ))

        await provider_with_key.complete(
            model="test",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client2,
        )

        call_kwargs2 = mock_client2.post.call_args
        headers2 = call_kwargs2[1]["headers"]
        assert headers2["Authorization"] == "Bearer sk-test-key-123"

    @pytest.mark.asyncio
    async def test_complete_no_usage_field(self) -> None:
        """Response without usage field; completion_tokens defaults to 0."""
        provider = VLLMProvider(base_url="http://localhost:8000/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "no usage here"}}],
            },
        ))

        result = await provider.complete(
            model="test",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["completion_tokens"] == 0


# ---------------------------------------------------------------------------
# Tests: LMStudioProvider
# ---------------------------------------------------------------------------


def _make_sse_response(sse_lines: list[str]) -> MagicMock:
    """Build a mock httpx Response that yields *sse_lines* via ``aiter_lines``."""

    async def _aiter_lines():
        for line in sse_lines:
            yield line

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = MagicMock(return_value=_aiter_lines())
    mock_response.aread = AsyncMock(return_value=b"")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


def _make_httpx_stream_context(sse_lines: list[str]) -> MagicMock:
    """Build a mock context manager that httpx.AsyncClient.stream() returns."""
    mock_response = _make_sse_response(sse_lines)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def _sse(*chunks: dict) -> list[str]:
    """Build a list of SSE-formatted lines from JSON dicts."""
    lines: list[str] = []
    for chunk in chunks:
        lines.append(f"data: {json.dumps(chunk)}")
        lines.append("")
    return lines


class TestLMStudioProvider:
    """Tests for ``llm_race.config.lm_studio.LMStudioProvider``."""

    # ------------------------------------------------------------------
    # 1. test_stream_complete_success
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stream_complete_success(self) -> None:
        """Mock SSE streaming with content chunks; verify TTFT, tokens, status."""
        provider = LMStudioProvider(base_url="http://localhost:1234/v1")

        chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " world"}}]},
        ]
        sse_lines = _sse(*chunks)

        mock_client = MagicMock()
        mock_client.stream.return_value = _make_httpx_stream_context(sse_lines)

        result = await provider.stream_complete(
            model="local-model",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["ttft"] is not None
        assert result["ttft"] >= 0
        assert result["completion_tokens"] == 2  # "Hello" + " world" = 2 tokens
        assert result["e2e_latency"] is not None
        assert result["e2e_latency"] >= 0
        assert len(result["inter_token_latencies"]) == 1
        assert result["tokens_per_second"] is not None
        assert result["itl_mean"] is not None

    # ------------------------------------------------------------------
    # 2. test_complete_success
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        """Mock 200 non-streaming response with ``usage.completion_tokens``."""
        provider = LMStudioProvider(base_url="http://localhost:1234/v1")

        mock_response = _make_mock_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "four tokens here now please"}}],
                "usage": {"completion_tokens": 4, "prompt_tokens": 2},
            },
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete(
            model="local-model",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["completion_tokens"] == 4
        assert result["ttft"] is None
        assert result["inter_token_latencies"] == []
        assert result["tokens_per_second"] is not None

    # ------------------------------------------------------------------
    # 3. test_complete_http_error
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_http_error(self) -> None:
        """Mock 400 response; verify ``status == 'error'``."""
        provider = LMStudioProvider(base_url="http://localhost:1234/v1")

        mock_response = _make_mock_response(
            status_code=400,
            json_data={"error": {"message": "Bad Request"}},
            text="Bad Request: invalid model",
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete(
            model="bad-model",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "error"
        assert "HTTP 400" in result["error_message"]

    # ------------------------------------------------------------------
    # 4. test_complete_timeout
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_timeout(self) -> None:
        """Simulate ``asyncio.TimeoutError``; verify ``status == 'error'``."""
        provider = LMStudioProvider(base_url="http://localhost:1234/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=asyncio.TimeoutError("timed out"))

        result = await provider.complete(
            model="local-model",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "error"
        assert result["error_message"] == "Timeout"

    # ------------------------------------------------------------------
    # 5. test_complete_no_usage_fallback
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_no_usage_fallback(self) -> None:
        """Mock 200 response WITHOUT ``usage`` key; verify token counting from content."""
        provider = LMStudioProvider(base_url="http://localhost:1234/v1")

        content = "this has six words total here"  # 6 whitespace-separated tokens
        mock_response = _make_mock_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": content}}],
            },
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete(
            model="local-model",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["completion_tokens"] == 6

    # ------------------------------------------------------------------
    # 6. test_api_key_from_env
    # ------------------------------------------------------------------

    def test_api_key_from_env(self) -> None:
        """Test that env var ``LMSTUDIO_API_KEY`` is used when no api_key param passed."""
        with patch.dict(os.environ, {"LMSTUDIO_API_KEY": "secret-from-env"}):
            provider = LMStudioProvider(base_url="http://localhost:1234/v1")
            assert provider.api_key == "secret-from-env"

        # Explicit api_key should override env var
        with patch.dict(os.environ, {"LMSTUDIO_API_KEY": "secret-from-env"}):
            provider = LMStudioProvider(
                base_url="http://localhost:1234/v1", api_key="explicit-key"
            )
            assert provider.api_key == "explicit-key"

        # No env var, no api_key → None
        with patch.dict(os.environ, {}, clear=True):
            provider = LMStudioProvider(base_url="http://localhost:1234/v1")
            assert provider.api_key is None


# ---------------------------------------------------------------------------
# OllamaProvider helpers
# ---------------------------------------------------------------------------

def _make_ollama_streaming_client(
    chunks: list[dict],
    status_code: int = 200,
) -> httpx.AsyncClient:
    """Return a mock AsyncClient whose .stream() context manager yields SSE chunks."""
    client = AsyncMock(spec=httpx.AsyncClient)

    lines = []
    for chunk in chunks:
        lines.append(f"data: {json.dumps(chunk)}")
    lines.append("data: [DONE]")
    raw_text = "\n".join(lines) + "\n"

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = status_code
    # aiter_lines must return an async iterator
    async def async_lines():
        for line in raw_text.splitlines():
            yield line
    mock_response.aiter_lines.side_effect = async_lines
    mock_response.aread = AsyncMock(return_value=b"")

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    mock_cm.__aexit__.return_value = None

    client.stream.return_value = mock_cm
    return client


def _make_ollama_nonstreaming_client(
    json_body: dict,
    status_code: int = 200,
) -> httpx.AsyncClient:
    """Return a mock AsyncClient whose .post() returns a JSON response."""
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body
    client.post.return_value = mock_response
    return client


# ---------------------------------------------------------------------------
# Tests: OllamaProvider.stream_complete()
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    """Tests for OllamaProvider.stream_complete() and complete()."""

    @pytest.mark.asyncio
    async def test_stream_complete_success(self) -> None:
        """Mock SSE streaming with typical Ollama response (no usage in chunks)."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "Hello, world"}]

        chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": ", world"}}]},
            {"choices": [{"delta": {"content": "!"}}]},
        ]
        client = _make_ollama_streaming_client(chunks)

        result = await provider.stream_complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["ttft"] is not None
        assert result["completion_tokens"] > 0
        assert result["prompt_length"] == 2
        assert result["tokens_per_second"] is not None
        assert result["e2e_latency"] > 0

    @pytest.mark.asyncio
    async def test_stream_complete_http_error(self) -> None:
        """Mock a non-200 HTTP response during streaming; returns error status."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "Hello"}]

        client = _make_ollama_streaming_client([], status_code=400)

        result = await provider.stream_complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "error"
        assert "HTTP 400" in result["error_message"]

    @pytest.mark.asyncio
    async def test_stream_complete_empty_content(self) -> None:
        """Chunks with empty content should produce zero completion_tokens."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "Hello"}]

        chunks = [
            {"choices": [{"delta": {"content": ""}}]},
            {"choices": [{"delta": {}}]},
        ]
        client = _make_ollama_streaming_client(chunks)

        result = await provider.stream_complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "success"
        assert result["completion_tokens"] == 0
        assert result["tokens_per_second"] is None

    # ------------------------------------------------------------------
    # Tests: OllamaProvider.complete()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_success_with_usage(self) -> None:
        """Mock 200 response that includes usage metadata."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "Say hello"}]

        json_body = {
            "choices": [{"message": {"content": "Hello world"}}],
            "usage": {"completion_tokens": 42, "prompt_tokens": 10, "total_tokens": 52},
        }
        client = _make_ollama_nonstreaming_client(json_body)

        result = await provider.complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["completion_tokens"] == 42
        assert result["ttft"] is None
        assert result["inter_token_latencies"] == []

    @pytest.mark.asyncio
    async def test_complete_no_usage_fallback(self) -> None:
        """CRITICAL: Ollama may omit usage — verify whitespace counting fallback."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "Say hello"}]

        json_body = {
            "choices": [{"message": {"content": "Hello, world"}}],
        }
        client = _make_ollama_nonstreaming_client(json_body)

        result = await provider.complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["completion_tokens"] == 2  # "Hello, world" splits into 2

    @pytest.mark.asyncio
    async def test_complete_success_reasoning_fallback(self) -> None:
        """When content is missing but reasoning is present, use reasoning text."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "Say hello"}]

        json_body = {
            "choices": [{"message": {"reasoning": "Let me think about this"}}],
        }
        client = _make_ollama_nonstreaming_client(json_body)

        result = await provider.complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "success"
        assert result["completion_tokens"] == 5

    @pytest.mark.asyncio
    async def test_complete_http_error(self) -> None:
        """Mock a 400 response."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "test"}]

        json_body = {"error": {"message": "Bad request"}}
        client = _make_ollama_nonstreaming_client(json_body, status_code=400)

        result = await provider.complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "error"
        assert "HTTP 400" in result["error_message"]

    @pytest.mark.asyncio
    async def test_complete_timeout(self) -> None:
        """Simulate a TimeoutError during the request."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "test"}]

        client = AsyncMock(spec=httpx.AsyncClient)
        client.post.side_effect = asyncio.TimeoutError("Request timed out")

        result = await provider.complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "error"
        assert result["error_message"] == "Timeout"

    @pytest.mark.asyncio
    async def test_complete_empty_choices(self) -> None:
        """Response with empty choices list should yield 0 completion_tokens."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        messages = [{"role": "user", "content": "test"}]

        json_body = {"choices": []}
        client = _make_ollama_nonstreaming_client(json_body)

        result = await provider.complete(
            model="llama3", messages=messages, client=client,
        )

        assert result["status"] == "success"
        assert result["completion_tokens"] == 0

    # ------------------------------------------------------------------
    # Tests: constructor / env
    # ------------------------------------------------------------------

    def test_default_base_url(self) -> None:
        p = OllamaProvider()
        assert p.base_url == "http://localhost:11434/v1"

    def test_custom_base_url(self) -> None:
        p = OllamaProvider(base_url="http://my-ollama:8080/v1")
        assert p.base_url == "http://my-ollama:8080/v1"

    def test_base_url_trailing_strip(self) -> None:
        p = OllamaProvider(base_url="http://localhost:11434/v1/")
        assert p.base_url == "http://localhost:11434/v1"

    def test_api_key_from_constructor(self) -> None:
        p = OllamaProvider(api_key="from-ctor")
        assert p.api_key == "from-ctor"

    @patch.dict(os.environ, {"OLLAMA_API_KEY": "from-env"})
    def test_api_key_from_env(self) -> None:
        """Verify OLLAMA_API_KEY env var is read when no api_key passed."""
        p = OllamaProvider()
        assert p.api_key == "from-env"

    @patch.dict(os.environ, {"OLLAMA_API_KEY": "from-env"}, clear=True)
    def test_api_key_env_not_read_when_ctor_provided(self) -> None:
        """Constructor api_key takes priority over env var."""
        p = OllamaProvider(api_key="from-ctor")
        assert p.api_key == "from-ctor"

    def test_default_timeout(self) -> None:
        p = OllamaProvider()
        assert p.timeout == 120

    def test_custom_timeout(self) -> None:
        p = OllamaProvider(timeout=30)
        assert p.timeout == 30


# ---------------------------------------------------------------------------
# Helpers for MLXLMProvider streaming tests
# ---------------------------------------------------------------------------

def _make_sse_stream_client(sse_events: list[dict]) -> MagicMock:
    """Build a MagicMock that mimics httpx.AsyncClient for SSE streaming."""
    sse_lines = [f"data: {json.dumps(e)}" for e in sse_events]
    mock_client = MagicMock()
    mock_client.stream.return_value = _make_httpx_stream_context(sse_lines)
    return mock_client


# ---------------------------------------------------------------------------
# Tests: MLXLMProvider
# ---------------------------------------------------------------------------

class TestMLXLMProvider:
    """Tests for ``MLXLMProvider``."""

    @pytest.mark.asyncio
    async def test_stream_complete_success(self) -> None:
        """Mock SSE streaming; verify metrics are collected correctly."""
        events = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " world"}}]},
            {"usage": {"completion_tokens": 2}},
        ]
        mock_client = _make_sse_stream_client(events)

        provider = MLXLMProvider(base_url="http://localhost:8080/v1")

        result = await provider.stream_complete(
            model="mlx-model",
            messages=[{"role": "user", "content": "Say hello"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["completion_tokens"] == 2
        assert result["prompt_length"] == 2
        assert result["tokens_per_second"] is not None
        assert result["ttft"] is not None
        assert len(result["inter_token_latencies"]) == 1

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        """Mock 200 with usage; verify metrics."""
        provider = MLXLMProvider(base_url="http://localhost:8080/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "Hello world"}}],
                "usage": {"completion_tokens": 2},
            },
        ))

        result = await provider.complete(
            model="mlx-model",
            messages=[{"role": "user", "content": "Say hello"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["error_message"] is None
        assert result["completion_tokens"] == 2
        assert result["prompt_length"] == 2
        assert result["tokens_per_second"] is not None
        assert result["ttft"] is None  # non-streaming

    @pytest.mark.asyncio
    async def test_complete_http_error(self) -> None:
        """Mock 400 response; verify status == 'error'."""
        provider = MLXLMProvider(base_url="http://localhost:8080/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=400,
            json_data={"error": {"message": "Bad model"}},
            text="Bad model",
        ))

        result = await provider.complete(
            model="bad-model",
            messages=[{"role": "user", "content": "test"}],
            client=mock_client,
        )

        assert result["status"] == "error"
        assert result["error_message"] is not None
        assert "HTTP 400" in result["error_message"]

    @pytest.mark.asyncio
    async def test_complete_timeout(self) -> None:
        """Simulate TimeoutError; verify status == 'error' and message."""
        provider = MLXLMProvider(base_url="http://localhost:8080/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=asyncio.TimeoutError("timed out"))

        result = await provider.complete(
            model="slow-model",
            messages=[{"role": "user", "content": "test"}],
            client=mock_client,
        )

        assert result["status"] == "error"
        assert result["error_message"] == "Timeout"

    @pytest.mark.asyncio
    async def test_complete_no_usage_fallback(self) -> None:
        """Response without usage; whitespace-count fallback for completion_tokens."""
        provider = MLXLMProvider(base_url="http://localhost:8080/v1")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=_make_mock_response(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "Hello world"}}],
            },
        ))

        result = await provider.complete(
            model="test",
            messages=[{"role": "user", "content": "hi"}],
            client=mock_client,
        )

        assert result["status"] == "success"
        assert result["completion_tokens"] == 2  # "Hello world".split() == 2

    @pytest.mark.asyncio
    async def test_api_key_from_env(self) -> None:
        """Verify MLXLM_API_KEY env var is read when api_key is not provided."""
        with patch.dict(os.environ, {"MLXLM_API_KEY": "secret-key-123"}):
            provider = MLXLMProvider()
            assert provider.api_key == "secret-key-123"

        # Explicit api_key should override env var
        with patch.dict(os.environ, {"MLXLM_API_KEY": "env-key"}):
            provider = MLXLMProvider(api_key="explicit-key")
            assert provider.api_key == "explicit-key"


# ---------------------------------------------------------------------------
# Tests: VLLMProvider env var fallback
# ---------------------------------------------------------------------------


class TestVLLMProviderEnvVars:
    """Tests for VLLMProvider VLLM_API_KEY env var fallback."""

    def test_env_var_fallback(self) -> None:
        """VLLM_API_KEY set in env -> provider reads it."""
        with patch.dict(os.environ, {"VLLM_API_KEY": "env-key"}):
            provider = VLLMProvider(base_url="http://localhost:8000/v1")
            assert provider.api_key == "env-key"
            assert provider.base_url == "http://localhost:8000/v1"

    def test_explicit_key_overrides_env(self) -> None:
        """Explicit api_key param takes priority over env var."""
        with patch.dict(os.environ, {"VLLM_API_KEY": "env-key"}):
            provider = VLLMProvider(base_url="http://localhost:8000/v1", api_key="explicit")
            assert provider.api_key == "explicit"

    def test_no_env_var_returns_none(self) -> None:
        """No VLLM_API_KEY env var -> api_key is None."""
        with patch.dict(os.environ, {}, clear=True):
            provider = VLLMProvider(base_url="http://localhost:8000/v1")
            assert provider.api_key is None