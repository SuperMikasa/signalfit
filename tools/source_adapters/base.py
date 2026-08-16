"""Small, dependency-free primitives for public job-source adapters."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class FetchResponse:
    request_url: str
    final_url: str
    status_code: int
    content_type: str
    body: bytes
    audit: dict[str, Any] | None = None

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class HttpClient:
    def __init__(self, user_agent: str, timeout: int = 45) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def get(self, url: str, accept: str = "application/json") -> FetchResponse:
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": accept})
        with urlopen(request, timeout=self.timeout) as response:
            return FetchResponse(
                request_url=url,
                final_url=response.geturl(),
                status_code=int(getattr(response, "status", 200)),
                content_type=str(response.headers.get("Content-Type") or ""),
                body=response.read(),
            )


class SourceAdapter(ABC):
    provider: str
    validation_method = "official_ats_api+strict_date_window+body_readable"

    @abstractmethod
    def endpoint(self, source: dict[str, Any]) -> str:
        """Return the public source endpoint used for discovery."""

    def fetch(self, source: dict[str, Any], client: HttpClient) -> FetchResponse:
        return client.get(self.endpoint(source))

    @abstractmethod
    def normalize(self, source: dict[str, Any], response: FetchResponse) -> list[dict[str, Any]]:
        """Convert a provider response into SignalFit's normalized job contract."""

    def job(
        self,
        source: dict[str, Any],
        *,
        provider_job_id: Any,
        title: Any,
        source_url: Any,
        location: Any,
        posted_at: Any,
        timestamp_basis: str,
        description: Any,
        company: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "board": str(source.get("board") or ""),
            "company": str(company or source.get("company") or ""),
            "allow_generic_ai_pm": bool(source.get("allow_generic_ai_pm")),
            "provider_job_id": str(provider_job_id or ""),
            "title": str(title or ""),
            "source_url": str(source_url or ""),
            "location": str(location or "Unspecified"),
            "posted_at": posted_at,
            "timestamp_basis": timestamp_basis,
            "description": str(description or ""),
            "validation_method": self.validation_method,
        }
