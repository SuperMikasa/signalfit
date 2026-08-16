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
RECENT_DIR = ROOT / "data" / "evidence" / "recent-14d"

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

        self.assertEqual(len(rows), 606)
        expected = {
            "ai_pm": {"signals": 206, "jobs": 36},
            "ai_fullstack": {"signals": 170, "jobs": 30},
            "fde": {"signals": 230, "jobs": 40},
        }
        for role_key, counts in expected.items():
            role_rows = [row for row in rows if row["role_family"] == role_key]
            self.assertEqual(len(role_rows), counts["signals"])
            self.assertEqual(len({row["source_url"] for row in role_rows}), counts["jobs"])
            self.assertEqual(sum(row["capability_key"] == "eligibility_constraint" for row in role_rows), counts["jobs"])
            self.assertTrue(all(row["source_url"].startswith("https://") for row in role_rows))

            role_map = baseline["roles"][role_key]
            self.assertEqual(role_map["jd_job_count"], counts["jobs"])
            self.assertEqual(role_map["jd_signal_count"], counts["signals"])
            self.assertEqual(role_map["constraints"]["signal_count"], counts["jobs"])

    def test_recent_14_day_scan_is_auditable_and_quality_gated(self):
        report = json.loads((RECENT_DIR / "coverage-report.json").read_text(encoding="utf-8"))
        jobs = [json.loads(line) for line in (RECENT_DIR / "recent-jobs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        signals = [json.loads(line) for line in (RECENT_DIR / "jd-signals.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

        self.assertEqual(report["window"], {"start": "2026-08-03", "end": "2026-08-16", "days": 14})
        self.assertEqual(report["sources"]["attempted"], 123)
        self.assertEqual(report["sources"]["succeeded"], 123)
        self.assertEqual(report["sources"]["failed"], 0)
        self.assertEqual(report["sources"]["deferred"], 8)
        self.assertEqual(report["sources"]["empty"], 1)
        self.assertEqual(report["jobs"]["accepted"], 100)
        self.assertEqual(report["jobs"]["adjacent_review"], 29)
        self.assertEqual(len(jobs), 129)
        self.assertEqual(len(signals), 600)
        self.assertEqual(sum(job["review_status"] == "accepted" for job in jobs), 100)
        self.assertEqual(sum(job["review_status"] == "needs_review" for job in jobs), 29)
        self.assertTrue(all("2026-08-03" <= job["posted_at"] <= "2026-08-16" for job in jobs))
        self.assertTrue(all(row["scope_tier"] != "adjacent_review" for row in signals))


if __name__ == "__main__":
    unittest.main()
