"""Timing and percentile helpers for benchmark results."""

import numpy as np


def compute_latency_stats(values: list[float]) -> dict[str, float]:
    arr = np.array(values) if values else np.array([])
    if len(arr) == 0:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
    }


def compute_itl_stats(inter_token_times: list[float]) -> dict[str, float | None]:
    arr = np.array(inter_token_times) if inter_token_times else np.array([])
    if len(arr) == 0:
        return {"mean": None, "p50": None, "p95": None, "p99": None}
    return {
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
    }
