# AGENTS.md — LLM Race Project

## Language rules

- **Code, filenames, commit messages, documentation**: English only.
- **Chat with the user**: Spanish (the user communicates in Spanish).
- **Error messages, logs, CLI output**: English.

## Project overview

`llm-race` is a benchmarking tool that records historical speed tests of LLM models across different providers, machines, and workloads. The goal is to build a queryable database of performance data with a simple web viewer for comparison.

## Tech stack

- **Language**: Python 3.11+
- **Database**: SQLite (via `sqlite3` stdlib + `sqlalchemy` ORM)
- **HTTP client**: `httpx` (async support for concurrent benchmarks)
- **Web viewer**: Python `http.server` + Jinja2 templates + Chart.js for graphs
- **CLI**: `argparse` or `click`
- **No heavy framework**: keep it lightweight — no FastAPI, no Django, no React

## Architecture

```
llm_race/
├── bench/          # Benchmark runner (CLI entry point)
│   ├── cli.py          # argparse/click commands
│   ├── runner.py       # orchestrates a benchmark run
│   ├── workloads.py    # workload profiles (single-user, multi-agent, etc.)
│   └── prompts.py      # prompt templates per size category
├── db/             # Data layer
│   ├── models.py       # SQLAlchemy models (Model, Machine, Benchmark, Result)
│   ├── schema.sql      # Raw schema for reference
│   └── queries.py      # Named queries (list, compare, timeseries)
├── web/            # Web viewer
│   ├── server.py       # HTTP server entry point
│   ├── templates/      # Jinja2 HTML templates
│   └── static/         # CSS, JS (Chart.js from CDN)
├── config/         # Configuration
│   ├── providers.py    # Provider implementations (OpenAI, Anthropic, vLLM, etc.)
│   └── presets.json    # Predefined model/provider combos to test
├── utils/          # Shared utilities
│   ├── system.py       # Collect machine/GPU/OS info
│   ├── timing.py       # Token timing, latency percentiles
│   └── reporter.py     # Format results for terminal output
├── __init__.py
├── __main__.py       # Entry: python -m llm_race
└── config.py         # Global config (DB path, defaults)
data/                 # Runtime data (gitignored)
└── benchmarks.db
```

## Coding conventions

- Type hints everywhere. Use `typing` module, not string annotations.
- Async for HTTP calls (`httpx.AsyncClient`), sync for DB and file I/O.
- Error handling: fail fast with clear messages. A benchmark that silently skips is worse than one that crashes.
- Logging over print: use `logging` module, respect log levels.
- Keep imports organized: stdlib → third-party → local, blank line between groups.
- Docstrings on public functions and classes. Brief, one-liner is fine for simple functions.

## Database conventions

- All timestamps in UTC ISO 8601 (`datetime.utcnow()`).
- Token counts are integers, never floats.
- Latency in milliseconds (float).
- Tokens/sec as float, rounded to 2 decimals on display.
- Every benchmark run gets a unique `run_id` (UUID4).
- Machine info is collected once per session and cached; re-collect only when `--force-detect` is passed.

## Web viewer conventions

- Mobile-first responsive CSS, no Bootstrap.
- Chart.js from CDN for time-series and bar charts.
- Dark theme default, light theme toggle.
- All pages server-rendered (Jinja2), no SPA framework.
- Comparison view: select 2-4 runs, show side-by-side metric table + overlaid charts.

## Benchmark runner conventions

- A "run" is defined by: model + provider + machine + workload + prompt_size + concurrency.
- Each run executes N warmup iterations (default 2) + M measured iterations (default 10).
- Report: mean, median, p90, p99 for latency; mean tokens/sec; error count.
- Streaming responses: measure TTFT + inter-token latency separately.
- Non-streaming: measure total latency only.
- Provider abstraction: each provider implements `stream_complete(prompt)` and `complete(prompt)` returning token stream with timestamps.

## Git conventions

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`.
- Feature branches from `main`. No long-lived branches.
- Commit before running benchmarks — don't mix code changes with data commits (data is gitignored).

## Testing

- Unit tests for: timing utilities, DB queries, prompt generation, result formatting.
- Integration tests require a real LLM endpoint — skip by default, enable with `LLM_RACE_TEST_ENDPOINT` env var.
- Run: `python -m pytest`

## Things to get wrong the first time

- **Do not** use `openai` Python SDK for non-OpenAI providers. Use `httpx` directly against the API endpoint — every provider has slightly different streaming format.
- **Do not** assume all providers return token counts. Some require counting on the client side (split by whitespace or use a tokenizer).
- **Do not** block the event loop with sync HTTP calls during concurrent benchmarks.
- **Do not** store raw prompt/response text in the database — store hashes and sizes. Raw data is gitignored and optional.
- **Do not** hardcode provider API keys — read from env vars or a `.env` file that is gitignored.
