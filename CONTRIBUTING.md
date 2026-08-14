# Contributing to SignalFit

Thanks for improving SignalFit. Small, evidence-backed changes are preferred over broad scoring rewrites.

Run both the local CLI tests and public demo tests before opening a pull request. Never add a real resume or generated private report as a fixture; use synthetic data under `examples/`.

## Before opening a pull request

1. Create an issue for changes to scoring semantics or accepted evidence types.
2. Keep official JD signals, interview reports, inferred practice questions, and eligibility constraints separate.
3. Add or update an anonymized fixture for behavior changes.
4. Run `npm run build` and `npm test`.
5. Confirm the change does not add resumes, private paths, credentials, cookies, or copyrighted page dumps.

## Contribute market evidence

Use the structured GitHub forms for [AI job descriptions](https://github.com/SuperMikasa/signalfit/issues/new?template=contribute-ai-jd.yml) and [real interview reports](https://github.com/SuperMikasa/signalfit/issues/new?template=contribute-interview.yml).

Submissions are an intake queue, not accepted evidence. A maintainer must verify the source and classify it before it can affect a baseline:

1. Official JD signals require a public company careers URL and an active-role check.
2. Interview evidence requires a public, traceable source. Only the latest `accepted` record with `evidence_type=real_interview_report` enters interview counts.
3. Practice questions and inferred topics never count as real interview reports.
4. Location, work authorization, graduation timing, experience years, and working hours remain eligibility constraints rather than capabilities.

Summarize sources in your own words. Do not paste full copyrighted pages or include candidate identities, private messages, or personal contact details.

## Baseline refresh cadence

The weekly GitHub workflow checks the bundled baseline age. When it exceeds 14 days, it creates or updates a maintainer refresh task. A reviewed refresh uses `build-role-capability-map`, reads back all three role maps, and preserves `provisional` until the expanded baseline is complete.

## Design principles

- Explain every score with inspectable inputs.
- Treat missing evidence as unknown, not as proof of missing ability.
- Never present a fit score as hiring probability.
- Keep hard eligibility constraints outside capability totals.
- Mark incomplete market baselines as provisional.

## Commit style

Use a short imperative subject, for example:

```text
Add local JSON import validation
```
