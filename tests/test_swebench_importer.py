"""Unit tests for SWE-bench results importer."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from llm_race.bench.swebench_importer import import_swebench_results
from llm_race.db.models import Benchmark, Machine, Model, init_db


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Create a temporary database."""
    db_file = tmp_path / "test.db"
    engine, session_factory = init_db(db_file)
    return db_file


@pytest.fixture
def pending_benchmark(db_path: Path) -> str:
    """Create a pending SWE-bench benchmark row and return its run_id."""
    engine, session_factory = init_db(db_path)
    with session_factory() as session:
        model = Model(
            slug="openai/gpt-4o/none",
            ai_lab="openai",
            name="gpt-4o",
            quantization="none",
            provider_name="litellm",
        )
        session.add(model)
        session.flush()

        machine = Machine(hostname="test-host")
        session.add(machine)
        session.flush()

        benchmark = Benchmark(
            run_id="test-run-id-123",
            model_id=model.id,
            machine_id=machine.id,
            benchmark_type="swebench",
            workload_profile="swebench",
            prompt_size="n/a",
            concurrency=1,
            max_tokens=0,
            temperature=0.0,
            top_p=1.0,
            started_at=datetime.utcnow(),
            status="running",
            swebench_subset="lite",
            swebench_split="dev",
            swebench_model_name="openai/gpt-4o",
        )
        session.add(benchmark)
        session.commit()

    return "test-run-id-123"


class TestImportSwebenchResults:
    """Tests for the SWE-bench results importer."""

    def test_import_basic_results(self, db_path: Path, pending_benchmark: str, tmp_path: Path) -> None:
        """Import results with 2 resolved and 1 unresolved instance."""
        preds = {
            "sympy__sympy-15599": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "sympy__sympy-15599",
                "model_patch": "diff --git a/foo.py b/foo.py\nnew content",
            },
            "django__django-12345": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "django__django-12345",
                "model_patch": "diff --git a/bar.py b/bar.py\nnew content",
            },
            "flask__flask-67890": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "flask__flask-67890",
                "model_patch": "",
            },
        }
        preds_file = tmp_path / "preds.json"
        preds_file.write_text(json.dumps(preds))

        success = import_swebench_results(pending_benchmark, str(tmp_path), str(db_path))
        assert success is True

        engine, session_factory = init_db(db_path)
        with session_factory() as session:
            b = session.query(Benchmark).filter(Benchmark.run_id == pending_benchmark).one()
            assert b.resolved_count == 2
            assert b.total_instances == 3
            assert b.resolve_rate == pytest.approx(66.67, abs=0.1)
            assert b.status == "partial"
            assert b.completed_at is not None

    def test_import_all_resolved(self, db_path: Path, pending_benchmark: str, tmp_path: Path) -> None:
        """Import results where all instances are resolved."""
        preds = {
            "sympy__sympy-15599": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "sympy__sympy-15599",
                "model_patch": "diff --git a/foo.py b/foo.py",
            },
            "django__django-12345": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "django__django-12345",
                "model_patch": "diff --git a/bar.py b/bar.py",
            },
        }
        preds_file = tmp_path / "preds.json"
        preds_file.write_text(json.dumps(preds))

        success = import_swebench_results(pending_benchmark, str(tmp_path), str(db_path))
        assert success is True

        engine, session_factory = init_db(db_path)
        with session_factory() as session:
            b = session.query(Benchmark).filter(Benchmark.run_id == pending_benchmark).one()
            assert b.resolved_count == 2
            assert b.total_instances == 2
            assert b.resolve_rate == 100.0
            assert b.status == "success"

    def test_import_empty_preds(self, db_path: Path, pending_benchmark: str, tmp_path: Path) -> None:
        """Import results with empty preds.json."""
        preds_file = tmp_path / "preds.json"
        preds_file.write_text("{}")

        success = import_swebench_results(pending_benchmark, str(tmp_path), str(db_path))
        assert success is True

        engine, session_factory = init_db(db_path)
        with session_factory() as session:
            b = session.query(Benchmark).filter(Benchmark.run_id == pending_benchmark).one()
            assert b.total_instances == 0
            assert b.status == "error"

    def test_import_invalid_run_id(self, db_path: Path, tmp_path: Path) -> None:
        """Import fails when run_id doesn't exist."""
        preds_file = tmp_path / "preds.json"
        preds_file.write_text("{}")

        success = import_swebench_results("nonexistent-run-id", str(tmp_path), str(db_path))
        assert success is False

    def test_import_missing_preds_file(self, db_path: Path, pending_benchmark: str, tmp_path: Path) -> None:
        """Import fails when preds.json doesn't exist."""
        success = import_swebench_results(pending_benchmark, str(tmp_path), str(db_path))
        assert success is False

    def test_import_all_failed(self, db_path: Path, pending_benchmark: str, tmp_path: Path) -> None:
        """Import results where all instances failed."""
        preds = {
            "sympy__sympy-15599": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "sympy__sympy-15599",
                "model_patch": "",
            },
            "django__django-12345": {
                "model_name_or_path": "openai/gpt-4o",
                "instance_id": "django__django-12345",
                "model_patch": None,
            },
        }
        preds_file = tmp_path / "preds.json"
        preds_file.write_text(json.dumps(preds))

        success = import_swebench_results(pending_benchmark, str(tmp_path), str(db_path))
        assert success is True

        engine, session_factory = init_db(db_path)
        with session_factory() as session:
            b = session.query(Benchmark).filter(Benchmark.run_id == pending_benchmark).one()
            assert b.resolved_count == 0
            assert b.total_instances == 2
            assert b.resolve_rate == 0.0
            assert b.status == "error"