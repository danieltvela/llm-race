# LLM Race

Benchmark and speed-test tracker for LLM models across different providers, machines, and workloads. Records historical performance data so you can compare models, quantizations, providers, and infrastructure over time.

## What it tracks

- **Models & variants**: base model, quantization (FP8, INT4, AWQ, GGUF Q4_K_M, etc.), context window
- **Providers**: vLLM, Ollama, LM Studio, MLX (extensible — add your own by implementing the `Provider` interface)
- **Infrastructure**: machine specs, GPU, OS, driver versions, network conditions
- **Workloads**: prompt size, expected output length, concurrency level (single user → many agents → massive concurrency)
- **Metrics**: tokens/sec (input & output), TTFT (time to first token), total latency, p50/p90/p99 latency, error rate, cost per token

## Quick start

```bash
# Create and activate virtual environment (one time)
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Run a benchmark
uv run python -m llm_race run --slug "Qwen/Qwen3.6-27B-FP8/FP8" --provider vllm --base-url http://192.168.1.47:8005/v1 --workload multi-agent

# View results in browser
uv run python -m llm_race.web --host 0.0.0.0 --port 7979
```

## Architecture

```
llm_race/
├── __init__.py
├── __main__.py              # Entry: python -m llm_race
├── bench/                   # Benchmark runner (CLI)
│   ├── cli.py               # argparse commands (run)
│   ├── runner.py            # orchestrates a benchmark run
│   ├── workloads.py         # workload profiles (single-user, multi-agent, …)
│   └── prompts.py           # prompt generation by token length
├── config/                  # Provider implementations & configuration
│   ├── __init__.py          # global config (DB path, defaults) + provider factory
│   ├── base.py              # abstract Provider base class
│   ├── vllm.py / ollama.py / lm_studio.py / mlx_lm.py
│   ├── presets.py / presets.json
├── db/                      # Data layer
│   ├── models.py            # SQLAlchemy ORM (Model, Machine, Benchmark, Result)
│   ├── schema.sql           # raw schema for reference
│   ├── queries.py           # list, compare, timeseries queries
│   ├── saver.py             # persist benchmark results
│   └── types.py             # query result dataclasses
├── data/
│   └── benchmarks.db        # SQLite database
├── utils/                   # Shared utilities
│   ├── system.py            # machine/GPU/OS info
│   ├── timing.py            # token timing, latency percentiles
│   ├── reporter.py          # format results (table, CSV, JSON)
│   └── sse.py               # SSE stream parser for OpenAI-compatible APIs
└── web/                     # Web viewer
    ├── __main__.py          # Entry: python -m llm_race.web
    ├── server.py            # HTTP server (http.server + Jinja2)
    ├── static/style.css     # Dark-theme CSS
    └── templates/           # Jinja2 templates
        ├── base.html
        ├── index.html       # benchmark list with filters
        ├── compare.html     # side-by-side comparison
        └── timeseries.html  # performance charts (Chart.js)
```

## Workload profiles

| Profile | Description | Concurrency |
|---------|-------------|-------------|
| `single-user` | Single request, measure raw latency | 1 |
| `chat` | Conversational flow with context growth | 1 |
| `multi-agent` | Multiple independent agents running in parallel | 4-16 |
| `high-throughput` | Many users hitting the endpoint simultaneously | 32-128 |
| `stress` | Maximum concurrency until degradation | 256+ |

## Prompt sizes

| Prompt tokens | Use case |
|---------------|----------|
| 64 | Short commands, quick queries |
| 512 | Code snippets, short documents |
| 2048 | Document analysis, moderate context |
| 4096 | Large files, extended conversation |

Prompt lengths are passed as integer values (`--prompt-lengths 64 512 2048 4096`).
Custom prompt templates can be added in `llm_race/bench/prompts.py`.

## Database

SQLite database at `llm_race/data/benchmarks.db`. Schema includes:
- `models`: model name, version, quantization, provider
- `machines`: hardware specs, OS, GPU info
- `benchmarks`: test runs with workload profile, prompt size, concurrency
- `results`: per-run metrics (tokens/sec, latency percentiles, errors)

## Web viewer

Lightweight web interface for:
- Listing all benchmarks with filters (model, provider, machine, date range)
- Side-by-side comparison of two or more runs
- Time-series charts showing performance over time
- Export results as CSV

## Contributing

Code and documentation in English. Feel free to add new providers, workload profiles, or metrics.
