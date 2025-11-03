"""Enhanced Exa search integration via Composio MCP with advanced features."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ...config import get_settings
from ...logging_config import logger

_DEFAULT_MAX_RESULTS = 5
_MAX_RESULTS = 20


class ComposioExaError(RuntimeError):
    """Raised when Composio Exa tools are unavailable or misconfigured."""


async def _call_composio_tool(
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Call a Composio Exa tool via MCP."""
    settings = get_settings()
    base_url = settings.composio_exa_mcp_url

    if not base_url:
        raise ComposioExaError("Composio MCP URL missing; set COMPOSIO_EXA_MCP_URL")

    # Ensure user_id is in URL
    if "?" in base_url:
        target_url = base_url if "user_id=" in base_url else f"{base_url}&user_id={settings.composio_exa_user_id or 'exa'}"
    else:
        target_url = f"{base_url}?user_id={settings.composio_exa_user_id or 'exa'}"

    try:
        async with streamablehttp_client(target_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_result = await session.call_tool(tool_name, arguments)
    except Exception as exc:
        logger.warning(f"Composio tool {tool_name} failed: {exc}")
        raise ComposioExaError(f"Failed to call {tool_name}: {exc}") from exc

    # Normalize response
    payload: Any = tool_result
    if hasattr(tool_result, "model_dump"):
        payload = tool_result.model_dump()
    elif hasattr(tool_result, "dict"):
        payload = tool_result.dict()

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, (list, tuple)):
        if payload and isinstance(payload[0], dict) and "text" in payload[0]:
            return {"data": [item.get("text", "") for item in payload]}
        return {"data": payload}

    return {"raw": str(payload)}


async def generate_answer_async(
    query: str,
    *,
    num_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a direct, citation-backed answer using Exa's AI.

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
        result = await _call_composio_tool("GENERATE_AN_ANSWER", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"generate_answer failed: {exc}")
        return {
            "query": query,
            "answer": None,
            "citations": [],
            "error": str(exc),
        }


async def find_similar_async(
    url: str,
    *,
    num_results: int = 10,
    include_text: bool = False,
    include_highlights: bool = False,
) -> Dict[str, Any]:
    """
    Find web pages semantically similar to a given URL.

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
        result = await _call_composio_tool("FIND_SIMILAR", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"find_similar failed: {exc}")
        return {
            "url": url,
            "results": [],
            "error": str(exc),
        }


async def get_contents_async(
    urls: List[str],
    *,
    include_text: bool = True,
    include_highlights: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve full content from a list of URLs or Exa document IDs.

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
        result = await _call_composio_tool("GET_CONTENTS_FROM_URLS_OR_DOCUMENT_IDS", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"get_contents failed: {exc}")
        return {
            "urls": urls,
            "contents": [],
            "error": str(exc),
        }


async def advanced_search_async(
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
    Advanced search with date filtering and categorization.

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
        result = await _call_composio_tool("SEARCH", arguments)
        return result
    except ComposioExaError as exc:
        logger.warning(f"advanced_search failed: {exc}")
        return {
            "query": query,
            "results": [],
            "error": str(exc),
        }


# Synchronous wrappers
def generate_answer(
    query: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Synchronous wrapper for generate_answer_async."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            generate_answer_async(query, **kwargs),
            loop,
        )
        return future.result()

    return asyncio.run(generate_answer_async(query, **kwargs))


def find_similar(
    url: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Synchronous wrapper for find_similar_async."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            find_similar_async(url, **kwargs),
            loop,
        )
        return future.result()

    return asyncio.run(find_similar_async(url, **kwargs))


def get_contents(
    urls: List[str],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Synchronous wrapper for get_contents_async."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            get_contents_async(urls, **kwargs),
            loop,
        )
        return future.result()

    return asyncio.run(get_contents_async(urls, **kwargs))


def advanced_search(
    query: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Synchronous wrapper for advanced_search_async."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            advanced_search_async(query, **kwargs),
            loop,
        )
        return future.result()

    return asyncio.run(advanced_search_async(query, **kwargs))


__all__ = [
    "ComposioExaError",
    "generate_answer",
    "generate_answer_async",
    "find_similar",
    "find_similar_async",
    "get_contents",
    "get_contents_async",
    "advanced_search",
    "advanced_search_async",
]
