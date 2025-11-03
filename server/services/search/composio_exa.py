"""Enhanced Exa search integration via Composio SDK (same pattern as Gmail)."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Optional

from ...config import get_settings
from ...logging_config import logger

_DEFAULT_MAX_RESULTS = 5
_MAX_RESULTS = 20

# Singleton client (same pattern as Gmail)
_CLIENT_LOCK = threading.Lock()
_CLIENT: Optional[Any] = None


class ComposioExaError(RuntimeError):
    """Raised when Composio Exa tools are unavailable or misconfigured."""


def _get_composio_client(settings: Optional[Any] = None):
    """Get or create singleton Composio client (same pattern as Gmail)."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    with _CLIENT_LOCK:
        if _CLIENT is None:
            from composio import Composio  # type: ignore

            resolved_settings = settings or get_settings()
            api_key = resolved_settings.composio_api_key
            try:
                _CLIENT = Composio(api_key=api_key) if api_key else Composio()
            except TypeError as exc:
                if api_key:
                    raise ComposioExaError(
                        "Installed Composio SDK does not accept api_key; upgrade SDK or remove COMPOSIO_API_KEY"
                    ) from exc
                _CLIENT = Composio()
    return _CLIENT


def _normalize_tool_response(result: Any) -> Dict[str, Any]:
    """Normalize Composio tool response (same pattern as Gmail)."""
    payload_dict: Optional[Dict[str, Any]] = None
    try:
        if hasattr(result, "model_dump"):
            payload_dict = result.model_dump()
        elif hasattr(result, "dict"):
            payload_dict = result.dict()
    except Exception:
        payload_dict = None

    if payload_dict is None:
        if isinstance(result, dict):
            payload_dict = result
        elif isinstance(result, list):
            payload_dict = {"items": result}
        else:
            payload_dict = {"repr": str(result)}

    return payload_dict


def _call_composio_tool(
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Call a Composio Exa tool via SDK (same pattern as Gmail)."""
    settings = get_settings()

    # For Exa tools, we use a generic user_id since no OAuth is needed
    user_id = settings.composio_exa_user_id or "exa-user"

    try:
        client = _get_composio_client(settings)
        result = client.client.tools.execute(
            tool_name,
            user_id=user_id,
            arguments=arguments,
        )
        return _normalize_tool_response(result)
    except Exception as exc:
        logger.exception(
            "composio exa tool execution failed",
            extra={"tool": tool_name, "user_id": user_id},
        )
        raise ComposioExaError(f"{tool_name} invocation failed: {exc}") from exc


def generate_answer_sync(
    query: str,
    *,
    num_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a direct, citation-backed answer using Exa's AI via Composio SDK.

    This is the most powerful search tool - it returns a synthesized answer
    with citations rather than just search results.

    Args:
        query: Natural language question or topic
        num_results: Number of sources to use for answer generation
        include_domains: Optional list of domains to prioritize
        exclude_domains: Optional list of domains to exclude

    Returns:
        Dict with 'answer' (text), 'citations' (list of sources), and metadata
    """
    arguments: Dict[str, Any] = {
        "query": query,
        "numResults": min(num_results, _MAX_RESULTS),
    }

    if include_domains:
        arguments["includeDomains"] = include_domains
    if exclude_domains:
        arguments["excludeDomains"] = exclude_domains

    try:
        result = _call_composio_tool("EXA_GENERATE_AN_ANSWER", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"generate_answer failed: {exc}")
        return {
            "query": query,
            "answer": None,
            "citations": [],
            "error": str(exc),
        }


def find_similar(
    url: str,
    *,
    num_results: int = 10,
    include_text: bool = False,
    include_highlights: bool = False,
) -> Dict[str, Any]:
    """
    Find web pages semantically similar to a given URL via Composio SDK.

    Uses embeddings-based search to find content similar to the reference URL.

    Args:
        url: Reference URL to find similar content for
        num_results: Number of similar pages to return
        include_text: Whether to include full text content
        include_highlights: Whether to include highlighted excerpts

    Returns:
        Dict with 'results' (list of similar pages) and metadata
    """
    arguments: Dict[str, Any] = {
        "url": url,
        "numResults": min(num_results, _MAX_RESULTS),
    }

    if include_text:
        arguments["text"] = True
    if include_highlights:
        arguments["highlights"] = True

    try:
        result = _call_composio_tool("EXA_FIND_SIMILAR", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"find_similar failed: {exc}")
        return {
            "url": url,
            "results": [],
            "error": str(exc),
        }


def get_contents(
    urls: List[str],
    *,
    include_text: bool = True,
    include_highlights: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve full content from a list of URLs or Exa document IDs via Composio SDK.

    Args:
        urls: List of URLs or Exa document IDs to fetch content from
        include_text: Whether to include full text content
        include_highlights: Whether to include highlighted excerpts

    Returns:
        Dict with 'contents' (list of retrieved content) and metadata
    """
    arguments: Dict[str, Any] = {
        "urls": urls,
    }

    if include_text:
        arguments["text"] = True
    if include_highlights:
        arguments["highlights"] = True

    try:
        result = _call_composio_tool("EXA_GET_CONTENTS_FROM_URLS_OR_DOCUMENT_IDS", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"get_contents failed: {exc}")
        return {
            "urls": urls,
            "contents": [],
            "error": str(exc),
        }


def advanced_search(
    query: str,
    *,
    num_results: int = 10,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Advanced search with date filtering and categorization via Composio SDK.

    Args:
        query: Search query
        num_results: Number of results
        include_domains: Domains to prioritize
        exclude_domains: Domains to exclude
        start_published_date: Start date filter (ISO format)
        end_published_date: End date filter (ISO format)
        category: Content category filter

    Returns:
        Dict with search results and metadata
    """
    arguments: Dict[str, Any] = {
        "query": query,
        "numResults": min(num_results, _MAX_RESULTS),
    }

    if include_domains:
        arguments["includeDomains"] = include_domains
    if exclude_domains:
        arguments["excludeDomains"] = exclude_domains
    if start_published_date:
        arguments["startPublishedDate"] = start_published_date
    if end_published_date:
        arguments["endPublishedDate"] = end_published_date
    if category:
        arguments["category"] = category

    try:
        result = _call_composio_tool("EXA_SEARCH", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"advanced_search failed: {exc}")
        return {
            "query": query,
            "results": [],
            "error": str(exc),
        }


# Keep the original function name for backwards compatibility
def generate_answer(query: str, **kwargs: Any) -> Dict[str, Any]:
    """Alias for generate_answer_sync."""
    return generate_answer_sync(query, **kwargs)


__all__ = [
    "ComposioExaError",
    "generate_answer",
    "generate_answer_sync",
    "find_similar",
    "get_contents",
    "advanced_search",
]
