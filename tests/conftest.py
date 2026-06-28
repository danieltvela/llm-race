"""Pytest configuration for LLM Race tests."""

import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True)
def _mock_monotonic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make time.monotonic() return a stable increasing value for deterministic timing."""
    counter = [0.0]

    def fake_monotonic() -> float:
        val = counter[0]
        counter[0] += 0.001
        return val

    monkeypatch.setattr("time.monotonic", fake_monotonic)