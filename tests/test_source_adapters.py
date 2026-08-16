import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from source_adapters import FetchResponse, detect_provider, get_adapter, write_raw_snapshot  # noqa: E402

spec = importlib.util.spec_from_file_location("scan_recent_jds", TOOLS / "scan_recent_jds.py")
assert spec and spec.loader
scanner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scanner
spec.loader.exec_module(scanner)


def response(payload, url="https://example.test/jobs"):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    return FetchResponse(
        request_url=url,
        final_url=url,
        status_code=200,
        content_type="application/json",
        body=body,
    )


class FakeClient:
    def __init__(self, fetch_response):
        self.fetch_response = fetch_response

    def get(self, url, accept="application/json"):
        return FetchResponse(
            request_url=url,
            final_url=self.fetch_response.final_url,
            status_code=self.fetch_response.status_code,
            content_type=self.fetch_response.content_type,
            body=self.fetch_response.body,
        )


class SourceAdaptersTest(unittest.TestCase):
    def test_network_environment_failure_has_distinct_outcome(self):
        self.assertEqual(scanner._failure_outcome(URLError("DNS unavailable")), "environment_unavailable")

    def test_catalog_validation_rejects_unresolvable_auto_source(self):
        with self.assertRaisesRegex(ValueError, "HTTPS careers_url"):
            scanner.validate_source_catalog({
                "schema_version": 2,
                "sources": [{"provider": "auto", "company": "Example AI"}],
            })

    def test_existing_ats_adapters_preserve_normalized_contract(self):
        fixtures = {
            "ashby": {
                "payload": {"jobs": [{
                    "id": "a1", "title": "AI Engineer", "jobUrl": "https://jobs.example/a1",
                    "location": "New York", "publishedAt": "2026-08-15T10:00:00Z",
                    "descriptionPlain": "Build production AI agents with Python and evaluation.",
                }]},
                "board": "example",
                "basis": "publishedAt",
            },
            "greenhouse": {
                "payload": {"jobs": [{
                    "id": 2, "title": "AI Product Manager", "absolute_url": "https://jobs.example/g2",
                    "location": {"name": "Remote"}, "first_published": "2026-08-14T10:00:00Z",
                    "content": "<p>Own AI product strategy, metrics, roadmap, evaluation and launch.</p>",
                }]},
                "board": "example",
                "basis": "first_published",
            },
            "lever": {
                "payload": [{
                    "id": "l3", "text": "Forward Deployed AI Engineer", "hostedUrl": "https://jobs.example/l3",
                    "categories": {"location": "Boston"}, "createdAt": 1786716000000,
                    "descriptionPlain": "Customer-facing Python API integration and full-stack delivery.",
                }],
                "board": "example",
                "basis": "createdAt",
            },
            "smartrecruiters": {
                "payload": {"jobs": [{
                    "id": "s4", "uuid": "uuid-s4", "name": "Forward Deployed AI Engineer",
                    "postingUrl": "https://jobs.smartrecruiters.com/Example/s4",
                    "location": {"fullLocation": "New York, NY, United States"},
                    "releasedDate": "2026-08-15T10:00:00Z",
                    "jobAd": {"sections": {
                        "jobDescription": {"text": "<p>Build customer-facing AI agents.</p>"},
                        "qualifications": {"text": "<p>Python, APIs and production delivery.</p>"},
                    }},
                }]},
                "board": "Example",
                "basis": "releasedDate",
            },
            "teamtailor": {
                "payload": b'''<?xml version="1.0" encoding="UTF-8"?>
                <rss version="2.0" xmlns:tt="https://teamtailor.com/locations"><channel><item>
                  <title>AI Product Engineer</title>
                  <description>&lt;p&gt;Build production AI agents with TypeScript.&lt;/p&gt;</description>
                  <pubDate>Sat, 15 Aug 2026 10:00:00 -0700</pubDate>
                  <link>https://careers.example.ai/jobs/42-ai-product-engineer</link>
                  <guid>tt-42</guid>
                  <tt:locations><tt:location><tt:name>San Francisco</tt:name></tt:location></tt:locations>
                </item></channel></rss>''',
                "board": "careers.example.ai",
                "basis": "pubDate",
            },
        }
        for provider, fixture in fixtures.items():
            with self.subTest(provider=provider):
                source = {"provider": provider, "board": fixture["board"], "company": "Example AI"}
                jobs = get_adapter(provider).normalize(source, response(fixture["payload"]))
                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0]["provider"], provider)
                self.assertEqual(jobs[0]["company"], "Example AI")
                self.assertEqual(jobs[0]["timestamp_basis"], fixture["basis"])
                self.assertTrue(jobs[0]["description"])
                self.assertTrue(jobs[0]["source_url"].startswith("https://"))

    def test_auto_resolver_detects_ats_link_and_jsonld_fallback(self):
        ashby = detect_provider(
            "https://example.ai/careers",
            '<a href="https://jobs.ashbyhq.com/example-ai">Open roles</a>',
        )
        self.assertIsNotNone(ashby)
        self.assertEqual((ashby.provider, ashby.board), ("ashby", "example-ai"))

        smartrecruiters = detect_provider(
            "https://example.ai/careers",
            '<a href="https://jobs.smartrecruiters.com/ServiceNow/123-ai-engineer">Open role</a>',
        )
        self.assertIsNotNone(smartrecruiters)
        self.assertEqual((smartrecruiters.provider, smartrecruiters.board), ("smartrecruiters", "ServiceNow"))

        teamtailor = detect_provider(
            "https://careers.example.ai/",
            '<script src="https://assets-aws.teamtailor-cdn.com/app.js"></script>'
            '<link rel="alternate" type="application/rss+xml" title="Jobs" href="/jobs.rss">',
        )
        self.assertIsNotNone(teamtailor)
        self.assertEqual((teamtailor.provider, teamtailor.board), ("teamtailor", "https://careers.example.ai"))

        direct_ashby = detect_provider("https://jobs.ashbyhq.com/Perplexity", "")
        self.assertIsNotNone(direct_ashby)
        self.assertEqual(direct_ashby.board, "Perplexity")

        page = """
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"JobPosting","title":"AI Engineer",
         "datePosted":"2026-08-15","description":"Build reliable AI agents."}
        </script>
        """
        jsonld = detect_provider("https://example.ai/careers/ai-engineer", page)
        self.assertIsNotNone(jsonld)
        self.assertEqual(jsonld.provider, "jsonld")

    def test_jsonld_adapter_requires_date_and_keeps_official_page(self):
        page = b"""
        <script type="application/ld+json">
        {"@type":"JobPosting","title":"AI Engineer","datePosted":"2026-08-15",
         "description":"<p>Python, agent orchestration, evaluation, APIs and production reliability.</p>",
         "url":"https://example.ai/jobs/1","identifier":{"value":"job-1"},
         "hiringOrganization":{"name":"Example AI"},
         "jobLocation":{"address":{"addressLocality":"Shanghai","addressCountry":"CN"}}}
        </script>
        """
        source = {"provider": "jsonld", "board": "https://example.ai/jobs/1", "company": "Example AI"}
        jobs = get_adapter("jsonld").normalize(
            source,
            FetchResponse(source["board"], source["board"], 200, "text/html", page),
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["posted_at"], "2026-08-15")
        self.assertEqual(jobs[0]["timestamp_basis"], "datePosted")
        self.assertEqual(jobs[0]["location"], "Shanghai, CN")
        self.assertEqual(jobs[0]["validation_method"], "official_careers_jsonld+strict_date_window+body_readable")

    def test_raw_snapshot_is_gzipped_private_envelope(self):
        source = {"provider": "ashby", "board": "example", "company": "Example AI"}
        payload = {"jobs": [{"id": "1", "descriptionPlain": "full source body"}]}
        with tempfile.TemporaryDirectory() as temp_dir:
            path, body_sha = write_raw_snapshot(Path(temp_dir), date(2026, 8, 15), source, response(payload))
            self.assertTrue(path.is_file())
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                stored = json.load(handle)
            self.assertEqual(stored["payload"], payload)
            self.assertEqual(stored["body_sha256"], body_sha)
            self.assertEqual(stored["source"]["company"], "Example AI")

    def test_scan_source_emits_auditable_raw_path(self):
        source = {"provider": "ashby", "board": "example", "company": "Example AI"}
        payload = {"jobs": [{
            "id": "1", "title": "AI Engineer", "jobUrl": "https://example.test/1",
            "publishedAt": "2026-08-15", "descriptionPlain": "Python agent evaluation API production reliability",
        }]}
        with tempfile.TemporaryDirectory() as temp_dir:
            scan = scanner.scan_source(
                0,
                source,
                FakeClient(response(payload)),
                Path(temp_dir),
                date(2026, 8, 15),
                True,
                scanner.ChineseRunLogger(quiet=True),
            )
            self.assertIsNone(scan.error)
            self.assertEqual(len(scan.jobs), 1)
            self.assertTrue(scan.raw_snapshot_path.endswith(".json.gz"))
            self.assertTrue(Path(scan.raw_snapshot_path).is_file())
            self.assertEqual(scan.jobs[0]["_source_key"], scan.source_key)


if __name__ == "__main__":
    unittest.main()
