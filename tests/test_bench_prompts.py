"""Tests for prompt generation (generate_prompt)."""

from __future__ import annotations

import random
import pytest

from llm_race.bench.prompts import generate_prompt


class TestGeneratePrompt:
    def test_returns_string(self):
        """generate_prompt returns a non-empty string."""
        prompt = generate_prompt(100)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_capitalized_sentences(self):
        """Sentences start with capital letter and end with period."""
        prompt = generate_prompt(200)
        # Sentences are joined with " ", each ends with ". "
        # Verify every ". " is preceded by a capitalized word and followed by a capital letter
        parts = prompt.split(". ")
        # All but the last part should have been a complete sentence (capitalized)
        for part in parts[:-1]:
            part = part.strip()
            assert part, "Empty sentence part found"
            assert part[0].isupper(), f"Sentence doesn't start with capital: {part[:30]}"
        # Last part should also be capitalized and end with period
        last = parts[-1].strip()
        if last:
            assert last[0].isupper(), f"Last sentence doesn't start with capital: {last[:30]}"
            assert last.endswith("."), f"Last sentence doesn't end with period: {last[:30]}"

    def test_no_placeholder_text(self):
        """Output doesn't contain Python object repr artifacts."""
        prompt = generate_prompt(100)
        assert "object at" not in prompt
        assert "built-in" not in prompt
        assert not prompt.startswith("<")

    def test_small_token_approx(self):
        """token_approx=0 or 1 still returns a valid string (edge case)."""
        for tiny in (0, 1):
            prompt = generate_prompt(tiny)
            assert isinstance(prompt, str)
            assert len(prompt) >= 0

    def test_deterministic_with_seed(self):
        """Same seed produces same output for same input."""
        random.seed(42)
        p1 = generate_prompt(100)
        random.seed(42)
        p2 = generate_prompt(100)
        assert p1 == p2

    def test_output_length_scales(self):
        """Larger token_approx produces longer (or equal) output on average."""
        small = generate_prompt(50)
        large = generate_prompt(500)
        assert len(large) > len(small)