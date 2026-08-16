import importlib.util
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "scan_recent_interviews.py"
spec = importlib.util.spec_from_file_location("scan_recent_interviews", MODULE)
assert spec and spec.loader
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class InterviewDiscoveryTest(unittest.TestCase):
    def test_parses_recent_nowcoder_card(self):
        body = '''<div class="show-time">08-13 16:09</div>
        <a href="/feed/main/detail/abcdef123456?sourceSSR=search">AI Agent 开发一面面经</a>
        <div class="placeholder-text">面试时间：8月9号&amp;nbsp;1. Agent 如何处理工具失败？</div>'''.encode("utf-8")
        rows = scanner.parse_nowcoder_results(body, "ai_fullstack", date(2026, 8, 16))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["discovered_published_at"], "2026-08-13")
        self.assertEqual(rows[0]["candidate_status"], "needs_review")
        self.assertEqual(rows[0]["source_url"], "https://www.nowcoder.com/feed/main/detail/abcdef123456")

    def test_excludes_guides_and_resolves_relative_dates(self):
        self.assertFalse(scanner.likely_first_person_report("Agent 面经汇总", "面试问题"))
        self.assertFalse(scanner.likely_first_person_report("面经", "Agent 与 Workflow 的区别，答：一；答：二"))
        self.assertFalse(scanner.likely_first_person_report("字节保洁岗三面面经", "如何用 AI 优化工作流"))
        self.assertEqual(scanner.parse_display_date("昨天 16:39", date(2026, 8, 16)), date(2026, 8, 15))
        self.assertEqual(scanner.parse_display_date("12-31 10:00", date(2026, 1, 2)), date(2025, 12, 31))


if __name__ == "__main__":
    unittest.main()
