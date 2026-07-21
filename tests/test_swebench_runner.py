"""Unit tests for SWE-bench launch script generation."""

import pytest

from llm_race.bench.swebench_runner import generate_swebench_launch_script


class TestGenerateSwebenchLaunchScript:
    """Tests for generate_swebench_launch_script."""

    def test_basic_script_contains_install(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "pip install mini-swe-agent" in script
        assert "pip3 install mini-swe-agent" in script

    def test_script_contains_swebench_command(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "mini-extra swebench" in script
        assert "--model openai/gpt-4o" in script
        assert "--subset lite" in script
        assert "--split dev" in script
        assert "--workers 1" in script

    def test_script_contains_import_command(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "python3 -m llm_race import" in script
        assert "--run-id test-run-id-123" in script

    def test_script_with_slice(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="verified",
            split="test",
            workers=4,
            instances="0:5",
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "--subset verified" in script
        assert "--split test" in script
        assert "--workers 4" in script
        assert "--slice 0:5" in script

    def test_script_with_base_url(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="qwen/qwen3-8b/none",
            base_url="http://localhost:8000/v1",
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "--config model.model_kwargs.api_base=http://localhost:8000/v1" in script

    def test_script_with_singularity_env(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="singularity",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "--environment-class singularity" in script

    def test_script_has_shebang(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert script.startswith("#!/usr/bin/env bash")
        assert "set -euo pipefail" in script

    def test_instances_all_does_not_add_slice(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="openai/gpt-4o/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances="all",
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "--slice" not in script

    def test_model_name_derived_from_slug(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="anthropic/claude-3-opus/none",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "--model anthropic/claude-3-opus" in script

    def test_model_name_with_extra(self) -> None:
        script = generate_swebench_launch_script(
            model_slug="meta/llama-3.1-8b/fp8/agent",
            base_url=None,
            subset="lite",
            split="dev",
            workers=1,
            instances=None,
            environment="docker",
            run_id="test-run-id-123",
            db_path="/tmp/test.db",
        )
        assert "--model meta/llama-3.1-8b" in script