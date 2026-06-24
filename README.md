# LLM Race

Benchmark and speed-test tracker for LLM models across different providers, machines, and workloads. Records historical performance data so you can compare models, quantizations, providers, and infrastructure over time.

## What it tracks

- **Models & variants**: base model, quantization (FP8, INT4, AWQ, GGUF Q4_K_M, etc.), context window
- **Providers**: OpenAI, Anthropic, xAI, local vLLM, Ollama, LM Studio, custom endpoints
- **Infrastructure**: machine specs, GPU, OS, driver versions, network conditions
- **Workloads**: prompt size, expected output length, concurrency level (single user → many agents → massive concurrency)
- **Metrics**: tokens/sec (input & output), TTFT (time to first token), total latency, p50/p90/p99 latency, error rate, cost per token

## Quick start

```bash
cd projects/ai/llm-race
pip install -r requirements.txt

# Run a benchmark
python -m llm_race.bench run --model "qwen3.6-27b-fp8" --provider vllm --endpoint http://192.168.1.47:8005

# View results in browser
python -m llm_race.web
```

## Architecture

```
llm_race/
├── bench/          # Benchmark runner (CLI)
├── db/             # SQLite schema & queries
├── web/            # Web viewer (static HTML + Python server)
├── config/         # Model presets, provider configs
└── utils/          # System info collection, timing helpers
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

| Size | Tokens (approx) | Use case |
|------|-----------------|----------|
| `tiny` | 10-50 | Quick commands, tool calls |
| `small` | 100-500 | Short questions, code snippets |
| `medium` | 500-2000 | Document analysis, longer context |
| `large` | 2000-8000 | Full files, extended conversation |
| `max` | 8000+ | Near-context-limit workloads |

## Database

SQLite database at `data/benchmarks.db`. Schema includes:
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
