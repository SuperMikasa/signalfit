import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "signalfit_cli.py"
SAMPLE_RESUME = ROOT / "examples" / "resume.sample.md"

spec = importlib.util.spec_from_file_location("signalfit_cli", CLI)
assert spec and spec.loader
signalfit_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signalfit_cli)


class SignalFitCliTest(unittest.TestCase):
    def test_doctor(self):
        result = subprocess.run(
            [sys.executable, str(CLI), "doctor"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        status = json.loads(result.stdout.split("\n提示：", 1)[0])
        self.assertTrue(status["python_supported"])
        self.assertTrue(status["baseline_map"])

    def test_analyzes_sample_without_persisting_absolute_resume_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result"
            subprocess.run(
                [sys.executable, str(CLI), "analyze", str(SAMPLE_RESUME), "--output-dir", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            fit = json.loads((output / "resume-role-fit.json").read_text(encoding="utf-8"))
            self.assertEqual(fit["resume_path"], SAMPLE_RESUME.name)
            self.assertNotIn(str(ROOT), json.dumps(fit, ensure_ascii=False))
            self.assertEqual(set(fit["roles"]), {"ai_pm", "ai_fullstack", "fde"})
            self.assertTrue((output / "role-fit-radar.html").is_file())
            self.assertTrue((output / "role-fit-radar-ai_pm.svg").is_file())

    def test_rejects_incomplete_updated_baseline(self):
        baseline = json.loads((ROOT / "data" / "baseline" / "role-capability-map.json").read_text(encoding="utf-8"))
        signalfit_cli.validate_capability_map(baseline)
        del baseline["roles"]["fde"]
        with self.assertRaisesRegex(ValueError, "必须包含"):
            signalfit_cli.validate_capability_map(baseline)


if __name__ == "__main__":
    unittest.main()
