"""Integration with the Exa search API."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import httpx

from ...config import get_settings
from ...logging_config import logger

_EXA_SEARCH_ENDPOINT = "https://api.exa.ai/search"


class ExaSearchError(RuntimeError):
    """Raised when Exa search cannot be completed."""


def _normalise_domains(domains: Optional[Iterable[str]]) -> Optional[List[str]]:
    if not domains:
        return None
    cleaned = [domain.strip() for domain in domains if isinstance(domain, str) and domain.strip()]
    return cleaned or None


def _extract_snippet(result: Dict[str, Any]) -> str:
    """Best-effort snippet extraction from Exa search results."""

    candidates: List[str] = []

    highlight = result.get("highlight")
    if isinstance(highlight, list):
        candidates.extend(str(item) for item in highlight if item)
    elif isinstance(highlight, (str, bytes)):
        candidates.append(highlight.decode("utf-8", errors="ignore") if isinstance(highlight, bytes) else highlight)
    elif isinstance(highlight, dict):
        snippet_value = highlight.get("snippet") or highlight.get("text")
        if isinstance(snippet_value, str):
            candidates.append(snippet_value)

    text_value = result.get("snippet") or result.get("text") or result.get("content")
    if isinstance(text_value, str):
        candidates.append(text_value)

    markdown_value = result.get("markdown")
    if isinstance(markdown_value, str):
        candidates.append(markdown_value)

    snippet = next((candidate.strip() for candidate in candidates if candidate and candidate.strip()), "")
    return snippet[:500]


def search_exa(
    query: str,
    *,
    num_results: int = 5,
    include_domains: Optional[Iterable[str]] = None,
    exclude_domains: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Run a neural web search via Exa and return normalised results.

    Parameters
    ----------
    query: str
        Search query text.
    num_results: int, optional
        Maximum number of results to return (clamped between 1 and 20).
    include_domains / exclude_domains: iterable[str], optional
        Domain filters to pass through to Exa.
    """

    settings = get_settings()
    api_key = settings.exa_api_key
    if not api_key:
        raise ExaSearchError("EXA_API_KEY is not configured")

    limit = max(1, min(int(num_results or 5), 20))
    payload: Dict[str, Any] = {
        "query": query,
        "type": "neural",
        "numResults": limit,
        "includeText": True,
    }

    include = _normalise_domains(include_domains)
    if include:
        payload["includeDomains"] = include
    exclude = _normalise_domains(exclude_domains)
    if exclude:
        payload["excludeDomains"] = exclude

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            response = client.post(_EXA_SEARCH_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network failures
        body = exc.response.text if exc.response else ""
        message = f"Exa search failed with status {exc.response.status_code if exc.response else 'unknown'}: {body}"
        logger.warning(message)
        raise ExaSearchError(message) from exc
    except httpx.HTTPError as exc:  # pragma: no cover - network failures
        message = f"Exa search request error: {exc}".strip()
        logger.warning(message)
        raise ExaSearchError(message) from exc

    data = response.json()
    raw_results = data.get("results")
    if not isinstance(raw_results, list):
        logger.debug("Unexpected Exa response payload: %s", data)
        raw_results = []

    normalised_results: List[Dict[str, Any]] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        normalised_results.append(
            {
                "title": (item.get("title") or item.get("id") or "Untitled").strip(),
                "url": item.get("url"),
                "score": item.get("score"),
                "snippet": _extract_snippet(item),
                "published": item.get("publishedDate") or item.get("published"),
            }
        )

    return {
        "query": query,
        "results": normalised_results,
    }

```},