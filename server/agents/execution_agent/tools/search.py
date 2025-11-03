"""Search tool schemas and handler for the execution agent."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from server.services.search.exa import ExaSearchError, search_exa

_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web via the Exa engine using Smithery MCP and return curated results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to send to Exa.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Maximum number of web results to return (defaults to 5, capped at 20).",
                    },
                    "include_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of domains that should be prioritised in the results.",
                    },
                    "exclude_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of domains that should be filtered out from the results.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }
]


def get_schemas() -> List[Dict[str, Any]]:
    """Return search tool schemas."""

    return _SCHEMAS


def build_registry(_: str) -> Dict[str, Callable[..., Any]]:
    """Return callable registry for search tools."""

    return {
        "search_web": search_web,
    }


def search_web(
    query: str,
    num_results: Optional[int] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute a Smithery-backed Exa web search."""

    try:
        return search_exa(
            query,
            num_results=num_results or 5,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
    except ExaSearchError as exc:
        return {
            "error": str(exc),
        }
