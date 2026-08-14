#!/usr/bin/env python3
"""Report whether the bundled AI-role baseline needs a reviewed refresh."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "data" / "baseline" / "role-capability-map.json"


def baseline_age_days(path: Path, now: datetime | None = None) -> tuple[str, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    generated_at = str(value.get("generated_at") or "")
    if not generated_at:
        raise ValueError("baseline is missing generated_at")
    generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    age = max(0, (current.astimezone(timezone.utc) - generated.astimezone(timezone.utc)).days)
    return generated_at, age


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--max-age-days", type=int, default=14)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    generated_at, age_days = baseline_age_days(args.baseline.resolve())
    stale = age_days > args.max_age_days
    result = {
        "generated_at": generated_at,
        "age_days": age_days,
        "max_age_days": args.max_age_days,
        "stale": stale,
    }
    print(json.dumps(result, ensure_ascii=False))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            for key, value in result.items():
                rendered = str(value).lower() if isinstance(value, bool) else str(value)
                output.write(f"{key}={rendered}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
