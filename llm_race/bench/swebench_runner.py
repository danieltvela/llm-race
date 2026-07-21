"""Launch script generator for mini-SWE-agent SWE-bench benchmarks."""

from __future__ import annotations

from llm_race.utils.slug import parse_slug


def generate_swebench_launch_script(
    model_slug: str,
    base_url: str | None,
    subset: str,
    split: str,
    workers: int,
    instances: str | None,
    environment: str,
    run_id: str,
    db_path: str,
) -> str:
    """Generate a self-contained bash script that runs mini-SWE-agent SWE-bench.

    The script installs mini-swe-agent if not present, runs the benchmark,
    and imports results back into the llm-race database.

    Args:
        model_slug: Model slug (e.g. "openai/gpt-4o/none").
        base_url: Optional custom API base URL.
        subset: SWE-bench subset (e.g. "lite", "verified", "full").
        split: Dataset split (e.g. "dev", "test").
        workers: Number of parallel workers.
        instances: Slice specification (e.g. "0:5") or None.
        environment: Environment type (docker, singularity, local).
        run_id: UUID of the benchmark run.
        db_path: Path to the llm-race database file.

    Returns:
        A bash script string.
    """
    parsed = parse_slug(model_slug)
    swebench_model_name = f"{parsed['ai_lab']}/{parsed['name']}"
    output_dir = f"/tmp/swebench_{run_id[:8]}"

    # Build mini-extra swebench command
    cmd_parts = [
        "mini-extra swebench",
        f"--model {swebench_model_name}",
        f"--subset {subset}",
        f"--split {split}",
        f"--workers {workers}",
        f"--output {output_dir}",
    ]

    if instances is not None and instances != "all":
        cmd_parts.append(f"--slice {instances}")

    if environment != "docker":
        cmd_parts.append(f"--environment-class {environment}")

    if base_url is not None:
        cmd_parts.append(f"--config model.model_kwargs.api_base={base_url}")

    cmd = " \\\n    ".join(cmd_parts)

    script = f"""#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# LLM Race — SWE-bench Launch Script
# Run ID: {run_id}
# Model:  {swebench_model_name}
# Slug:   {model_slug}
# Subset: {subset} | Split: {split} | Workers: {workers}
# Env:    {environment}
# ============================================================

echo "=========================================="
echo "LLM Race — SWE-bench Benchmark"
echo "=========================================="
echo "Run ID:  {run_id}"
echo "Model:   {swebench_model_name}"
echo "Subset:  {subset}"
echo "Split:   {split}"
echo "Workers: {workers}"
echo "Env:     {environment}"
echo "=========================================="

    # ── Docker environment checks ──────────────────────────────────
if [ "{environment}" = "docker" ]; then
    if ! command -v docker &>/dev/null; then
        echo ""
        echo "ERROR: Docker is not installed."
        echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
        echo "Or use --swebench-environment local to run without Docker (less secure)."
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        echo ""
        echo "ERROR: Docker daemon is not running."
        echo ""
        if command -v colima &>/dev/null; then
            echo "Colima detected. Start it with:"
            echo "  colima start --arch x86_64"
            echo "  colima start --arch aarch64 --vm-type vz --vz-rosetta"
        else
            echo "Start Docker Desktop and re-run this script."
        fi
        echo ""
        echo "Or skip Docker entirely:"
        echo "  python3 -m llm_race run --benchmark-type swebench --swebench-environment local ..."
        exit 1
    fi

    # ── Colima on Apple Silicon ─────────────────────────────────
    # SWE-bench Docker images are x86_64-only.
    # Colima must be running an x86_64 VM or ARM64+Rosetta VM.
    if command -v colima &>/dev/null; then
        echo ""
        echo "Colima detected."

        # Check current Colima architecture
        COLIMA_ARCH=$(colima status 2>/dev/null | grep -o 'arch: [^ ]*' | cut -d' ' -f2 || echo "")

        if [ "$COLIMA_ARCH" = "aarch64" ] || [ -z "$COLIMA_ARCH" ]; then
            # Check if Rosetta is available (macOS 13+ with VZ)
            if [ "$(uname -m)" = "arm64" ] && [ -e "/Library/Apple/usr/libexec/oah/libRosettaRuntime" ]; then
                echo ""
                echo "WARNING: Colima is running in ARM64 mode, but SWE-bench images are x86_64 only."
                echo ""
                echo "Your Colima VM needs x86_64 support. Choose one:"
                echo ""
                echo "  Option A (recommended, fast): x86_64 VM"
                echo "    colima stop"
                echo "    colima start --arch x86_64"
                echo ""
                echo "  Option B (ARM64 + Rosetta):"
                echo "    colima stop"
                echo "    colima start --arch aarch64 --vm-type vz --vz-rosetta"
                echo ""
                echo "Or use the local environment (no Docker):"
                echo "  python3 -m llm_race run --benchmark-type swebench --swebench-environment local ..."
                exit 1
            fi
        fi
    fi

    # Apple Silicon (ARM64) macOS: set platform emulation for x86_64 images.
    # Docker Desktop handles this with Rosetta; Colima with --arch x86_64.
    UNAME_M=$(uname -m 2>/dev/null || echo "")
    case "$UNAME_M" in
        arm64|aarch64)
            echo ""
            echo "Detected ARM64 architecture (Apple Silicon)."
            echo "Setting DOCKER_DEFAULT_PLATFORM=linux/amd64 for x86_64 SWE-bench containers."
            export DOCKER_DEFAULT_PLATFORM=linux/amd64
            ;;
    esac

    echo ""
    echo "Docker is ready."
fi

# ── Install mini-swe-agent ────────────────────────────────────
if ! python3 -c "import minisweagent" 2>/dev/null; then
    echo ""
    echo "mini-swe-agent not found. Installing..."
    if command -v pip3 &>/dev/null; then
        pip3 install mini-swe-agent
    elif command -v pip &>/dev/null; then
        pip install mini-swe-agent
    else
        echo "Error: pip or pip3 not found. Install mini-swe-agent manually."
        exit 1
    fi
    echo "mini-swe-agent installed."
fi

# ── Create output directory ───────────────────────────────────
mkdir -p {output_dir}

# ── Run SWE-bench evaluation ──────────────────────────────────
echo ""
echo "Starting SWE-bench evaluation..."
echo ""

{cmd}

echo ""
echo "SWE-bench evaluation complete."

# ── Import results into llm-race database ─────────────────────
echo ""
echo "Importing results into llm-race database..."
python3 -m llm_race import --run-id {run_id} --output-dir {output_dir} --db {db_path}

echo ""
echo "=========================================="
echo "Benchmark complete. Results imported with run_id: {run_id}"
echo "View at: http://127.0.0.1:8080/run/{run_id}"
echo "=========================================="
"""
    return script