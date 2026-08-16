# Public evidence layer

This directory is the auditable, public-safe input for the bundled SignalFit baseline.

- `jd-signals.jsonl` contains one atomic requirement per line. Each row includes an official job URL, retrieval date, role family, capability key, importance, and a concise paraphrase.
- `question-bank.jsonl` contains one paraphrased interview question per row. `report_id` identifies the independent interview report; `record_id` identifies the extracted question.
- `record-status.jsonl` is the appendable review ledger. Only the latest `accepted` decision paired with `evidence_type=real_interview_report` enters scoring.
- `interview-source-catalog.json`, `interview-search-catalog.json`, `interview-source-leads.jsonl`, and `interview-baseline-report.md` document where the baseline came from, which public searches run daily, what remains blocked, and why a lead was excluded.
- `accepted-interview-snapshot.json` is a legacy, non-traceable aggregate retained only for migration history. Its counts must not be presented as independent reports.
- `source-catalog.json` is the community-editable official source registry; `source-catalog.schema.json` documents provider and resolver fields.
- `recent-14d/` contains the strict rolling discovery set, accepted signals, source success/failure report, detailed Chinese run log, per-source machine log, and adjacent roles waiting for review.
- `baseline/baseline-progress.json` records coverage progress. The baseline remains `provisional` while China coverage and accepted interview breadth are still being expanded.

Current cumulative snapshot: 106 independent active JD URLs, 606 atomic requirements, 57 traceable interview reports, and 277 accepted question summaries. Interview coverage is AI Product 18 reports / 94 questions, AI Full-stack 23 / 132, and FDE 16 / 51; 10 accepted reports were published in the latest 14-day interview window. The reviewed 2026-08-03 to 2026-08-16 rolling JD scan attempted and read 123 official ATS boards, scanned 11,278 active jobs, found 1,755 jobs in-window, accepted 100 strict target jobs, and separated 29 adjacent jobs for manual review. Every newly accepted job contributes five capability signals plus one eligibility constraint; constraints never enter the radar score.

Source policy:

1. Use a company careers page or its official ATS endpoint for JD evidence.
2. Keep each requirement atomic and preserve the exact source URL and retrieval date.
3. Keep location, experience, education, work authorization, travel, and work-mode rules under `eligibility_constraint`.
4. Do not convert JD language into an alleged interview question.
5. Do not mirror full copyrighted pages, account-gated content, or personal identifiers.
6. Keep generic roles that merely mention AI in `needs_review`; only explicit AI roles or reviewed AI-native roles enter the capability score.
7. Count interview reports and extracted questions separately. Score interview penetration by independent reports so one long post cannot dominate a capability.
8. Use a 24-month window for the sparse historical interview baseline and a 14-day window for daily incremental discovery.

Reproduce the rolling scan:

```bash
tools/run_daily_discovery.sh
```

To stream that same command in a dedicated cmux workspace:

```bash
tools/open_daily_discovery_cmux.sh
```

The normal daily run writes to `.signalfit-cache/runs/YYYY-MM-DD/` so unreviewed discovery does not dirty or overwrite the public baseline. Raw provider responses are stored as private gzip envelopes under `.signalfit-cache/raw/YYYY-MM-DD/<provider>/`; the public run log keeps only paths, hashes, counts, URLs, statuses, and errors. Both cache roots are ignored by Git.

The same run writes `interview-source-run.log`, `interview-source-runs.jsonl`, and `interview-candidates.jsonl` for unreviewed incremental discovery, plus `interview-evidence.log` for accepted website URLs, companies, report/question counts, topics, and excluded leads. Search-page Raw snapshots are stored under `.signalfit-cache/raw/YYYY-MM-DD/interviews/`.

For a reviewed maintainer refresh, write to the public audit directory explicitly:

```bash
python3 tools/scan_recent_jds.py \
  --as-of YYYY-MM-DD \
  --days 14 \
  --output-dir data/evidence/recent-14d
```

Source entries may use `ashby`, `greenhouse`, or `lever` with a provider board slug. A company with an official Careers page can instead use `provider: auto` plus `careers_url`; the resolver records the detected provider and evidence URL. An unresolved page is reported as `resolver_required` and never enters scoring.
