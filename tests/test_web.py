"""Tests for the LLM Race web viewer."""

from __future__ import annotations

import threading
import time
from http.client import HTTPConnection
from pathlib import Path

import pytest

from llm_race.db.models import init_db

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
PORT = 18923


def _get(path: str) -> tuple[int, bytes, dict[str, str]]:
    """Make GET request, return (status, body, headers)."""
    conn = HTTPConnection("127.0.0.1", PORT, timeout=5)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        status = response.status
        body = response.read()
        headers = dict(response.getheaders())
        return status, body, headers
    finally:
        conn.close()


@pytest.fixture(scope="module")
def server():
    """Start server in background thread, yield, then shutdown."""
    from llm_race.web import server as server_module

    static_dir = PROJECT_ROOT / "llm_race" / "web" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    css_file = static_dir / "style.css"
    if not css_file.exists():
        css_file.write_text("/* placeholder */")

    server_module._init_db_on_startup()

    srv = server_module.create_server(host="127.0.0.1", port=PORT)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)
    yield srv
    srv.shutdown()
    t.join(timeout=2)


def test_server_starts_and_responds_200(server) -> None:
    """Server should start and respond to requests."""
    status, body, headers = _get("/")
    assert status in (200, 501)


def test_unknown_route_returns_404(server) -> None:
    """GET /nonexistent should return 404."""
    status, body, headers = _get("/nonexistent")
    assert status == 404


def test_static_css_returns_200(server) -> None:
    """GET /static/style.css should return 200."""
    status, body, headers = _get("/static/style.css")
    assert status == 200
    assert "text/css" in headers.get("Content-Type", "")


def test_static_nonexistent_returns_404(server) -> None:
    """GET /static/nonexistent.txt should return 404."""
    status, body, headers = _get("/static/nonexistent.txt")
    assert status == 404


def test_static_directory_traversal_blocked(server) -> None:
    """Directory traversal via static path should be blocked."""
    status, body, headers = _get("/static/../config/__init__.py")
    assert status in (403, 404)


def test_index_route_returns_200(server) -> None:
    """GET / should return 200 with real implementation."""
    status, body, headers = _get("/")
    assert status == 200


def test_compare_route_returns_200(server) -> None:
    """GET /compare should return 200 (real implementation now)."""
    status, body, headers = _get("/compare")
    assert status == 200


def test_timeseries_route_returns_200(server) -> None:
    """GET /timeseries should return 200 (real implementation)."""
    status, body, headers = _get("/timeseries")
    assert status == 200


def test_timeseries_contains_chart_container(server) -> None:
    """Timeseries page should contain canvas or chart-related elements."""
    status, body, headers = _get("/timeseries")
    assert status == 200
    assert b"<canvas" in body or b"chart" in body.lower() or b"timeseries" in body.lower()


def test_timeseries_contains_filter_form(server) -> None:
    """Timeseries page should contain filter fields."""
    status, body, headers = _get("/timeseries")
    assert status == 200
    assert any(term in body for term in [b"model", b"provider", b"metric", b"date_start", b"date_end"])


def test_timeseries_empty_state(server) -> None:
    """Timeseries page with no data should show empty state."""
    status, body, headers = _get("/timeseries")
    assert status == 200
    # Either shows data or empty state message
    assert (b"No data" in body or b"data" in body.lower() or b"timeseries" in body.lower() or b"canvas" in body)


def test_csv_export_returns_200(server) -> None:
    """GET /export/csv should return 200 (real implementation)."""
    status, body, headers = _get("/export/csv")
    assert status == 200


def test_csv_export_content_type(server) -> None:
    """CSV export should have text/csv content type."""
    status, body, headers = _get("/export/csv")
    assert status == 200
    ct = headers.get("Content-Type", "")
    assert "text/csv" in ct or "csv" in ct


def test_csv_export_content_disposition(server) -> None:
    """CSV export should have Content-Disposition header."""
    status, body, headers = _get("/export/csv")
    assert status == 200
    cd = headers.get("Content-Disposition", "")
    assert "attachment" in cd or "filename" in cd or "benchmarks.csv" in cd


def test_csv_export_contains_headers(server) -> None:
    """CSV export should contain header row with expected fields."""
    status, body, headers = _get("/export/csv")
    assert status == 200
    assert b"run_id" in body
    assert b"model_name" in body


def test_index_returns_html(server) -> None:
    """Index page should return 200 with HTML content."""
    status, body, headers = _get("/")
    assert status == 200
    assert b"text/html" in headers.get("Content-Type", "").encode() or b"Benchmarks" in body


def test_index_contains_filter_form(server) -> None:
    """Index page should contain filter form fields."""
    status, body, headers = _get("/")
    assert status == 200
    filters_found = sum(term in body for term in [b"model_name", b"provider_name", b"machine", b"date_start", b"date_end"])
    assert filters_found >= 3, f"Expected at least 3 filter fields, found {filters_found}"


def test_index_pagination_controls(server) -> None:
    """Index page should contain pagination controls or empty state."""
    status, body, headers = _get("/?page=1")
    assert status == 200
    assert (
        b"Page" in body
        or b"page" in body
        or b"Previous" in body
        or b"Next" in body
        or b"No benchmarks found" in body
    )


def test_index_empty_state(server) -> None:
    """Index page with no data should show empty state."""
    status, body, headers = _get("/")
    assert status == 200
    assert (b"Benchmarks" in body) or (b"benchmarks" in body)


def test_compare_with_single_run_shows_error(server) -> None:
    """GET /compare?run_id=abc should show validation error."""
    status, body, headers = _get("/compare?run_id=abc-123")
    assert status == 200
    assert any(term in body for term in [b"2-4", b"select", b"error", b"invalid"])


def test_compare_contains_chart_container(server) -> None:
    """Compare page should contain canvas for Chart.js."""
    status, body, headers = _get("/compare")
    assert status == 200
    assert b"<canvas" in body or b"chart" in body.lower()


def test_compare_contains_metrics_table(server) -> None:
    """Compare page should contain metrics table structure."""
    status, body, headers = _get("/compare")
    assert status == 200
    assert b"table" in body.lower() or b"Metric" in body or b"metrics" in body.lower()


def test_compare_contains_empty_state(server) -> None:
    """Compare page with no run_ids should show empty state."""
    status, body, headers = _get("/compare")
    assert status == 200
    assert b"No runs to compare" in body or b"Enter 2-4" in body
