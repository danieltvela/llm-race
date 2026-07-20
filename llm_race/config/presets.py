"""Preset definitions for llm-race benchmarks."""

import json
import logging
from pathlib import Path
from typing import Any

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PRESETS: list[dict[str, Any]] | None = None

_PRESETS_PATH = Path(__file__).resolve().parent / "presets.json"


def _load_presets_data() -> list[dict[str, Any]]:
    """Load and validate presets from the JSON file."""
    global _PRESETS

    if _PRESETS is not None:
        return _PRESETS

    with open(_PRESETS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    presets: list[dict[str, Any]] = data.get("presets", [])

    required_fields = ("key", "name", "provider", "slug", "ai_lab", "model_api_name", "quantization")
    for preset in presets:
        missing = [f for f in required_fields if f not in preset]
        if missing:
            logger.warning(
                "Preset %r is missing required fields: %s",
                preset.get("key", "<unknown>"),
                ", ".join(missing),
            )

    _PRESETS = presets
    return _PRESETS


def load_preset(key: str) -> dict[str, Any]:
    """Return the preset matching *key*.

    Raises:
        KeyError: If *key* is not found.
    """
    presets = _load_presets_data()
    available = [p["key"] for p in presets]
    for preset in presets:
        if preset["key"] == key:
            return preset
    raise KeyError(
        f"Unknown preset {key!r}. Available: {', '.join(available)}"
    )


def list_presets() -> list[dict[str, Any]]:
    """Return all presets as a list of dicts."""
    return _load_presets_data()