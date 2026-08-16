"""Public job-source adapters used by the SignalFit discovery scanner."""

from .adapters import get_adapter, supported_providers
from .base import FetchResponse, HttpClient, SourceAdapter
from .raw_store import write_raw_snapshot
from .resolver import ProviderResolution, detect_provider, resolve_source

__all__ = [
    "FetchResponse",
    "HttpClient",
    "ProviderResolution",
    "SourceAdapter",
    "detect_provider",
    "get_adapter",
    "resolve_source",
    "supported_providers",
    "write_raw_snapshot",
]
