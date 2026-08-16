# Public evidence layer

This directory is the auditable, public-safe input for the bundled SignalFit baseline.

- `jd-signals.jsonl` contains one atomic requirement per line. Each row includes an official job URL, retrieval date, role family, capability key, importance, and a concise paraphrase.
- `accepted-interview-snapshot.json` preserves only aggregate counts and short question summaries from previously accepted real-interview records. It does not republish full posts or personal data.
- `question-bank.jsonl` and `record-status.jsonl` are the import surfaces for newly reviewed interview evidence.
- `source-catalog.json` is the community-editable official ATS source registry.
- `recent-14d/` contains the strict rolling discovery set, accepted signals, source success/failure report, and adjacent roles waiting for review.
- `baseline/baseline-progress.json` records coverage progress. The baseline remains `provisional` while China coverage and accepted interview breadth are still being expanded.

Current cumulative snapshot: 106 independent active JD URLs and 606 atomic requirements. The 2026-08-02 to 2026-08-15 rolling scan attempted 138 official ATS boards, read 105 successfully, scanned 10,299 active jobs, found 1,581 jobs in-window, accepted 76 strict target jobs, and separated 22 adjacent jobs for manual review. Every newly accepted job contributes five capability signals plus one eligibility constraint; constraints never enter the radar score.

Source policy:

1. Use a company careers page or its official ATS endpoint for JD evidence.
2. Keep each requirement atomic and preserve the exact source URL and retrieval date.
3. Keep location, experience, education, work authorization, travel, and work-mode rules under `eligibility_constraint`.
4. Do not convert JD language into an alleged interview question.
5. Do not mirror full copyrighted pages, account-gated content, or personal identifiers.
6. Keep generic roles that merely mention AI in `needs_review`; only explicit AI roles or reviewed AI-native roles enter the capability score.

Reproduce the rolling scan:

```bash
python3 tools/scan_recent_jds.py \
  --as-of 2026-08-15 \
  --days 14 \
  --output-dir data/evidence/recent-14d
```
