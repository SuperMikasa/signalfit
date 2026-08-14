# SignalFit agent instructions

SignalFit is a local-first resume evidence analyzer for AI Product, AI Full-stack / Agent Engineering, and FDE roles.

When a user asks to analyze a resume:

1. Keep the resume local. Do not upload it, paste it into a remote service, commit it, or copy it into tracked repository files.
2. Run `./signalfit doctor`.
3. Run `./signalfit analyze <user-provided-resume-path>`.
4. Read `.signalfit/latest.json`, then read the generated `resume-role-fit.md` and report the three role scores, strongest evidence, prioritized gaps, and any separate eligibility constraints.
5. Link the generated `role-fit-radar.html`. Use `./signalfit serve` only when the user wants a local HTTP preview.
6. Treat every score as resume evidence coverage, not hiring probability or a claim about the person’s full ability.
7. Preserve `provisional` labels when the bundled market baseline is incomplete.

Do not publish generated results without explicit user approval. Do not infer capabilities that lack a quoted resume line. To update the market baseline, use the separate `build-role-capability-map` skill only when the user explicitly requests fresh JD or interview evidence.
