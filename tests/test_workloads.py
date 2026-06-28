"""Tests for workload profiles module."""

from __future__ import annotations

import inspect
import subprocess
import sys

import pytest

from llm_race.bench.workloads import (
    HIGH_THROUGHPUT,
    MULTI_AGENT,
    SINGLE_USER,
    STRESS,
    CHAT,
    WORKLOAD_REGISTRY,
    WorkloadProfile,
    get_workload,
)


# ---------------------------------------------------------------------------
# Unit tests: WORKLOAD_REGISTRY
# ---------------------------------------------------------------------------


class TestWorkloadRegistry:
    """Verify all 5 profiles exist with correct attributes."""

    def test_registry_contains_all_profiles(self):
        assert len(WORKLOAD_REGISTRY) == 5
        for name in ("single-user", "chat", "multi-agent", "high-throughput", "stress"):
            assert name in WORKLOAD_REGISTRY

    def test_single_user_profile(self):
        p = WORKLOAD_REGISTRY["single-user"]
        assert p.name == "single-user"
        assert p.concurrency_levels == [1]
        assert "latency" in p.description.lower()

    def test_chat_profile(self):
        p = WORKLOAD_REGISTRY["chat"]
        assert p.name == "chat"
        assert p.concurrency_levels == [1]

    def test_multi_agent_profile(self):
        p = WORKLOAD_REGISTRY["multi-agent"]
        assert p.name == "multi-agent"
        assert p.concurrency_levels == [4, 8, 16]

    def test_high_throughput_profile(self):
        p = WORKLOAD_REGISTRY["high-throughput"]
        assert p.name == "high-throughput"
        assert p.concurrency_levels == [32, 64, 128]

    def test_stress_profile(self):
        p = WORKLOAD_REGISTRY["stress"]
        assert p.name == "stress"
        assert p.concurrency_levels == [256, 512]

    def test_all_profiles_have_default_prompt_lengths(self):
        for name, profile in WORKLOAD_REGISTRY.items():
            assert len(profile.default_prompt_lengths) > 0
            assert all(isinstance(l, int) for l in profile.default_prompt_lengths)

    def test_all_profiles_have_descriptions(self):
        for name, profile in WORKLOAD_REGISTRY.items():
            assert len(profile.description) > 0

    def test_all_profiles_have_behavior(self):
        for name, profile in WORKLOAD_REGISTRY.items():
            assert len(profile.behavior) > 0

    def test_profiles_are_frozen(self):
        """WorkloadProfile instances should be immutable."""
        for name, profile in WORKLOAD_REGISTRY.items():
            assert isinstance(profile, WorkloadProfile)
            assert profile.__class__.__hash__ is not None


# ---------------------------------------------------------------------------
# Unit tests: get_workload
# ---------------------------------------------------------------------------


class TestGetWorkload:
    def test_get_workload_valid(self):
        p = get_workload("single-user")
        assert p.name == "single-user"

    def test_get_workload_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown workload profile"):
            get_workload("nonexistent")

    def test_get_workload_error_includes_valid_names(self):
        with pytest.raises(ValueError) as exc_info:
            get_workload("invalid")
        msg = str(exc_info.value)
        assert "single-user" in msg
        assert "multi-agent" in msg

    def test_get_workload_case_sensitive(self):
        with pytest.raises(ValueError):
            get_workload("SINGLE-USER")

    def test_get_workload_returns_all_profiles(self):
        for name in WORKLOAD_REGISTRY:
            p = get_workload(name)
            assert p is WORKLOAD_REGISTRY[name]


# ---------------------------------------------------------------------------
# Integration tests: CLI
# ---------------------------------------------------------------------------


class TestCLIIntegration:
    """Test --workload CLI argument via subprocess."""

    @staticmethod
    def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "llm_race.bench.cli", *args],
            capture_output=True,
            text=True,
        )

    def test_cli_help_includes_workload(self):
        result = self._run_cli("run", "--help")
        assert "--workload" in result.stdout
        assert "single-user" in result.stdout
        assert "multi-agent" in result.stdout

    def test_cli_rejects_invalid_workload(self):
        result = self._run_cli("run", "--workload", "invalid")
        assert result.returncode != 0
        assert "invalid choice" in result.stderr

    def test_cli_backward_compat_with_concurrency(self):
        result = self._run_cli("run", "--help")
        assert "--concurrency" in result.stdout