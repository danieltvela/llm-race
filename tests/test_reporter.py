"""Tests for reporter (format_table, save_csv, save_json)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from llm_race.bench.runner import ScenarioResult
from llm_race.utils.reporter import format_table, save_csv, save_json


def _make_result(**overrides: object) -> ScenarioResult:
    """Create a ScenarioResult with sensible defaults for testing."""
    defaults: dict[str, object] = {
        "concurrency": 1,
        "prompt_length": 100,
        "total_requests": 10,
        "successful_requests": 10,
        "failed_requests": 0,
        "e2e_mean": 1.0,
        "e2e_p50": 0.9,
        "e2e_p95": 1.5,
        "e2e_p99": 2.0,
        "e2e_max": 2.5,
        "ttft_mean": 0.1,
        "ttft_p50": 0.08,
        "ttft_p95": 0.15,
        "ttft_p99": 0.2,
        "throughput_rps": 10.0,
        "throughput_tps": 500.0,
        "itl_mean": 0.02,
        "itl_p50": 0.015,
        "itl_p95": 0.03,
        "wall_clock_seconds": 5.0,
    }
    defaults.update(overrides)
    return ScenarioResult(**defaults)  # type: ignore[arg-type]


class TestFormatTable:
    def test_header_in_output(self):
        """Output contains expected column headers."""
        result = format_table([_make_result()])
        assert "Concurrency" in result
        assert "Prompt Len" in result
        assert "TPS" in result

    def test_single_result(self):
        """One ScenarioResult appears in the formatted output."""
        result = format_table([_make_result(concurrency=4)])
        assert "  4" in result

    def test_multiple_results(self):
        """Two ScenarioResults both appear in output."""
        r1 = _make_result(concurrency=1)
        r2 = _make_result(concurrency=8)
        result = format_table([r1, r2])
        assert "  1" in result
        assert "  8" in result

    def test_empty_list(self):
        """Empty list returns a string with header and separator only."""
        result = format_table([])
        assert "Concurrency" in result
        assert result.count("\n") >= 1  # header + separator


class TestSaveCsv:
    def test_csv_created(self):
        """File is created at specified path."""
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        try:
            save_csv([_make_result()], str(tmp))
            assert tmp.exists()
            assert tmp.stat().st_size > 0
        finally:
            os.unlink(tmp)

    def test_csv_content(self):
        """File contains expected headers and data."""
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        try:
            save_csv([_make_result(concurrency=7)], str(tmp))
            content = tmp.read_text()
            assert "concurrency" in content
            assert "7" in content
        finally:
            os.unlink(tmp)

    def test_empty_list_writes_header_only(self):
        """Empty results writes only header row."""
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        try:
            save_csv([], str(tmp))
            content = tmp.read_text()
            assert content.strip() != ""  # header exists
            assert "concurrency" in content.split("\n")[0]
        finally:
            os.unlink(tmp)

    def test_csv_values_match(self):
        """Values in CSV match the ScenarioResult fields."""
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        try:
            r = _make_result(concurrency=3, successful_requests=8, failed_requests=2)
            save_csv([r], str(tmp))
            content = tmp.read_text()
            # CSV header + 1 data row
            lines = content.strip().split("\n")
            assert len(lines) == 2
            assert "3" in lines[1]
        finally:
            os.unlink(tmp)


class TestSaveJson:
    def test_json_created(self):
        """File is created at specified path."""
        tmp = Path(tempfile.mktemp(suffix=".json"))
        try:
            save_json([_make_result()], str(tmp))
            assert tmp.exists()
            assert tmp.stat().st_size > 0
        finally:
            os.unlink(tmp)

    def test_json_structure(self):
        """File contains 'timestamp' and 'scenarios' top-level keys."""
        tmp = Path(tempfile.mktemp(suffix=".json"))
        try:
            save_json([_make_result()], str(tmp))
            data = json.loads(tmp.read_text())
            assert "timestamp" in data
            assert "scenarios" in data
        finally:
            os.unlink(tmp)

    def test_json_content(self):
        """Scenario fields appear correctly in JSON."""
        tmp = Path(tempfile.mktemp(suffix=".json"))
        try:
            save_json([_make_result(concurrency=5)], str(tmp))
            data = json.loads(tmp.read_text())
            assert len(data["scenarios"]) == 1
            assert data["scenarios"][0]["concurrency"] == 5
        finally:
            os.unlink(tmp)

    def test_empty_list_writes_empty_scenarios(self):
        """Empty results gives empty scenarios array in JSON."""
        tmp = Path(tempfile.mktemp(suffix=".json"))
        try:
            save_json([], str(tmp))
            data = json.loads(tmp.read_text())
            assert data["scenarios"] == []
        finally:
            os.unlink(tmp)