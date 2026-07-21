"""Import mini-SWE-agent SWE-bench results into the llm-race database."""

from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from llm_race.config import DB_PATH
from llm_race.db.models import Benchmark, init_db

logger = logging.getLogger(__name__)


def import_swebench_results(
    run_id: str,
    output_dir: str | Path,
    db_path: str | Path = DB_PATH,
) -> bool:
    """Parse mini-swe-agent output and update the Benchmark row in the database.

    Reads preds.json from the output directory, counts resolved vs total instances,
    optionally reads trajectory files for per-instance metrics, and updates the
    Benchmark row with the results.

    Args:
        run_id: UUID of the benchmark run to update.
        output_dir: Directory containing mini-swe-agent output (preds.json).
        db_path: Path to the SQLite database file.

    Returns:
        True on success, False on failure.
    """
    output_path = Path(output_dir)
    preds_file = output_path / "preds.json"

    if not preds_file.exists():
        logger.error("preds.json not found at %s", preds_file)
        return False

    try:
        preds_data: dict[str, Any] = json.loads(preds_file.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read preds.json: %s", exc)
        return False

    # Count instances
    total_instances = len(preds_data)
    if total_instances == 0:
        logger.warning("No instances found in preds.json")

    # Count resolved instances (non-empty model_patch)
    resolved_count = 0
    for instance_id, data in preds_data.items():
        model_patch = data.get("model_patch", "")
        if model_patch and model_patch.strip():
            resolved_count += 1

    # Compute resolve rate
    if total_instances > 0:
        resolve_rate = round(resolved_count / total_instances * 100, 2)
    else:
        resolve_rate = 0.0

    # Read per-instance trajectory data for additional metrics
    avg_cost_usd: float | None = None
    avg_steps: float | None = None
    avg_wall_time_s: float | None = None

    costs: list[float] = []
    steps: list[int] = []
    wall_times: list[float] = []

    for instance_id in preds_data:
        traj_file = output_path / instance_id / f"{instance_id}.traj.json"
        if not traj_file.exists():
            continue

        try:
            traj_data: dict[str, Any] = json.loads(traj_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        # Extract cost info
        info = traj_data.get("info", {})
        if isinstance(info, dict):
            # Cost might be in info or at the top level
            cost = info.get("cost")
            if cost is not None:
                try:
                    costs.append(float(cost))
                except (ValueError, TypeError):
                    pass

            # Steps / n_calls
            n_steps = info.get("n_steps") or info.get("n_calls") or info.get("steps")
            if n_steps is not None:
                try:
                    steps.append(int(n_steps))
                except (ValueError, TypeError):
                    pass

            # Wall time
            wall_time = info.get("wall_time") or info.get("wall_time_s")
            if wall_time is not None:
                try:
                    wall_times.append(float(wall_time))
                except (ValueError, TypeError):
                    pass

        # Also check top-level keys
        if "cost" in traj_data:
            try:
                costs.append(float(traj_data["cost"]))
            except (ValueError, TypeError):
                pass

    if costs:
        avg_cost_usd = round(statistics.mean(costs), 4)
    if steps:
        avg_steps = round(statistics.mean(steps), 2)
    if wall_times:
        avg_wall_time_s = round(statistics.mean(wall_times), 2)

    # Determine status
    if total_instances == 0:
        status = "error"
    elif resolved_count == total_instances:
        status = "success"
    elif resolved_count > 0:
        status = "partial"
    else:
        status = "error"

    # Update the database
    try:
        engine, session_factory = init_db(str(db_path))
        with session_factory() as session:
            benchmark = session.execute(
                select(Benchmark).where(
                    Benchmark.run_id == run_id,
                    Benchmark.benchmark_type == "swebench",
                )
            ).scalar_one_or_none()

            if benchmark is None:
                logger.error("No pending Benchmark row found for run_id=%s", run_id)
                return False

            benchmark.resolved_count = resolved_count
            benchmark.total_instances = total_instances
            benchmark.resolve_rate = resolve_rate
            benchmark.avg_cost_usd = avg_cost_usd
            benchmark.avg_steps = avg_steps
            benchmark.avg_wall_time_s = avg_wall_time_s
            benchmark.status = status
            benchmark.completed_at = datetime.utcnow()
            benchmark.total_requests = total_instances
            benchmark.successful_requests = resolved_count
            benchmark.failed_requests = total_instances - resolved_count

            session.commit()

        logger.info(
            "Imported SWE-bench results: run_id=%s, resolved=%d/%d (%.1f%%)",
            run_id, resolved_count, total_instances, resolve_rate,
        )
        return True

    except Exception:
        logger.exception("Failed to update database for run_id=%s", run_id)
        return False