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
from llm_race.db.models import init_db

logger = logging.getLogger(__name__)

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
        self._send_501()

    def handle_compare(self, params: dict[str, list[str]]) -> None:
        self._send_501()

    def handle_timeseries(self, params: dict[str, list[str]]) -> None:
        self._send_501()

    def handle_csv_export(self, params: dict[str, list[str]]) -> None:
        self._send_501()

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
