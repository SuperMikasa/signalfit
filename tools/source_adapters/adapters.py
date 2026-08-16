"""Adapters for public ATS endpoints and standards-based job pages."""

from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote, urlencode

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


class SmartRecruitersAdapter(SourceAdapter):
    provider = "smartrecruiters"

    def endpoint(self, source: dict[str, Any]) -> str:
        query = {"limit": 100, "offset": 0}
        if source.get("query"):
            query["q"] = str(source["query"])
        board = quote(str(source["board"]), safe="")
        return f"https://api.smartrecruiters.com/v1/companies/{board}/postings?{urlencode(query)}"

    def fetch(self, source: dict[str, Any], client: Any) -> FetchResponse:
        first = client.get(self.endpoint(source))
        first_payload = first.json()
        if not isinstance(first_payload, dict):
            raise ValueError("SmartRecruiters postings response must be an object")

        rows = [row for row in first_payload.get("content", []) if isinstance(row, dict)]
        total = int(first_payload.get("totalFound") or len(rows))
        limit = int(first_payload.get("limit") or 100)
        list_requests = 1
        for offset in range(limit, total, limit):
            query = {"limit": limit, "offset": offset}
            if source.get("query"):
                query["q"] = str(source["query"])
            board = quote(str(source["board"]), safe="")
            page_url = (
                f"https://api.smartrecruiters.com/v1/companies/{board}/postings?"
                f"{urlencode(query)}"
            )
            page = client.get(page_url).json()
            if isinstance(page, dict):
                rows.extend(row for row in page.get("content", []) if isinstance(row, dict))
            list_requests += 1

        details: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []

        def fetch_detail(row: dict[str, Any]) -> dict[str, Any]:
            detail_url = str(row.get("ref") or "")
            if not detail_url.startswith("https://"):
                board = quote(str(source["board"]), safe="")
                detail_url = (
                    f"https://api.smartrecruiters.com/v1/companies/{board}/postings/"
                    f"{quote(str(row.get('id') or row.get('uuid') or ''), safe='')}"
                )
            payload = client.get(detail_url).json()
            if not isinstance(payload, dict):
                raise ValueError("SmartRecruiters posting detail must be an object")
            return payload

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(rows)))) as executor:
            future_rows = {executor.submit(fetch_detail, row): row for row in rows}
            for future in as_completed(future_rows):
                row = future_rows[future]
                try:
                    details.append(future.result())
                except Exception as exc:
                    failures.append({
                        "id": str(row.get("id") or row.get("uuid") or "unknown"),
                        "error": f"{type(exc).__name__}: {exc}",
                    })

        details.sort(key=lambda row: (str(row.get("releasedDate") or ""), str(row.get("id") or "")), reverse=True)
        audit = {
            "list_requests": list_requests,
            "listed_postings": len(rows),
            "detail_requests": len(rows),
            "detail_succeeded": len(details),
            "detail_failed": len(failures),
        }
        aggregate = {
            "provider": self.provider,
            "company_identifier": source.get("board"),
            "query": source.get("query"),
            "total_found": total,
            "audit": audit,
            "detail_failures": failures,
            "jobs": details,
        }
        return FetchResponse(
            request_url=first.request_url,
            final_url=first.final_url,
            status_code=first.status_code,
            content_type="application/json",
            body=json.dumps(aggregate, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            audit=audit,
        )

    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        payload = response.json()
        rows = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            location = row.get("location") or {}
            job_ad = row.get("jobAd") or {}
            sections = job_ad.get("sections") if isinstance(job_ad, dict) else {}
            description_parts: list[str] = []
            if isinstance(sections, dict):
                for section in sections.values():
                    if isinstance(section, dict):
                        description_parts.append(strip_html(str(section.get("text") or "")))
            jobs.append(self.job(
                source,
                provider_job_id=row.get("uuid") or row.get("id"),
                title=row.get("name"),
                source_url=row.get("postingUrl") or row.get("applyUrl"),
                location=location.get("fullLocation") if isinstance(location, dict) else location,
                posted_at=row.get("releasedDate"),
                timestamp_basis="releasedDate",
                description=" ".join(part for part in description_parts if part),
            ))
        return jobs


class TeamtailorAdapter(SourceAdapter):
    provider = "teamtailor"
    validation_method = "official_teamtailor_rss+strict_date_window+body_readable"

    def endpoint(self, source: dict[str, Any]) -> str:
        board = str(source["board"]).strip().rstrip("/")
        base_url = board if board.startswith(("https://", "http://")) else f"https://{board}"
        return f"{base_url}/jobs.rss"

    def fetch(self, source: dict[str, Any], client: Any) -> FetchResponse:
        return client.get(self.endpoint(source), accept="application/rss+xml,application/xml,text/xml")

    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        page = response.text()
        for match in re.finditer(r"<item\b[^>]*>(.*?)</item>", page, flags=re.I | re.S):
            item = match.group(1)

            def value(tag: str) -> str:
                found = re.search(
                    rf"<{re.escape(tag)}\b[^>]*>(.*?)</{re.escape(tag)}>",
                    item,
                    flags=re.I | re.S,
                )
                if not found:
                    return ""
                raw = re.sub(r"^\s*<!\[CDATA\[(.*)\]\]>\s*$", r"\1", found.group(1), flags=re.S)
                return html.unescape(raw).strip()

            posted_at = value("pubDate")
            if posted_at:
                posted_at = parsedate_to_datetime(posted_at).isoformat()
            locations = [
                html.unescape(location).strip()
                for location in re.findall(r"<tt:name\b[^>]*>(.*?)</tt:name>", item, flags=re.I | re.S)
                if html.unescape(location).strip()
            ]
            jobs.append(self.job(
                source,
                provider_job_id=value("guid") or value("link"),
                title=value("title"),
                source_url=value("link"),
                location=" / ".join(locations) or "Unspecified",
                posted_at=posted_at,
                timestamp_basis="pubDate",
                description=strip_html(value("description")),
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
    for adapter in (
        AshbyAdapter(), GreenhouseAdapter(), LeverAdapter(), SmartRecruitersAdapter(),
        TeamtailorAdapter(), JsonLdJobPostingAdapter(),
    )
}


def get_adapter(provider: str) -> SourceAdapter:
    try:
        return _ADAPTERS[provider]
    except KeyError as exc:
        raise ValueError(f"unsupported provider: {provider}") from exc


def supported_providers() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))
