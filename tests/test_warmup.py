"""Unit tests for warmup/measured iterations in runner.py."""

import asyncio

import pytest

from llm_race.bench.runner import RequestMetrics, run_scenario
from llm_race.config import DEFAULT_MEASURED_ITERATIONS, DEFAULT_WARMUP_ITERATIONS
from llm_race.config.base import Provider


class FakeProvider(Provider):
    """Mock provider that returns controllable results for testing."""

    timeout: int = 30

    def __init__(self, latency: float = 0.05) -> None:
        self.latency = latency
        self.call_count = 0

    async def stream_complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_p: float = 1.0,
        client: object = None,
    ) -> dict:
        """Simulate a streaming completion with configurable latency."""
        self.call_count += 1
        await asyncio.sleep(self.latency)
        return {
            "status": "success",
            "e2e_latency": self.latency,
            "ttft": self.latency / 2,
            "completion_tokens": 50,
            "prompt_length": len(messages[1]["content"]),
            "inter_token_latencies": [0.01] * 10,
            "tokens_per_second": 1000.0,
        }

    async def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 256,
        temperature: float = 0.0,
        top_p: float = 1.0,
        client: object = None,
    ) -> dict:
        """Simulate a non-streaming completion (not used by runner)."""
        return await self.stream_complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            client=client,
        )


class TestWarmupDiscard:
    """Warmup results must NOT appear in returned metrics."""

    @pytest.mark.asyncio
    async def test_warmup_discarded(self) -> None:
        provider = FakeProvider()
        metrics, wall_elapsed = await run_scenario(
            provider=provider,
            model="test-model",
            concurrency=2,
            prompt_length=64,
            max_tokens=100,
            temperature=0.0,
            top_p=1.0,
            warmup_iterations=2,
            measured_iterations=3,
        )
        assert len(metrics) == 6, f"Expected 6 metrics, got {len(metrics)}"
        # warmup_iterations=2 at concurrency=1 + measured_iterations=3 at concurrency=2 = 2 + 6 = 8
        assert provider.call_count == 8, f"Expected 8 calls, got {provider.call_count}"
        assert wall_elapsed > 0, "Wall clock should be positive"

    @pytest.mark.asyncio
    async def test_warmup_zero(self) -> None:
        provider = FakeProvider()
        metrics, wall_elapsed = await run_scenario(
            provider=provider,
            model="test-model",
            concurrency=2,
            prompt_length=64,
            max_tokens=100,
            temperature=0.0,
            top_p=1.0,
            warmup_iterations=0,
            measured_iterations=2,
        )
        assert len(metrics) == 4, f"Expected 4 metrics, got {len(metrics)}"
        assert provider.call_count == 4, f"Expected 4 calls, got {provider.call_count}"
        assert wall_elapsed > 0, "Wall clock should be positive"

    @pytest.mark.asyncio
    async def test_measured_zero(self) -> None:
        provider = FakeProvider()
        metrics, wall_elapsed = await run_scenario(
            provider=provider,
            model="test-model",
            concurrency=2,
            prompt_length=64,
            max_tokens=100,
            temperature=0.0,
            top_p=1.0,
            warmup_iterations=1,
            measured_iterations=0,
        )
        assert len(metrics) == 0, f"Expected 0 metrics, got {len(metrics)}"
        assert wall_elapsed == 0.0, "Wall clock should be 0 when not measured"
        # NOTE: runner.py returns early when measured_iterations==0, so warmup
        # is also skipped. This is the current behaviour of the code under test.
        assert provider.call_count == 0, f"Expected 0 calls, got {provider.call_count}"


class TestRequestIDs:
    """Request IDs must be sequential from 0 across all measured batches."""

    @pytest.mark.asyncio
    async def test_sequential_ids(self) -> None:
        provider = FakeProvider()
        metrics, wall_elapsed = await run_scenario(
            provider=provider,
            model="test-model",
            concurrency=2,
            prompt_length=64,
            max_tokens=100,
            temperature=0.0,
            top_p=1.0,
            warmup_iterations=2,
            measured_iterations=3,
        )
        assert len(metrics) == 6
        assert wall_elapsed > 0
        ids = [m.request_id for m in metrics]
        assert ids == list(range(6)), f"IDs not sequential: {ids}"
        assert {m.request_id for m in metrics} == set(range(6))

    @pytest.mark.asyncio
    async def test_ids_across_batches(self) -> None:
        provider = FakeProvider()
        metrics, wall_elapsed = await run_scenario(
            provider=provider,
            model="test-model",
            concurrency=1,
            prompt_length=64,
            max_tokens=100,
            temperature=0.0,
            top_p=1.0,
            warmup_iterations=1,
            measured_iterations=5,
        )
        assert len(metrics) == 5
        assert metrics[0].request_id == 0
        assert metrics[4].request_id == 4
        ids = [m.request_id for m in metrics]
        assert ids == list(range(5)), f"IDs not sequential across batches: {ids}"


class TestDefaults:
    """Default constants must match AGENTS.md."""

    def test_default_warmup(self) -> None:
        assert DEFAULT_WARMUP_ITERATIONS == 1

    def test_default_measured(self) -> None:
        assert DEFAULT_MEASURED_ITERATIONS == 10


class TestCLIArgs:
    """CLI argument parsing for warmup/measured flags."""

    def test_cli_defaults(self) -> None:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--warmup-iterations", type=int, default=DEFAULT_WARMUP_ITERATIONS
        )
        parser.add_argument(
            "--measured-iterations", type=int, default=DEFAULT_MEASURED_ITERATIONS
        )
        args = parser.parse_args([])
        assert args.warmup_iterations == DEFAULT_WARMUP_ITERATIONS
        assert args.measured_iterations == DEFAULT_MEASURED_ITERATIONS

    def test_cli_custom(self) -> None:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--warmup-iterations", type=int, default=DEFAULT_WARMUP_ITERATIONS
        )
        parser.add_argument(
            "--measured-iterations", type=int, default=DEFAULT_MEASURED_ITERATIONS
        )
        args = parser.parse_args(
            ["--warmup-iterations", "5", "--measured-iterations", "20"]
        )
        assert args.warmup_iterations == 5
        assert args.measured_iterations == 20
