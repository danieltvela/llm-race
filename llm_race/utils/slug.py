"""Slug generation, validation, and parsing for model identification.

A model slug is a composite identifier composed of ``ai_lab``, ``name``,
``quantization``, and an optional ``extra`` component, joined by ``/``:

    ``{ai_lab}/{name}/{quantization}``
    ``{ai_lab}/{name}/{quantization}/{extra}``

All components are lowercased and normalized (non-alphanumeric characters
replaced with ``-``, consecutive dashes collapsed, leading/trailing dashes
trimmed).
"""

from __future__ import annotations

import re
from typing import Any


def _normalize(part: str) -> str:
    """Lowercase and replace non-alphanumeric characters with ``-``."""
    part = part.lower().strip()
    part = re.sub(r"[^a-z0-9]", "-", part)
    part = re.sub(r"-+", "-", part)
    part = part.strip("-")
    return part


def build_slug(
    ai_lab: str,
    name: str,
    quantization: str,
    extra: str | None = None,
) -> str:
    """Build a normalized model slug from its components.

    Args:
        ai_lab: The AI lab / organization (e.g. ``"Qwen"``, ``"Meta"``).
        name: The model name (e.g. ``"Qwen3-8B"``, ``"Llama-3.2-3B"``).
        quantization: The quantization type (e.g. ``"FP8"``, ``"none"``).
        extra: Optional extra modifier (e.g. ``"agent-bench-optimized"``).

    Returns:
        A normalized slug string like ``"qwen/qwen3-8b/none"``.

    Raises:
        ValueError: If any required component is empty after normalization.
    """
    lab = _normalize(ai_lab)
    model_name = _normalize(name)
    quant = _normalize(quantization)

    if not lab:
        raise ValueError(f"ai_lab cannot be empty: {ai_lab!r}")
    if not model_name:
        raise ValueError(f"name cannot be empty: {name!r}")
    if not quant:
        raise ValueError(f"quantization cannot be empty: {quantization!r}")

    if extra:
        extra_norm = _normalize(extra)
        if extra_norm:
            return f"{lab}/{model_name}/{quant}/{extra_norm}"

    return f"{lab}/{model_name}/{quant}"


def parse_slug(slug: str) -> dict[str, str | None]:
    """Parse a model slug into its components.

    Args:
        slug: A slug string like ``"qwen/qwen3-8b/none"``.

    Returns:
        A dict with keys ``ai_lab``, ``name``, ``quantization``, and
        ``extra`` (``None`` if the slug has only 3 parts).

    Raises:
        ValueError: If the slug has fewer than 3 or more than 4 parts,
            or any required part is empty.
    """
    parts = slug.strip().split("/")
    if len(parts) < 3 or len(parts) > 4:
        raise ValueError(
            f"Invalid slug format: {slug!r}. "
            f"Expected 3 or 4 parts separated by '/'. Got {len(parts)}."
        )

    ai_lab, name, quantization = parts[0], parts[1], parts[2]
    extra = parts[3] if len(parts) == 4 else None

    if not ai_lab or not name or not quantization:
        raise ValueError(
            f"Invalid slug: required parts cannot be empty: {slug!r}"
        )

    return {
        "ai_lab": ai_lab,
        "name": name,
        "quantization": quantization,
        "extra": extra,
    }


def validate_slug(slug: str) -> bool:
    """Check if a string is a valid model slug.

    Args:
        slug: The string to validate.

    Returns:
        ``True`` if the slug has 3 or 4 non-empty parts separated by ``/``,
        ``False`` otherwise.
    """
    try:
        parse_slug(slug)
        return True
    except ValueError:
        return False