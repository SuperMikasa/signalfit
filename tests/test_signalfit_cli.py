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
EVIDENCE = ROOT / "data" / "evidence" / "jd-signals.jsonl"

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

    def test_public_baseline_has_balanced_auditable_evidence(self):
        rows = [json.loads(line) for line in EVIDENCE.read_text(encoding="utf-8").splitlines() if line.strip()]
        baseline = json.loads((ROOT / "data" / "baseline" / "role-capability-map.json").read_text(encoding="utf-8"))

        self.assertEqual(len(rows), 150)
        for role_key in ("ai_pm", "ai_fullstack", "fde"):
            role_rows = [row for row in rows if row["role_family"] == role_key]
            self.assertEqual(len(role_rows), 50)
            self.assertEqual(len({row["source_url"] for row in role_rows}), 10)
            self.assertEqual(sum(row["capability_key"] == "eligibility_constraint" for row in role_rows), 10)
            self.assertTrue(all(row["source_url"].startswith("https://") for row in role_rows))
            self.assertTrue(all(row["retrieved_at"] == "2026-08-14" for row in role_rows))

            role_map = baseline["roles"][role_key]
            self.assertEqual(role_map["jd_job_count"], 10)
            self.assertEqual(role_map["jd_signal_count"], 50)
            self.assertEqual(role_map["constraints"]["signal_count"], 10)


if __name__ == "__main__":
    unittest.main()
