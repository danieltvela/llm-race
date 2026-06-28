"""QA Scenario 3: measured_iterations=0 returns empty."""

import asyncio
import sys

sys.path.insert(0, "/Users/danielvela/projects/ai/llm-race")

from llm_race.bench.runner import run_scenario
from llm_race.config.base import Provider


class FakeProvider(Provider):
    timeout: int = 30

    def __init__(self, latency: float = 0.01) -> None:
        self.latency = latency
        self.call_count = 0

    async def stream_complete(self, model, messages, max_tokens=256, temperature=0.0, top_p=1.0, client=None):
        self.call_count += 1
        return {
            "status": "success",
            "e2e_latency": self.latency,
            "ttft": self.latency / 2,
            "completion_tokens": 50,
            "prompt_length": len(messages[1]["content"]),
            "inter_token_latencies": [0.01] * 10,
            "tokens_per_second": 1000.0,
        }

    async def complete(self, model, messages, max_tokens=256, temperature=0.0, top_p=1.0, client=None):
        return await self.stream_complete(model=model, messages=messages, max_tokens=max_tokens,
                                          temperature=temperature, top_p=top_p, client=client)


async def main() -> None:
    provider = FakeProvider()
    metrics = await run_scenario(
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

    errors = []
    if len(metrics) != 0:
        errors.append(f"FAIL: len(metrics) == {len(metrics)}, expected 0")
    else:
        print("PASS: len(metrics) == 0")

    if provider.call_count != 0:
        errors.append(f"FAIL: provider.call_count == {provider.call_count}, expected 0")
    else:
        print("PASS: provider.call_count == 0")

    if errors:
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("QA Scenario 3: PASSED")


if __name__ == "__main__":
    asyncio.run(main())
