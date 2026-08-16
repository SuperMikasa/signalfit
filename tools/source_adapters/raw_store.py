"""Private raw-response cache. Files live under a Git-ignored directory."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .base import FetchResponse


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-.").lower()
    return value[:80] or "source"


def write_raw_snapshot(
    raw_root: Path,
    snapshot_day: date,
    source: dict[str, Any],
    response: FetchResponse,
) -> tuple[Path, str]:
    provider = _slug(str(source.get("provider") or "unknown"))
    company = _slug(str(source.get("company") or "company"))
    board = str(source.get("board") or response.final_url)
    identity_hash = hashlib.sha256(board.encode("utf-8")).hexdigest()[:10]
    path = raw_root / snapshot_day.isoformat() / provider / f"{company}-{identity_hash}.json.gz"
    body_sha256 = hashlib.sha256(response.body).hexdigest()
    try:
        payload: Any = response.json()
        encoding = "json"
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = response.text()
        encoding = "text"
    envelope = {
        "schema_version": 1,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": source.get("provider"),
            "board": source.get("board"),
            "company": source.get("company"),
        },
        "request_url": response.request_url,
        "final_url": response.final_url,
        "status_code": response.status_code,
        "content_type": response.content_type,
        "body_sha256": body_sha256,
        "body_encoding": encoding,
        "payload": payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(envelope, handle, ensure_ascii=False, separators=(",", ":"))
    return path, body_sha256
