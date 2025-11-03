"""Exa search integration via Smithery MCP server."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ...config import get_settings
from ...logging_config import logger

_DEFAULT_MAX_RESULTS = 5
_MAX_RESULTS = 20


class ExaSearchError(RuntimeError):
    """Raised when the Exa search backend is unavailable or misconfigured."""


def _normalise_domains(domains: Optional[Iterable[str]]) -> Optional[List[str]]:
    if not domains:
        return None
    cleaned = [domain.strip() for domain in domains if isinstance(domain, str) and domain.strip()]
    return cleaned or None


async def _fetch_via_mcp(
    query: str,
    limit: int,
    include_domains: Optional[List[str]],
    exclude_domains: Optional[List[str]],
) -> Dict[str, Any]:
    settings = get_settings()
    api_key = settings.smithery_exa_api_key
    profile = settings.smithery_exa_profile
    base_url = settings.smithery_base_url
    tool_name = settings.smithery_exa_tool_name or "exa_search"

    if not api_key or not profile:
        raise ExaSearchError("Smithery credentials missing; set SMITHERY_EXA_API_KEY and SMITHERY_EXA_PROFILE")
    if not base_url:
        raise ExaSearchError("Smithery base URL missing; set SMITHERY_BASE_URL")

    params = urlencode({"api_key": api_key, "profile": profile})
    separator = "&" if "?" in base_url else "?"
    target_url = f"{base_url}{separator}{params}"

    arguments: Dict[str, Any] = {
        "query": query,
        "numResults": limit,
    }
    if include_domains:
        arguments["includeDomains"] = include_domains
    if exclude_domains:
        arguments["excludeDomains"] = exclude_domains

    async with streamablehttp_client(target_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_result = await session.call_tool(tool_name, arguments)

    payload: Any = tool_result
    if hasattr(tool_result, "model_dump"):
        payload = tool_result.model_dump()
    elif hasattr(tool_result, "dict"):
        payload = tool_result.dict()

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, (list, tuple)):
        texts: List[str] = []
        for item in payload:
            if isinstance(item, dict) and "text" in item:
                texts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                texts.append(item)
        combined = "\n".join(texts).strip()
        if combined:
            try:
                return json.loads(combined)
            except json.JSONDecodeError:
                return {"raw": combined}

    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload}

    return {"raw": repr(payload)}


async def search_exa_async(
    query: str,
    *,
    num_results: int = _DEFAULT_MAX_RESULTS,
    include_domains: Optional[Iterable[str]] = None,
    exclude_domains: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Execute an Exa search request via Smithery MCP."""

    limit = max(1, min(int(num_results or _DEFAULT_MAX_RESULTS), _MAX_RESULTS))
    include = _normalise_domains(include_domains)
    exclude = _normalise_domains(exclude_domains)

    try:
        raw_payload = await _fetch_via_mcp(query, limit, include, exclude)
    except Exception as exc:  # pragma: no cover - network/SDK failures
        logger.warning("Exa search failed: %s", exc)
        if isinstance(exc, ExaSearchError):
            raise
        raise ExaSearchError(str(exc)) from exc

    results = raw_payload.get("results") if isinstance(raw_payload, dict) else None

    if not isinstance(results, list):
        return {
            "query": query,
            "results": [],
            "raw": raw_payload,
        }

    normalised: List[Dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        normalised.append(
            {
                "title": (item.get("title") or item.get("id") or "Untitled").strip(),
                "url": item.get("url"),
                "score": item.get("score"),
                "snippet": item.get("snippet") or item.get("text"),
                "published": item.get("publishedDate") or item.get("published"),
            }
        )

    return {
        "query": query,
        "results": normalised,
    }


def search_exa(
    query: str,
    *,
    num_results: int = _DEFAULT_MAX_RESULTS,
    include_domains: Optional[Iterable[str]] = None,
    exclude_domains: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Synchronously execute an Exa search via Smithery."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            search_exa_async(
                query,
                num_results=num_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            ),
            loop,
        )
        return future.result()

    return asyncio.run(
        search_exa_async(
            query,
            num_results=num_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
    )
