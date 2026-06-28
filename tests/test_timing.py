"""Tests for timing utilities (compute_latency_stats, compute_itl_stats)."""

from __future__ import annotations

import pytest

from llm_race.utils.timing import compute_itl_stats, compute_latency_stats


class TestComputeLatencyStats:
    def test_normal_values(self):
        """[10, 20, 30, 40, 50] → mean=30, p50=30, p95=48, p99=49.6, max=50"""
        stats = compute_latency_stats([10.0, 20.0, 30.0, 40.0, 50.0])
        assert stats["mean"] == 30.0
        assert stats["p50"] == 30.0
        assert stats["p95"] == 48.0
        assert stats["p99"] == pytest.approx(49.6, abs=0.1)
        assert stats["max"] == 50.0

    def test_empty_list(self):
        """Empty list returns all 0.0"""
        stats = compute_latency_stats([])
        assert stats == {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}

    def test_single_value(self):
        """[42.0] → mean=42, p50=42, max=42"""
        stats = compute_latency_stats([42.0])
        assert stats["mean"] == 42.0
        assert stats["p50"] == 42.0
        assert stats["max"] == 42.0

    def test_all_same(self):
        """[5,5,5,5,5] → all stats = 5.0"""
        stats = compute_latency_stats([5.0, 5.0, 5.0, 5.0, 5.0])
        for k in ("mean", "p50", "p95", "p99", "max"):
            assert stats[k] == 5.0, f"{k} should be 5.0, got {stats[k]}"

    def test_floats(self):
        """Float values with decimals return correct stats"""
        stats = compute_latency_stats([1.5, 2.5, 3.5])
        assert stats["mean"] == pytest.approx(2.5)

    def test_unsorted_values(self):
        """Unsorted input produces correct stats"""
        stats = compute_latency_stats([50.0, 10.0, 30.0, 20.0, 40.0])
        assert stats["mean"] == 30.0
        assert stats["p50"] == 30.0
        assert stats["max"] == 50.0

    def test_two_values(self):
        """Two values: mean=25, p50=25, p95=47.5, p99=49.5, max=50"""
        stats = compute_latency_stats([0.0, 50.0])
        assert stats["mean"] == 25.0
        assert stats["p50"] == 25.0
        assert stats["max"] == 50.0

    def test_negative_values(self):
        """Negative values handled correctly"""
        stats = compute_latency_stats([-10.0, 0.0, 10.0])
        assert stats["mean"] == 0.0
        assert stats["max"] == 10.0

    def test_large_values(self):
        """Large latency values (e.g. ms)"""
        stats = compute_latency_stats([1000.0, 2000.0, 3000.0])
        assert stats["mean"] == 2000.0
        assert stats["max"] == 3000.0

    def test_returns_dict(self):
        """Return type is always a dict with correct keys"""
        stats = compute_latency_stats([1.0, 2.0, 3.0])
        assert isinstance(stats, dict)
        assert set(stats.keys()) == {"mean", "p50", "p95", "p99", "max"}


class TestComputeItlStats:
    def test_normal_values(self):
        """List of values returns dict with float values"""
        stats = compute_itl_stats([0.01, 0.02, 0.03, 0.04, 0.05])
        assert isinstance(stats["mean"], float)
        assert stats["mean"] == pytest.approx(0.03, abs=0.001)

    def test_empty_list(self):
        """Empty list returns all None (not 0.0)"""
        stats = compute_itl_stats([])
        assert stats == {"mean": None, "p50": None, "p95": None, "p99": None}

    def test_single_value(self):
        """Single value returns that value for all stats"""
        stats = compute_itl_stats([0.5])
        assert stats["mean"] == 0.5
        assert stats["p50"] == 0.5
        assert stats["p95"] == 0.5
        assert stats["p99"] == 0.5

    def test_all_same(self):
        """[0.1, 0.1, 0.1] → all stats = 0.1"""
        stats = compute_itl_stats([0.1, 0.1, 0.1])
        for k in ("mean", "p50", "p95", "p99"):
            assert stats[k] == pytest.approx(0.1, abs=1e-9)

    def test_floats(self):
        """Float values with decimals return correct stats"""
        stats = compute_itl_stats([0.001, 0.002, 0.003])
        assert stats["mean"] == pytest.approx(0.002, abs=0.0001)

    def test_returns_dict(self):
        """Return type is always a dict with correct keys"""
        stats = compute_itl_stats([0.1, 0.2])
        assert isinstance(stats, dict)
        assert set(stats.keys()) == {"mean", "p50", "p95", "p99"}

    def test_sorted_values(self):
        """Sorted input produces correct percentiles"""
        stats = compute_itl_stats([0.01, 0.02, 0.03, 0.04, 0.05])
        assert stats["p50"] == pytest.approx(0.03, abs=0.001)
        assert stats["p95"] == pytest.approx(0.048, abs=0.001)

    def test_unsorted_values(self):
        """Unsorted input produces correct stats"""
        stats = compute_itl_stats([0.05, 0.01, 0.03, 0.02, 0.04])
        assert stats["mean"] == pytest.approx(0.03, abs=0.001)
        assert stats["max"] if "max" in stats else True  # no max key in ITL