"""Global configuration for llm-race."""

import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from llm_race.config.base import Provider

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT.parent / ".env")

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "benchmarks.db"

DEFAULT_BASE_URL = os.environ.get("LLM_RACE_BASE_URL", "http://localhost:8000/v1")
DEFAULT_MODEL = os.environ.get("LLM_RACE_MODEL", "Qwen3-8B")
DEFAULT_PROVIDER = os.environ.get("LLM_RACE_PROVIDER", "vllm")
DEFAULT_CONCURRENCY = [1, 16, 128, 512]
DEFAULT_PROMPT_LENGTHS = [64, 512, 2048, 4096]
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_REQUEST_TIMEOUT = 120
DEFAULT_WARMUP_ITERATIONS = 1
DEFAULT_MEASURED_ITERATIONS = 10

WEB_PORT = int(os.environ.get("LLM_RACE_WEB_PORT", "8080"))
WEB_HOST = os.environ.get("LLM_RACE_WEB_HOST", "127.0.0.1")


def create_provider(provider_type: str, **kwargs: Any) -> Provider:
    """Build a provider by type name.

    Example::

        provider = create_provider("vllm", base_url="http://localhost:8000/v1")

    Raises:
        ValueError: If *provider_type* is not registered.
    """
    if provider_type == "vllm":
        from llm_race.config.vllm import VLLMProvider

        return VLLMProvider(**kwargs)
    elif provider_type == "lm_studio":
        from llm_race.config.lm_studio import LMStudioProvider

        return LMStudioProvider(**kwargs)
    elif provider_type == "mlx_lm":
        from llm_race.config.mlx_lm import MLXLMProvider

        return MLXLMProvider(**kwargs)
    elif provider_type == "ollama":
        from llm_race.config.ollama import OllamaProvider

        return OllamaProvider(**kwargs)

    raise ValueError(
        f"Unknown provider: {provider_type!r}. Available: vllm, lm_studio, mlx_lm, ollama"
    )


from llm_race.config.presets import load_preset, list_presets
