# SignalFit

**Clone it. Point your coding agent at a local resume. Get an evidence-backed AI role radar.**

[Public demo](https://roletrace-open.eric348737.chatgpt.site) · [MIT License](LICENSE)

SignalFit is a local-first career intelligence toolkit focused exclusively on AI roles. Its first baseline covers three role families:

- AI Product;
- AI Full-stack / Agent Engineering;
- Forward Deployed Engineering (FDE).

It compares a local resume with an evidence-backed capability baseline derived from public job descriptions and accepted interview reports. The result is a role scorecard, quoted resume evidence, prioritized gaps, SVG radar charts, and a standalone HTML report.

The current `provisional` baseline contains 106 role-classified independent active JD URLs, 606 atomic job-requirement signals, 45 traceable interview reports, and 207 accepted question summaries. By role: AI Product 36 / 206 / 15 / 76, AI Full-stack 30 / 170 / 15 / 85, and FDE 40 / 230 / 15 / 46 (JD / requirements / reports / questions). The latest strict rolling window covers 2026-08-02 through 2026-08-15: 138 official ATS boards attempted, 105 readable boards, 10,299 active jobs scanned, 1,581 in-window jobs, 76 accepted target jobs, and 22 adjacent roles kept out of scoring for manual review.

The public-safe evidence layer lives in [`data/evidence`](data/evidence): every JD signal keeps its official source URL, retrieval date, role family, capability key, and separate eligibility constraint. Each accepted interview question keeps a report ID, public source URL, review status, and paraphrased prompt. Full copyrighted pages and candidate identities are not mirrored.

Scores mean **resume evidence coverage**. They are not hiring probabilities and do not measure abilities that are absent from the document.

## Use with any coding CLI

```bash
git clone https://github.com/SuperMikasa/signalfit.git
cd signalfit
./signalfit doctor
./signalfit update
./signalfit example
```

Then start OpenCode, Claude Code, Codex, or another repository-aware coding agent and ask:

```text
Update SignalFit's public AI-role baseline, read AGENTS.md, and analyze my local resume at /absolute/path/to/resume.pdf. Keep the resume and all generated results local. Then summarize my fit for AI Product, AI Full-stack / Agent Engineering, and FDE, and give me the local radar report path.
```

The deterministic command behind that workflow is:

```bash
./signalfit analyze /absolute/path/to/resume.pdf
```

Results are written under `.signalfit/`, which is ignored by Git. To view the latest report over a local-only HTTP server:

```bash
./signalfit serve
# http://127.0.0.1:8788/role-fit-radar.html
```

No global skill installation is required. Coding agents can follow [AGENTS.md](AGENTS.md). Codex users may optionally copy `skills/run-signalfit-locally` into their personal skills directory.

## Supported resume files

Markdown, TXT, and DOCX work with Python's standard library. PDF requires either `pdftotext` or `pypdf`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./signalfit analyze /absolute/path/to/resume.pdf
```

The `signalfit` launcher automatically uses `.venv/bin/python` when that environment exists.

## Outputs

Each run creates:

- `resume-role-fit.json` — machine-readable scores and quoted evidence;
- `resume-role-fit.md` — readable Chinese evidence and gap report;
- `role-fit-radar.html` — standalone responsive report;
- `role-fit-radar-*.svg` — one chart per role.

The generated JSON stores only the resume filename, not its absolute filesystem path or a file fingerprint.

## Keep the AI-role baseline current

Users can fetch the latest reviewed public baseline without uploading a resume:

```bash
./signalfit update
```

The downloaded map is schema-checked and stored under the Git-ignored `.signalfit/baseline/` directory. Future analyses prefer this cache and fall back to the bundled provisional baseline when no update is available.

The repository also runs a weekly freshness check. If the bundled baseline is older than 14 days, GitHub Actions opens or updates a maintainer task for a reviewed JD and interview-evidence refresh. The scheduled check does not admit unreviewed community content directly into scores.

Maintainers can reproduce the high-recall official ATS scan before review:

```bash
tools/run_daily_discovery.sh
```

The daily runner streams a detailed Chinese log and writes an auditable run under `.signalfit-cache/runs/YYYY-MM-DD/`. Full provider responses are gzip-compressed under `.signalfit-cache/raw/YYYY-MM-DD/`; both locations are Git-ignored. The scheduled discovery run never promotes evidence or rewrites the public capability map automatically.

On macOS with cmux installed, open the same run in a dedicated workspace:

```bash
tools/open_daily_discovery_cmux.sh
```

The source registry is [`data/evidence/source-catalog.json`](data/evidence/source-catalog.json). It keeps daily `sources`, official pages in `deferred_sources` that still need an adapter, and migrated/duplicate `retired_sources` as separate auditable lists. SignalFit uses provider adapters for Ashby, Greenhouse, Lever, SmartRecruiters, and Teamtailor's public jobs RSS, plus an official-page resolver that can detect those providers or standards-based `JobPosting` JSON-LD. SmartRecruiters sources may include a `query` so an acquired product such as Moveworks can be isolated inside its parent company's board. A resolver entry looks like:

```json
{
  "provider": "auto",
  "company": "Example AI",
  "careers_url": "https://example.ai/careers",
  "region": "US"
}
```

Each run produces `source-run.log` with the site, request URL, HTTP result, raw count, 14-day count, accepted count, review count, raw snapshot location, and deferred-source reasons. `source-runs.jsonl` contains the per-source scan evidence in machine-readable form. An HTTP-success source with zero active jobs is reported as `empty_success`, not silently mixed into non-empty sources. Generic roles that merely mention AI stay in `needs_review`; only strict or explicitly reviewed AI roles produce scoring signals.

## How it works

```text
public JD signals + accepted interview reports
                    ↓
          role capability baseline
                    ↓
             local resume file
                    ↓
 evidence scoring → gaps → radar report
```

The repository packages four agent skills:

- `run-signalfit-locally` — private end-to-end local workflow;
- `build-role-capability-map` — JD/interview evidence → ranked role capabilities;
- `score-resume-role-fit` — resume → quoted evidence and prioritized gaps;
- `render-role-skill-radar` — fit JSON → HTML, Markdown, and SVG.

The bundled baseline is currently marked `provisional`. Eligibility constraints such as location, work authorization, graduation date, and work hours stay separate from capability scores.

## Privacy model

SignalFit is designed so a user can keep sensitive career material on their own machine:

- resumes are read from the path the user provides;
- private runs default to the ignored `.signalfit/` directory;
- resume analysis makes no network requests; the explicit `update` command downloads only the public capability baseline;
- generated reports are never published automatically;
- public examples are synthetic and contain no personal resume data.

Do not commit private resumes, generated fit reports, cookies, tokens, or restricted source text. See [SECURITY.md](SECURITY.md).

## Development

The local resume pipeline requires Python 3.10 or newer. The public demo additionally requires Node.js 22.13 or newer.

```bash
./signalfit doctor
./signalfit example
npm install
npm test
```

Validate the repository skills with:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/run-signalfit-locally
```

## Contributing

Community evidence is part of the product loop:

- [submit an official AI job description](https://github.com/SuperMikasa/signalfit/issues/new?template=contribute-ai-jd.yml);
- [submit a verifiable AI interview report](https://github.com/SuperMikasa/signalfit/issues/new?template=contribute-interview.yml).

Every contribution enters review first. Official JD signals, accepted real interview reports, inferred practice questions, and eligibility constraints remain separate. Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing scoring rules, evidence sources, or privacy behavior.

## License

[MIT](LICENSE)
