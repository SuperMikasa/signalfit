# Public evidence layer

This directory is the auditable, public-safe input for the bundled SignalFit baseline.

- `jd-signals.jsonl` contains one atomic requirement per line. Each row includes an official job URL, retrieval date, role family, capability key, importance, and a concise paraphrase.
- `accepted-interview-snapshot.json` preserves only aggregate counts and short question summaries from previously accepted real-interview records. It does not republish full posts or personal data.
- `question-bank.jsonl` and `record-status.jsonl` are the import surfaces for newly reviewed interview evidence.
- `baseline/baseline-progress.json` records coverage progress. The baseline remains `provisional` while China coverage and accepted interview breadth are still being expanded.

Current snapshot: 30 independent active JD URLs and 150 atomic requirements, split evenly across AI Product, AI Full-stack / Agent Engineering, and FDE. Ten requirements per role are eligibility constraints and never enter the radar score.

Source policy:

1. Use a company careers page or its official ATS endpoint for JD evidence.
2. Keep each requirement atomic and preserve the exact source URL and retrieval date.
3. Keep location, experience, education, work authorization, travel, and work-mode rules under `eligibility_constraint`.
4. Do not convert JD language into an alleged interview question.
5. Do not mirror full copyrighted pages, account-gated content, or personal identifiers.
