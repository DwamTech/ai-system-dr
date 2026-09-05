"""Status/reconnect regression tests, isolated from live jobs and model downloads."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


class FakeEngine:
    def __init__(self, **kwargs):
        self.options = kwargs


class IndexingStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location(
            "isolated_indexing_jobs", Path(__file__).with_name("indexing_jobs.py")
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict("os.environ", {"INDEXING_JOBS_DIR": str(root)}), patch.dict(
            sys.modules, {
                "engine_optimized": types.SimpleNamespace(OptimizedRAGEngine=FakeEngine),
                "processor_optimized": types.SimpleNamespace(OptimizedDocumentProcessor=object),
            }
        ):
            spec.loader.exec_module(module)
        self.manager = module.indexing_jobs

    def write_status(self, **changes):
        status = {
            "id": "test-job", "state": "running", "progress": 5,
            "elapsed_seconds": 0,
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat(),
        }
        status.update(changes)
        self.manager._write_status("test-job", status)

    def test_blocking_warmup_clock_moves_without_fake_progress_or_disk_writes(self):
        self.write_status()
        path = self.manager._status_path("test-job")
        original = path.read_bytes()
        status = self.manager.get_status("test-job")
        self.assertGreaterEqual(status["elapsed_seconds"], 65)
        self.assertLess(status["elapsed_seconds"], 70)
        self.assertEqual(status["progress"], 5)
        self.assertEqual(path.read_bytes(), original)

    def test_completed_elapsed_remains_final(self):
        self.write_status(state="completed", progress=100, elapsed_seconds=12)
        self.assertEqual(self.manager.get_status("test-job")["elapsed_seconds"], 12)

    def test_malformed_timestamp_does_not_break_status(self):
        self.write_status(started_at="invalid", elapsed_seconds=7)
        self.assertEqual(self.manager.get_status("test-job")["elapsed_seconds"], 7)

    def test_completed_job_reconnects_once_with_saved_model(self):
        self.write_status(state="completed", model_name="configured-model")
        engine = self.manager.get_engine("test-job")
        self.assertEqual(engine.options, {"model_name": "configured-model", "report_errors": False})
        self.assertIs(engine, self.manager.get_engine("test-job"))

    def test_running_missing_and_failed_jobs_do_not_fabricate_ready_engines(self):
        self.write_status()
        self.assertIsNone(self.manager.get_engine("test-job"))
        self.write_status(state="failed")
        self.assertIsNone(self.manager.get_engine("test-job"))
        self.assertIsNone(self.manager.get_engine("missing"))
        self.assertIsNone(self.manager.get_engine(None))


if __name__ == "__main__":
    unittest.main()
