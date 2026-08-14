# Contributing to RoleTrace

Thanks for improving RoleTrace. Small, evidence-backed changes are preferred over broad scoring rewrites.

## Before opening a pull request

1. Create an issue for changes to scoring semantics or accepted evidence types.
2. Keep official JD signals, interview reports, inferred practice questions, and eligibility constraints separate.
3. Add or update an anonymized fixture for behavior changes.
4. Run `npm run build` and `npm test`.
5. Confirm the change does not add resumes, private paths, credentials, cookies, or copyrighted page dumps.

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
