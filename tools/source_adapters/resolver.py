"""Resolve an official careers page to a supported public source provider."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .adapters import extract_job_postings
from .base import FetchResponse, HttpClient


@dataclass(frozen=True)
class ProviderResolution:
    provider: str
    board: str
    evidence_url: str


PROVIDER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ashby", re.compile(r"https?://jobs\.ashbyhq\.com/([^\s/?#\"'<>]+)", re.I)),
    ("greenhouse", re.compile(r"https?://(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([^\s/?#&\"'<>]+)", re.I)),
    ("lever", re.compile(r"https?://jobs(?:\.eu)?\.lever\.co/([^\s/?#\"'<>]+)", re.I)),
)


def detect_provider(final_url: str, page: str) -> ProviderResolution | None:
    haystack = f"{final_url}\n{page}"
    for provider, pattern in PROVIDER_PATTERNS:
        match = pattern.search(haystack)
        if match:
            return ProviderResolution(
                provider=provider,
                board=match.group(1).strip(),
                evidence_url=match.group(0).strip(),
            )
    if extract_job_postings(page):
        return ProviderResolution(provider="jsonld", board=final_url, evidence_url=final_url)
    return None


def resolve_source(
    source: dict[str, Any],
    client: HttpClient,
) -> tuple[dict[str, Any], ProviderResolution, FetchResponse]:
    careers_url = str(source.get("careers_url") or "")
    if not careers_url.startswith(("https://", "http://")):
        raise ValueError("auto source requires an official careers_url")
    response = client.get(careers_url, accept="text/html,application/xhtml+xml")
    resolution = detect_provider(response.final_url, response.text())
    if not resolution:
        raise ValueError("official careers page did not expose a supported ATS link or JobPosting JSON-LD")
    resolved = dict(source)
    resolved["provider"] = resolution.provider
    resolved["board"] = resolution.board
    resolved["resolved_from"] = careers_url
    return resolved, resolution, response
