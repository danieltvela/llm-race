import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_race.bench.runner import ScenarioResult  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


def format_table(results: list["ScenarioResult"]) -> str:
    header = (
        f"{'Concurrency':>12} | {'Prompt Len':>11} | {'OK/Total':>10} | "
        f"{'Wall(s)':>9} | {'RPS':>8} | {'TPS':>10} | "
        f"{'TTFT p50':>11} | {'TTFT p95':>11} | "
        f"{'E2E p50':>9} | {'E2E p95':>9} | "
        f"{'ITL p50':>9}"
    )
    sep = "-" * len(header)
    lines = [header, sep]

    for r in results:
        row = (
            f"{r.concurrency:>12} | {r.prompt_length:>11} | "
            f"{r.successful_requests}/{r.total_requests:>7} | "
            f"{r.wall_clock_seconds:>9.2f} | "
            f"{r.throughput_rps:>8.1f} | "
            f"{r.throughput_tps:>10.1f} | "
            f"{r.ttft_p50*1000:>11.0f}ms | "
            f"{r.ttft_p95*1000:>11.0f}ms | "
            f"{r.e2e_p50:>9.3f}s | "
            f"{r.e2e_p95:>9.3f}s | "
            f"{r.itl_p50*1000:>9.0f}ms"
        )
        lines.append(row)

    table = "\n".join(lines)
    logger.info("Formatted benchmark results table:\n%s", table)
    return table


def save_csv(results: list["ScenarioResult"], path: str) -> None:
    fields = [
        "concurrency", "prompt_length", "total_requests", "successful_requests",
        "failed_requests", "wall_clock_seconds", "throughput_rps", "throughput_tps",
        "ttft_mean", "ttft_p50", "ttft_p95", "ttft_p99",
        "e2e_mean", "e2e_p50", "e2e_p95", "e2e_p99", "e2e_max",
        "itl_mean", "itl_p50", "itl_p95",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    logger.info("Saved benchmark CSV to %s", path)


def save_json(results: list["ScenarioResult"], path: str) -> None:
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios": [asdict(r) for r in results],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Saved benchmark JSON to %s", path)
