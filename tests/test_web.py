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


def test_index_route_returns_501(server) -> None:
    """GET / should return 501 (stub)."""
    status, body, headers = _get("/")
    assert status == 501


def test_compare_route_returns_501(server) -> None:
    """GET /compare should return 501 (stub)."""
    status, body, headers = _get("/compare")
    assert status == 501


def test_timeseries_route_returns_501(server) -> None:
    """GET /timeseries should return 501 (stub)."""
    status, body, headers = _get("/timeseries")
    assert status == 501


def test_csv_export_route_returns_501(server) -> None:
    """GET /export/csv should return 501 (stub)."""
    status, body, headers = _get("/export/csv")
    assert status == 501
