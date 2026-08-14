import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "signalfit_cli.py"
SAMPLE_RESUME = ROOT / "examples" / "resume.sample.md"


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


if __name__ == "__main__":
    unittest.main()
