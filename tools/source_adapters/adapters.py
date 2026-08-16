"""Adapters for public ATS endpoints and standards-based job pages."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from .base import FetchResponse, SourceAdapter


def strip_html(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value or "", flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


class AshbyAdapter(SourceAdapter):
    provider = "ashby"

    def endpoint(self, source: dict[str, Any]) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{quote(str(source['board']), safe='')}"

    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        payload = response.json()
        rows = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            description = row.get("descriptionPlain") or strip_html(str(row.get("descriptionHtml") or ""))
            address = row.get("address") if isinstance(row.get("address"), dict) else {}
            postal = address.get("postalAddress") if isinstance(address.get("postalAddress"), dict) else {}
            jobs.append(self.job(
                source,
                provider_job_id=row.get("id"),
                title=row.get("title"),
                source_url=row.get("jobUrl") or row.get("applyUrl"),
                location=row.get("location") or postal.get("addressLocality"),
                posted_at=row.get("publishedAt"),
                timestamp_basis="publishedAt",
                description=description,
            ))
        return jobs


class GreenhouseAdapter(SourceAdapter):
    provider = "greenhouse"

    def endpoint(self, source: dict[str, Any]) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{quote(str(source['board']), safe='')}/jobs?content=true"

    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        payload = response.json()
        rows = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            location = row.get("location") or {}
            company_name = str(row.get("company_name") or "")
            jobs.append(self.job(
                source,
                provider_job_id=row.get("id"),
                title=row.get("title"),
                source_url=row.get("absolute_url"),
                location=location.get("name") if isinstance(location, dict) else location,
                posted_at=row.get("first_published"),
                timestamp_basis="first_published",
                description=strip_html(str(row.get("content") or "")),
                company=source.get("company") if company_name in {"", "Job Board"} else company_name,
            ))
        return jobs


class LeverAdapter(SourceAdapter):
    provider = "lever"

    def endpoint(self, source: dict[str, Any]) -> str:
        return f"https://api.lever.co/v0/postings/{quote(str(source['board']), safe='')}?mode=json"

    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        payload = response.json()
        rows = payload if isinstance(payload, list) else []
        jobs: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            categories = row.get("categories") or {}
            created_at = row.get("createdAt")
            posted_at = None
            if isinstance(created_at, (int, float)):
                posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).isoformat()
            jobs.append(self.job(
                source,
                provider_job_id=row.get("id"),
                title=row.get("text"),
                source_url=row.get("hostedUrl") or row.get("applyUrl"),
                location=categories.get("location") if isinstance(categories, dict) else None,
                posted_at=posted_at,
                timestamp_basis="createdAt",
                description=" ".join(str(row.get(key) or "") for key in (
                    "descriptionPlain", "descriptionBodyPlain", "additionalPlain", "openingPlain"
                )),
            ))
        return jobs


def _walk_jsonld(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(_walk_jsonld(item))
    elif isinstance(value, dict):
        type_value = value.get("@type")
        types = type_value if isinstance(type_value, list) else [type_value]
        if "JobPosting" in types:
            found.append(value)
        if "@graph" in value:
            found.extend(_walk_jsonld(value["@graph"]))
    return found


def extract_job_postings(page: str) -> list[dict[str, Any]]:
    postings: list[dict[str, Any]] = []
    pattern = re.compile(
        r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        flags=re.I | re.S,
    )
    for match in pattern.finditer(page):
        try:
            postings.extend(_walk_jsonld(json.loads(html.unescape(match.group(1)).strip())))
        except (json.JSONDecodeError, TypeError):
            continue
    return postings


def _jsonld_location(value: Any) -> str:
    values = value if isinstance(value, list) else [value]
    labels: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        address = item.get("address") or {}
        if isinstance(address, str):
            labels.append(address)
            continue
        if isinstance(address, dict):
            label = ", ".join(str(address.get(key) or "") for key in (
                "addressLocality", "addressRegion", "addressCountry"
            ) if address.get(key))
            if label:
                labels.append(label)
    return " / ".join(labels) or "Unspecified"


class JsonLdJobPostingAdapter(SourceAdapter):
    provider = "jsonld"
    validation_method = "official_careers_jsonld+strict_date_window+body_readable"

    def endpoint(self, source: dict[str, Any]) -> str:
        url = str(source.get("careers_url") or source.get("board") or "")
        if not url.startswith(("https://", "http://")):
            raise ValueError("jsonld source requires careers_url")
        return url

    def fetch(self, source: dict[str, Any], client: Any) -> FetchResponse:
        return client.get(self.endpoint(source), accept="text/html,application/xhtml+xml")

    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for row in extract_job_postings(response.text()):
            organization = row.get("hiringOrganization") or {}
            identifier = row.get("identifier") or {}
            provider_job_id = identifier.get("value") if isinstance(identifier, dict) else identifier
            jobs.append(self.job(
                source,
                provider_job_id=provider_job_id or row.get("url") or response.final_url,
                title=row.get("title"),
                source_url=row.get("url") or response.final_url,
                location=_jsonld_location(row.get("jobLocation")),
                posted_at=row.get("datePosted"),
                timestamp_basis="datePosted",
                description=strip_html(str(row.get("description") or "")),
                company=organization.get("name") if isinstance(organization, dict) else source.get("company"),
            ))
        return jobs


_ADAPTERS: dict[str, SourceAdapter] = {
    adapter.provider: adapter
    for adapter in (AshbyAdapter(), GreenhouseAdapter(), LeverAdapter(), JsonLdJobPostingAdapter())
}


def get_adapter(provider: str) -> SourceAdapter:
    try:
        return _ADAPTERS[provider]
    except KeyError as exc:
        raise ValueError(f"unsupported provider: {provider}") from exc


def supported_providers() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))
