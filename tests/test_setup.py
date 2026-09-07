import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.analysis_job import AnalysisJob
from modules.config import Config, ConfigurationRequiredError
from modules.setup_service import SetupService


class SetupServiceTest(unittest.TestCase):
    def test_requires_a_real_music_folder_and_deduplicates_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = SetupService(root / "config.json")
            result = service.validate({"musicRoots": [str(root), str(root)], "outputRoot": str(root / "output"), "analysisWorkers": 2, "supportedFormats": ["mp3"], "modules": {}})
            self.assertTrue(result["valid"])
            self.assertEqual(result["config"]["musicRoots"], [str(root.resolve())])
            self.assertEqual(result["config"]["supportedFormats"], [".mp3"])
            self.assertFalse(service.validate({"musicRoots": [str(root / "missing")]} )["valid"])

    def test_save_creates_local_config_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = SetupService(root / "config" / "config.json")
            result = service.save({"musicRoots": [str(root)], "outputRoot": str(root / "output"), "analysisWorkers": 1, "supportedFormats": [".mp3"], "modules": {}})
            self.assertTrue(result["valid"])
            self.assertTrue(service.path.exists())
            self.assertTrue((root / "output").is_dir())

    def test_missing_local_config_has_clear_first_run_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Config(Path(directory) / "missing.json")
            self.assertFalse(config.configured)
            with self.assertRaises(ConfigurationRequiredError):
                config.require_configured()


class AnalysisJobTest(unittest.TestCase):
    @patch("modules.analysis_job.Pipeline")
    def test_one_job_at_a_time_and_module_overrides_stay_in_memory(self, pipeline_class):
        pipeline_class.return_value.run.return_value = {"status": "complete", "tracks": 1}
        job = AnalysisJob()
        with patch("modules.analysis_job.Thread") as thread:
            first = job.start({"musicRoots": ["/music"], "modules": {"energy": False}}, {"energy": True})
            self.assertEqual(first["status"], "running")
            self.assertIsNone(job.start({"musicRoots": ["/music"]}, {}))
            thread.assert_called_once()

    def test_stop_marks_a_running_job_as_stopping(self):
        job = AnalysisJob()
        job._state["status"] = "running"
        self.assertEqual(job.stop()["status"], "stopping")
