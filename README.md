# SignalFit

[Live site](https://roletrace-open.eric348737.chatgpt.site) · [Source repository](https://github.com/SuperMikasa/signalfit)

SignalFit is an open-source career intelligence workbench for AI Product, AI Full-stack / Agent Engineering, and Forward Deployed Engineering roles.

It turns three distinct inputs into an explainable capability map:

1. official job-description signals;
2. accepted, candidate-authored interview reports;
3. evidence that can be located in a resume.

The output is a role-specific scorecard, prioritized gap list, and radar visualization. A score is **resume evidence coverage**, not a hiring probability or a claim about a person’s full ability.

## Why this exists

Most career tools collapse job descriptions, interview anecdotes, and resume keywords into one opaque score. SignalFit keeps their provenance separate:

- JD signals describe what the market asks for.
- Verified interview reports describe what candidates were actually tested on.
- Resume evidence describes what a candidate can currently prove.
- Location, work authorization, graduation date, and work hours remain separate eligibility constraints.

## Demo

The site ships with an anonymized example in [`public/example-fit.json`](public/example-fit.json). You can import another compatible JSON file directly in the browser. Imported files are read locally and are not uploaded.

The published site also exposes a versioned MIT source archive, so the project remains downloadable even when a GitHub mirror is temporarily unavailable.

## Run locally

Requires Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Then open the local URL printed by the development server.

## Validate

```bash
npm run build
npm test
```

## Input shape

The browser accepts a JSON document with a `roles` object. Each role contains:

```json
{
  "role_label": "AI Full-stack / Agent Engineering",
  "overall_score": 84,
  "axes": [
    {
      "rank": 1,
      "label": "Full-stack production delivery",
      "candidate_score": 100,
      "market_score": 85,
      "gap_priority": 0,
      "learning_actions": ["Keep production-delivery evidence current"]
    }
  ],
  "gaps": [],
  "constraints_to_review": { "signal_count": 0 }
}
```

See the complete example for all supported fields.

## Companion skills

The pipeline is deliberately split into three single-purpose skills:

- `build-role-capability-map`: JD and accepted interview evidence → ranked capabilities.
- `score-resume-role-fit`: resume → evidence coverage and prioritized gaps.
- `render-role-skill-radar`: fit JSON → radar and readable report.

This repository contains the public web surface. The skills can be used independently or connected to a scheduled evidence collection workflow.

## Privacy and evidence policy

Do not commit:

- private resumes or personally identifying application material;
- cookies, tokens, account data, private messages, or paywalled text;
- complete copies of third-party articles or job boards;
- unverified search snippets presented as interview evidence.

Public examples should use aggregate counts, short paraphrases, and synthetic or anonymized candidate evidence. See [SECURITY.md](SECURITY.md) for reporting sensitive-data exposure.

## Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a new scoring rule or evidence source.

## License

[MIT](LICENSE)
