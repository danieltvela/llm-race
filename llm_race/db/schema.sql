-- Raw SQLite schema for llm-race benchmark database.
-- PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug VARCHAR(500) NOT NULL,
    ai_lab VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    quantization VARCHAR(50),
    extra VARCHAR(100),
    provider_name VARCHAR(100) NOT NULL,
    context_window INTEGER,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    UNIQUE(slug)
);

CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname VARCHAR(255) NOT NULL,
    cpu VARCHAR(255),
    gpu VARCHAR(255),
    gpu_count INTEGER,
    ram_gb FLOAT,
    os VARCHAR(100),
    os_version VARCHAR(100),
    driver_version VARCHAR(100),
    python_version VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    UNIQUE(hostname)
);

CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(36) NOT NULL,
    model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    workload_profile VARCHAR(50) NOT NULL,
    prompt_size VARCHAR(20) NOT NULL,
    prompt_token_count INTEGER,
    prompt_hash VARCHAR(64),
    prompt_text_size INTEGER,
    concurrency INTEGER NOT NULL,
    max_tokens INTEGER NOT NULL,
    temperature FLOAT NOT NULL,
    top_p FLOAT NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    wall_clock_seconds FLOAT,
    total_requests INTEGER NOT NULL DEFAULT 0,
    successful_requests INTEGER NOT NULL DEFAULT 0,
    failed_requests INTEGER NOT NULL DEFAULT 0,
    throughput_rps FLOAT,
    throughput_tps FLOAT,
    e2e_mean_ms FLOAT,
    e2e_p50_ms FLOAT,
    e2e_p90_ms FLOAT,
    e2e_p99_ms FLOAT,
    ttft_mean_ms FLOAT,
    ttft_p50_ms FLOAT,
    ttft_p90_ms FLOAT,
    ttft_p99_ms FLOAT,
    itl_mean_ms FLOAT,
    itl_p50_ms FLOAT,
    itl_p90_ms FLOAT,
    itl_p99_ms FLOAT,
    cost_per_token FLOAT,
    pp_mean FLOAT,
    pp_p50 FLOAT,
    pp_p90 FLOAT,
    pp_p99 FLOAT,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_benchmarks_run_id ON benchmarks(run_id);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_id INTEGER NOT NULL REFERENCES benchmarks(id) ON DELETE CASCADE,
    request_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    ttft_ms FLOAT,
    e2e_latency_ms FLOAT,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    tokens_per_second FLOAT,
    pp FLOAT,
    itl_mean FLOAT,
    itl_p50 FLOAT,
    itl_p90 FLOAT,
    itl_p99 FLOAT,
    cost_per_token FLOAT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id) ON DELETE CASCADE,
    UNIQUE(benchmark_id, request_id)
);