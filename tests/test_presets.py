"""Tests for preset loader module and CLI preset flags."""

from __future__ import annotations

import subprocess
import sys

import pytest

from llm_race.config.presets import (
    _PRESETS_PATH,
    _load_presets_data,
    list_presets,
    load_preset,
)


# ---------------------------------------------------------------------------
# Unit tests: load_preset
# ---------------------------------------------------------------------------


class TestPresetLoader:
    """Verify preset loading, error handling, and list behavior."""

    def test_load_preset_known_key(self):
        preset = load_preset("qwen3-8b-vllm")
        assert isinstance(preset, dict)
        assert preset["key"] == "qwen3-8b-vllm"
        assert preset["provider"] == "vllm"
        assert preset["slug"] == "qwen/qwen3-8b/none"
        assert preset["ai_lab"] == "qwen"
        assert preset["model_api_name"] == "Qwen3-8B"
        assert preset["quantization"] == "none"

    def test_load_preset_unknown_key_raises_keyerror(self):
        with pytest.raises(KeyError, match="nonexistent"):
            load_preset("nonexistent")

    def test_load_preset_error_message_includes_available_keys(self):
        try:
            load_preset("nonexistent")
        except KeyError as exc:
            msg = str(exc)
            available = list_presets()
            for preset in available:
                assert preset["key"] in msg, (
                    f"Error message should list all available keys; "
                    f"missing {preset['key']!r}"
                )
        else:
            pytest.fail("KeyError was not raised")

    def test_list_presets_returns_all_presets(self):
        presets = list_presets()
        assert len(presets) == 10

    def test_list_presets_each_has_required_fields(self):
        required = ("key", "name", "provider", "slug", "ai_lab", "model_api_name", "quantization")
        for preset in list_presets():
            for field in required:
                assert field in preset, (
                    f"Preset {preset.get('key', '<unknown>')!r} "
                    f"missing required field {field!r}"
                )

    def test_list_presets_keys_are_unique(self):
        keys = [p["key"] for p in list_presets()]
        assert len(keys) == len(set(keys))

    def test_load_preset_is_cached(self):
        first = _load_presets_data()
        second = _load_presets_data()
        assert first is second

    def test_load_preset_json_path_exists(self):
        assert _PRESETS_PATH.exists()
        assert _PRESETS_PATH.suffix == ".json"

    def test_all_providers_are_string(self):
        for preset in list_presets():
            assert isinstance(preset["provider"], str)
            assert len(preset["provider"]) > 0

    def test_all_slugs_are_string(self):
        for preset in list_presets():
            assert isinstance(preset["slug"], str)
            assert len(preset["slug"]) > 0

    def test_all_names_are_string(self):
        for preset in list_presets():
            assert isinstance(preset["name"], str)
            assert len(preset["name"]) > 0


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCLIIntegration:
    """Test CLI flags via subprocess."""

    @staticmethod
    def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "llm_race.bench.cli", *args],
            capture_output=True,
            text=True,
        )

    def test_cli_help_includes_preset_flags(self):
        result = self._run_cli("run", "--help")
        assert result.returncode == 0
        assert "--preset" in result.stdout
        assert "--list-presets" in result.stdout

    def test_cli_list_presets_output(self):
        result = self._run_cli("run", "--list-presets")
        assert result.returncode == 0
        keys = [p["key"] for p in list_presets()]
        for key in keys:
            assert key in result.stdout, (
                f"--list-presets should print {key!r}"
            )

    def test_cli_unknown_preset_error(self):
        result = self._run_cli("run", "--preset", "nonexistent", "--no-db")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "nonexistent" in combined
        # Should list available keys
        available = list_presets()
        for preset in available:
            assert preset["key"] in combined, (
                f"Error should list {preset['key']!r}"
            )

    def test_cli_preset_smoke_test(self):
        """Verify --preset is accepted by argparse without error."""
        result = self._run_cli("run", "--preset", "qwen3-8b-vllm", "--help")
        assert result.returncode == 0