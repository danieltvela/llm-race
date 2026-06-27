"""Entry point: python -m llm_race.web."""

from __future__ import annotations

import argparse
import logging

from llm_race.web.server import run_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Race Web Viewer")
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Server port (default: 8080, env: LLM_RACE_WEB_PORT)",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Bind address (default: 127.0.0.1, env: LLM_RACE_WEB_HOST)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
