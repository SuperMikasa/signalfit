# SignalFit

**Clone it. Point your coding agent at a local resume. Get an evidence-backed AI role radar.**

[Public demo](https://roletrace-open.eric348737.chatgpt.site) · [MIT License](LICENSE)

SignalFit is a local-first career intelligence toolkit focused exclusively on AI roles. Its first baseline covers three role families:

- AI Product;
- AI Full-stack / Agent Engineering;
- Forward Deployed Engineering (FDE).

It compares a local resume with an evidence-backed capability baseline derived from public job descriptions and accepted interview reports. The result is a role scorecard, quoted resume evidence, prioritized gaps, SVG radar charts, and a standalone HTML report.

Scores mean **resume evidence coverage**. They are not hiring probabilities and do not measure abilities that are absent from the document.

## Use with any coding CLI

```bash
git clone https://github.com/SuperMikasa/signalfit.git
cd signalfit
./signalfit doctor
./signalfit example
```

Then start OpenCode, Claude Code, Codex, or another repository-aware coding agent and ask:

```text
Read AGENTS.md. Analyze my local resume at /absolute/path/to/resume.pdf with SignalFit. Keep the resume and all generated results local. Then summarize my fit for AI Product, AI Full-stack / Agent Engineering, and FDE, and give me the local radar report path.
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
- the launcher makes no network requests;
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

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing scoring rules, evidence sources, or privacy behavior.

## License

[MIT](LICENSE)
