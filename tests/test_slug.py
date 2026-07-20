"""Tests for the slug utility module."""

from __future__ import annotations

import pytest

from llm_race.utils.slug import build_slug, parse_slug, validate_slug


class TestBuildSlug:
    """Test build_slug() function."""

    def test_build_slug_basic(self):
        assert build_slug("Qwen", "Qwen3-8B", "none") == "qwen/qwen3-8b/none"

    def test_build_slug_with_extra(self):
        assert build_slug("google", "Gemma-4-26B", "none", "agent-bench") == "google/gemma-4-26b/none/agent-bench"

    def test_build_slug_special_chars(self):
        assert build_slug("AI Lab!", "Model@2.0", "FP 8") == "ai-lab/model-2-0/fp-8"

    def test_build_slug_empty_ai_lab_raises(self):
        with pytest.raises(ValueError, match="ai_lab"):
            build_slug("", "Qwen3-8B", "none")

    def test_build_slug_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            build_slug("Qwen", "", "none")

    def test_build_slug_empty_quantization_raises(self):
        with pytest.raises(ValueError, match="quantization"):
            build_slug("Qwen", "Qwen3-8B", "")

    def test_build_slug_extra_empty_ignored(self):
        assert build_slug("Qwen", "Qwen3-8B", "none", "") == "qwen/qwen3-8b/none"

    def test_build_slug_extra_none_ignored(self):
        assert build_slug("Qwen", "Qwen3-8B", "none", None) == "qwen/qwen3-8b/none"


class TestParseSlug:
    """Test parse_slug() function."""

    def test_parse_slug_3_parts(self):
        result = parse_slug("qwen/qwen3-8b/none")
        assert result == {"ai_lab": "qwen", "name": "qwen3-8b", "quantization": "none", "extra": None}

    def test_parse_slug_4_parts(self):
        result = parse_slug("a/b/c/d")
        assert result == {"ai_lab": "a", "name": "b", "quantization": "c", "extra": "d"}

    def test_parse_slug_2_parts_raises(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            parse_slug("a/b")

    def test_parse_slug_5_parts_raises(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            parse_slug("a/b/c/d/e")

    def test_parse_slug_empty_part_raises(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            parse_slug("/qwen3-8b/none")


class TestValidateSlug:
    """Test validate_slug() function."""

    def test_validate_slug_valid_3_parts(self):
        assert validate_slug("qwen/qwen3-8b/none") is True

    def test_validate_slug_valid_4_parts(self):
        assert validate_slug("a/b/c/d") is True

    def test_validate_slug_invalid_2_parts(self):
        assert validate_slug("a/b") is False

    def test_validate_slug_invalid_5_parts(self):
        assert validate_slug("a/b/c/d/e") is False

    def test_validate_slug_empty_string(self):
        assert validate_slug("") is False