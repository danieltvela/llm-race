"""HTTP server for LLM Race benchmark viewer.

Serves Jinja2-rendered HTML pages at:
- /            — benchmark list with filters
- /compare     — side-by-side comparison
- /timeseries  — performance charts
- /export/csv  — CSV download
"""

from __future__ import annotations

import http.server
import json
import logging
import mimetypes
import os
import posixpath
from datetime import datetime, date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from jinja2 import Environment, FileSystemLoader, PackageLoader

from llm_race.config import DB_PATH, WEB_HOST, WEB_PORT
from llm_race.db.models import init_db, Model, Machine, Benchmark
from collections import OrderedDict

from llm_race.db.types import BenchmarkFilters
from llm_race.db.queries import list_benchmarks, compare_runs, timeseries

logger = logging.getLogger(__name__)


def _fmt(val: float | int | None) -> str:
    if val is None:
        return ""
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


HERE = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> str:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)


_engine = None
_SessionFactory = None


def _init_db_on_startup() -> None:
    global _engine, _SessionFactory
    _engine, _SessionFactory = init_db(str(DB_PATH))
    logger.info("Database initialized at %s", DB_PATH)


def _get_db_session():
    from contextlib import contextmanager
    from sqlalchemy.orm import Session

    @contextmanager
    def _session():
        if _SessionFactory is None:
            raise RuntimeError("Database not initialized. Call _init_db_on_startup() first.")
        session: Session = _SessionFactory()
        try:
            yield session
        finally:
            session.close()

    return _session()


class BenchmarkHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("HTTP %s", format % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        try:
            if path == "/":
                self.handle_index(params)
            elif path == "/compare":
                self.handle_compare(params)
            elif path == "/timeseries":
                self.handle_timeseries(params)
            elif path == "/export/csv":
                self.handle_csv_export(params)
            elif path.startswith("/static/"):
                self.serve_static(path)
            else:
                self.send_error(404, "Not Found")
        except Exception as exc:
            logger.exception("Error handling %s", path)
            self.send_error(500, f"Internal Server Error: {exc}")

    def handle_index(self, params: dict[str, list[str]]) -> None:
        model_name = params.get("model_name", [None])[0]
        provider_name = params.get("provider_name", [None])[0]
        machine_hostname = params.get("machine_hostname", [None])[0]
        date_start_str = params.get("date_start", [None])[0]
        date_end_str = params.get("date_end", [None])[0]
        status = params.get("status", [None])[0]
        workload_profile = params.get("workload_profile", [None])[0]
        prompt_size = params.get("prompt_size", [None])[0]

        page = int(params.get("page", ["1"])[0])
        limit = int(params.get("limit", ["20"])[0])
        sort_by = params.get("sort_by", ["started_at"])[0]
        sort_order = params.get("sort_order", ["desc"])[0]

        date_start = datetime.fromisoformat(date_start_str) if date_start_str else None
        date_end = datetime.fromisoformat(date_end_str) if date_end_str else None

        filters = BenchmarkFilters(
            model_name=model_name,
            provider_name=provider_name,
            machine_hostname=machine_hostname,
            date_start=date_start,
            date_end=date_end,
            status=status,
            workload_profile=workload_profile,
            prompt_size=prompt_size,
        )

        with _get_db_session() as session:
            result = list_benchmarks(
                session,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                offset=(page - 1) * limit,
                limit=limit,
            )

            total_pages = max(1, (result.total_count + limit - 1) // limit)
            has_prev = page > 1
            has_next = page < total_pages

            model_names = [row[0] for row in session.query(Model.name).distinct().order_by(Model.name).all()]
            provider_names = [row[0] for row in session.query(Model.provider_name).distinct().order_by(Model.provider_name).all()]
            machine_hostnames = [row[0] for row in session.query(Machine.hostname).distinct().order_by(Machine.hostname).all()]

            html = jinja_env.get_template("index.html").render(
                benchmarks=result.items,
                total_count=result.total_count,
                page=page,
                limit=limit,
                total_pages=total_pages,
                has_prev=has_prev,
                has_next=has_next,
                prev_page=page - 1 if has_prev else 1,
                next_page=page + 1 if has_next else page,
                filters=filters,
                model_names=model_names,
                provider_names=provider_names,
                machine_hostnames=machine_hostnames,
                sort_by=sort_by,
                sort_order=sort_order,
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_html(self, html: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def handle_compare(self, params: dict[str, list[str]]) -> None:
        run_ids = params.get("run_id", [])
        if len(run_ids) == 1 and "," in run_ids[0]:
            run_ids = run_ids[0].split(",")
        run_ids = [r.strip() for r in run_ids if r.strip()]

        if not run_ids:
            html = jinja_env.get_template("compare.html").render(
                error=None,
                runs=[],
                metrics_table={},
                chart_data={},
                run_ids=run_ids,
            )
            self._send_html(html)
            return

        if len(run_ids) < 2 or len(run_ids) > 4:
            error = "Please select 2 to 4 benchmark runs to compare."
            html = jinja_env.get_template("compare.html").render(
                error=error,
                runs=[],
                metrics_table={},
                chart_data={},
                run_ids=run_ids,
            )
            self._send_html(html)
            return

        with _get_db_session() as session:
            runs = compare_runs(session, run_ids)

            if not runs:
                error = "No benchmark runs found for the given IDs."
                html = jinja_env.get_template("compare.html").render(
                    error=error,
                    runs=[],
                    metrics_table={},
                    chart_data={},
                    run_ids=run_ids,
                )
                self._send_html(html)
                return

            metrics_table = OrderedDict()
            metrics_table["Model"] = [r.model_name for r in runs]
            metrics_table["Provider"] = [r.provider_name for r in runs]
            metrics_table["Machine"] = [r.hostname for r in runs]
            metrics_table["Throughput (TPS)"] = [
                round(r.throughput_tps, 1) if r.throughput_tps is not None else None
                for r in runs
            ]
            metrics_table["E2E Mean (ms)"] = [
                round(r.e2e_mean_ms, 1) if r.e2e_mean_ms is not None else None
                for r in runs
            ]
            metrics_table["E2E P50 (ms)"] = [
                round(r.e2e_p50_ms, 1) if r.e2e_p50_ms is not None else None
                for r in runs
            ]
            metrics_table["E2E P90 (ms)"] = [
                round(r.e2e_p90_ms, 1) if r.e2e_p90_ms is not None else None
                for r in runs
            ]
            metrics_table["E2E P99 (ms)"] = [
                round(r.e2e_p99_ms, 1) if r.e2e_p99_ms is not None else None
                for r in runs
            ]
            metrics_table["Total Requests"] = [r.total_requests for r in runs]
            metrics_table["Success Rate (%)"] = [
                round(r.successful_requests / r.total_requests * 100, 1)
                if r.total_requests else None
                for r in runs
            ]
            metrics_table["Wall Clock (s)"] = [
                round(r.wall_clock_seconds, 1) if r.wall_clock_seconds is not None else None
                for r in runs
            ]

            chart_metrics = [
                "Throughput (TPS)",
                "E2E Mean (ms)",
                "E2E P50 (ms)",
                "E2E P90 (ms)",
                "E2E P99 (ms)",
            ]
            chart_datasets = []
            colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"]
            for i, run in enumerate(runs):
                color = colors[i % 4]
                data = [metrics_table[m][i] for m in chart_metrics]
                chart_datasets.append(
                    {
                        "label": run.model_name[:20],
                        "data": data,
                        "backgroundColor": color,
                        "borderColor": color,
                        "borderWidth": 1,
                    }
                )
            chart_data = {"labels": chart_metrics, "datasets": chart_datasets}

            html = jinja_env.get_template("compare.html").render(
                runs=runs,
                metrics_table=metrics_table,
                chart_data=chart_data,
                error=None,
                run_ids=run_ids,
            )
            self._send_html(html)

    def handle_timeseries(self, params: dict[str, list[str]]) -> None:
        model = params.get("model", [None])[0]
        provider = params.get("provider", [None])[0]
        metric = params.get("metric", ["throughput_tps"])[0]
        date_start_str = params.get("date_start", [None])[0]
        date_end_str = params.get("date_end", [None])[0]
        level = params.get("level", ["benchmark"])[0]

        date_start = datetime.fromisoformat(date_start_str) if date_start_str else None
        date_end = datetime.fromisoformat(date_end_str) if date_end_str else None

        allowed_metrics = [
            "throughput_tps", "tokens_per_second", "e2e_mean_ms", "e2e_p50_ms",
            "e2e_p90_ms", "e2e_p99_ms", "wall_clock_seconds", "total_tokens",
            "total_requests", "successful_requests", "failed_requests",
        ]

        with _get_db_session() as session:
            model_options = [row[0] for row in session.query(Model.name).distinct().order_by(Model.name).all()]
            provider_options = [row[0] for row in session.query(Model.provider_name).distinct().order_by(Model.provider_name).all()]

            if metric not in allowed_metrics:
                error = f"Invalid metric '{metric}'. Allowed: {', '.join(allowed_metrics)}"
                html = jinja_env.get_template("timeseries.html").render(
                    points=[],
                    metric_options=allowed_metrics,
                    model_options=model_options,
                    provider_options=provider_options,
                    selected_model=model or "",
                    selected_provider=provider or "",
                    selected_metric=metric,
                    date_start=date_start_str or "",
                    date_end=date_end_str or "",
                    error=error,
                    total_points=0,
                )
                self._send_html(html)
                return

            points = timeseries(session, model, provider, metric, date_start, date_end, level)

            chart_points = [
                {
                    "date": p.date.isoformat() if p.date else None,
                    "value": round(p.value, 2) if p.value is not None else None,
                    "run_id": p.run_id,
                    "label": p.label,
                }
                for p in points
            ]

            html = jinja_env.get_template("timeseries.html").render(
                points=chart_points,
                metric_options=allowed_metrics,
                model_options=model_options,
                provider_options=provider_options,
                selected_model=model or "",
                selected_provider=provider or "",
                selected_metric=metric,
                date_start=date_start_str or "",
                date_end=date_end_str or "",
                error=None,
                total_points=len(points),
            )
            self._send_html(html)

    def handle_csv_export(self, params: dict[str, list[str]]) -> None:
        import csv
        import io

        run_id = params.get("run_id", [None])[0]

        with _get_db_session() as session:
            if run_id:
                rows = compare_runs(session, [run_id])
            else:
                result = list_benchmarks(session, filters=None, offset=0, limit=10000)
                rows = result.items

            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow([
                "run_id", "model_name", "provider_name", "hostname",
                "workload_profile", "prompt_size", "concurrency",
                "started_at", "completed_at", "wall_clock_seconds",
                "total_requests", "successful_requests", "failed_requests",
                "throughput_tps", "tokens_per_second",
                "e2e_mean_ms", "e2e_p50_ms", "e2e_p90_ms", "e2e_p99_ms",
                "ttft_mean_ms", "itl_mean_ms", "total_tokens", "status",
            ])

            for r in rows:
                writer.writerow([
                    r.run_id,
                    r.model_name,
                    r.provider_name,
                    r.hostname,
                    r.workload_profile,
                    r.prompt_size,
                    r.concurrency,
                    r.started_at.isoformat() if hasattr(r, "started_at") and r.started_at else "",
                    r.completed_at.isoformat() if hasattr(r, "completed_at") and r.completed_at else "",
                    r.wall_clock_seconds if hasattr(r, "wall_clock_seconds") else "",
                    r.total_requests if hasattr(r, "total_requests") else "",
                    r.successful_requests if hasattr(r, "successful_requests") else "",
                    r.failed_requests if hasattr(r, "failed_requests") else "",
                    _fmt(r.throughput_tps),
                    _fmt(getattr(r, "tokens_per_second", None)),
                    _fmt(r.e2e_mean_ms),
                    _fmt(getattr(r, "e2e_p50_ms", None)),
                    _fmt(getattr(r, "e2e_p90_ms", None)),
                    _fmt(getattr(r, "e2e_p99_ms", None)),
                    _fmt(getattr(r, "ttft_mean_ms", None)),
                    _fmt(getattr(r, "itl_mean_ms", None)),
                    getattr(r, "total_tokens", ""),
                    getattr(r, "status", ""),
                ])

            csv_content = output.getvalue()

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="benchmarks.csv"')
        self.send_header("Content-Length", str(len(csv_content.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(csv_content.encode("utf-8"))

    def _send_501(self) -> None:
        self.send_response(501)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>501 Not Implemented</h1></body></html>")

    def serve_static(self, path: str) -> None:
        rel_path = path[len("/static/"):]
        rel_path = posixpath.normpath(rel_path)
        if rel_path.startswith("..") or rel_path.startswith("/"):
            self.send_error(403, "Forbidden")
            return

        file_path = STATIC_DIR / rel_path
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError as exc:
            self.send_error(500, f"Error reading file: {exc}")


def create_server(host: str = WEB_HOST, port: int = WEB_PORT) -> http.server.HTTPServer:
    server = http.server.HTTPServer((host, port), BenchmarkHTTPHandler)
    logger.info("Server created at %s:%d", host, port)
    return server


def run_server(host: str = WEB_HOST, port: int = WEB_PORT, debug: bool = False) -> None:
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    logger.info("Initializing LLM Race Web Viewer on %s:%d", host, port)
    _init_db_on_startup()

    server = create_server(host, port)
    logger.info("Serving at http://%s:%d/", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
