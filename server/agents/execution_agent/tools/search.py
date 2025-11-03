"""Search tool schemas and handlers for the execution agent using Composio/Exa."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from server.services.search.exa import ExaSearchError, search_exa
from server.services.execution import get_execution_agent_logs

_LOG_STORE = get_execution_agent_logs()
_SEARCH_AGENT_NAME = "search-execution-agent"

_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web via the Exa engine using the configured MCP gateway and return curated results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to send to Exa. Be specific and detailed for best results.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search for recent news articles on a specific topic using trusted news sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news topic to search for.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of news articles to return (defaults to 10, capped at 20).",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_topic",
            "description": "Conduct comprehensive research on a topic, optionally focusing on specific aspects. Returns diverse perspectives and sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The main topic to research in depth.",
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional specific aspects to focus on (e.g., ['history', 'current developments', 'future outlook']).",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of sources to gather per focus area (defaults to 10, capped at 20).",
                    },
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_company",
            "description": "Search for comprehensive information about a company including news, financials, leadership, products, and public information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "The name of the company to research.",
                    },
                    "aspects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific aspects to research (e.g., ['news', 'financials', 'leadership', 'products']). Defaults to ['news', 'overview'].",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results per aspect (defaults to 8, capped at 15).",
                    },
                },
                "required": ["company_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_academic",
            "description": "Search for academic papers, research articles, and scholarly sources on a topic from academic databases and journals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research topic or academic question to find sources for.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of academic sources to find (defaults to 10, capped at 20).",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]


def get_schemas() -> List[Dict[str, Any]]:
    """Return search tool schemas."""

    return _SCHEMAS


def build_registry(_: str) -> Dict[str, Callable[..., Any]]:
    """Return callable registry for search tools."""

    return {
        "search_web": search_web,
        "search_news": search_news,
        "research_topic": research_topic,
        "search_company": search_company,
        "search_academic": search_academic,
    }


def _log_search(tool_name: str, query: str, success: bool, result_count: int = 0, error: Optional[str] = None) -> None:
    """Log search action to execution agent journal."""
    if success:
        _LOG_STORE.record_action(
            _SEARCH_AGENT_NAME,
            description=f"{tool_name} succeeded | query='{query}' | results={result_count}",
        )
    else:
        _LOG_STORE.record_action(
            _SEARCH_AGENT_NAME,
            description=f"{tool_name} failed | query='{query}' | error={error}",
        )


def search_web(
    query: str,
    num_results: Optional[int] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute a web search via the Exa engine using the configured MCP gateway."""

    try:
        result = search_exa(
            query,
            num_results=num_results or 5,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        _log_search("search_web", query, success=True, result_count=len(result.get("results", [])))
        return result
    except ExaSearchError as exc:
        error_msg = str(exc)
        _log_search("search_web", query, success=False, error=error_msg)
        return {
            "query": query,
            "results": [],
            "error": error_msg,
            "error_type": "search_unavailable",
        }
    except Exception as exc:
        error_msg = str(exc)
        _log_search("search_web", query, success=False, error=error_msg)
        return {
            "query": query,
            "results": [],
            "error": f"Unexpected error: {error_msg}",
            "error_type": "unknown",
        }


def search_news(
    query: str,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Search for recent news articles using trusted news sources."""

    # Focus on major news domains for news search
    news_domains = [
        "nytimes.com",
        "wsj.com",
        "reuters.com",
        "bloomberg.com",
        "bbc.com",
        "theguardian.com",
        "cnn.com",
        "apnews.com",
        "npr.org",
        "ft.com",
        "economist.com",
        "politico.com",
    ]

    try:
        result = search_exa(
            query,
            num_results=num_results or 10,
            include_domains=news_domains,
        )
        _log_search("search_news", query, success=True, result_count=len(result.get("results", [])))
        return result
    except ExaSearchError as exc:
        error_msg = str(exc)
        _log_search("search_news", query, success=False, error=error_msg)
        return {
            "query": query,
            "results": [],
            "error": error_msg,
            "error_type": "search_unavailable",
        }
    except Exception as exc:
        error_msg = str(exc)
        _log_search("search_news", query, success=False, error=error_msg)
        return {
            "query": query,
            "results": [],
            "error": f"Unexpected error: {error_msg}",
            "error_type": "unknown",
        }


def research_topic(
    topic: str,
    focus_areas: Optional[List[str]] = None,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Conduct comprehensive research on a topic with optional focus areas."""

    if not focus_areas:
        # Single comprehensive search
        return search_web(topic, num_results=num_results or 10)

    # Search for each focus area
    results_by_area: Dict[str, Any] = {
        "topic": topic,
        "focus_areas": {},
        "total_results": 0,
    }

    results_per_area = max(3, (num_results or 10) // len(focus_areas))

    for area in focus_areas:
        query = f"{topic} {area}"
        try:
            area_results = search_exa(query, num_results=results_per_area)
            results_by_area["focus_areas"][area] = area_results.get("results", [])
            results_by_area["total_results"] += len(area_results.get("results", []))
        except ExaSearchError as exc:
            results_by_area["focus_areas"][area] = {
                "error": str(exc),
                "results": [],
            }

    _log_search("research_topic", topic, success=True, result_count=results_by_area["total_results"])
    return results_by_area


def search_company(
    company_name: str,
    aspects: Optional[List[str]] = None,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Search for comprehensive information about a company."""

    if not aspects:
        aspects = ["news", "overview"]

    company_results: Dict[str, Any] = {
        "company": company_name,
        "aspects": {},
        "total_results": 0,
    }

    results_per_aspect = num_results or 8

    for aspect in aspects:
        query = f"{company_name} {aspect}"
        try:
            aspect_results = search_exa(query, num_results=results_per_aspect)
            company_results["aspects"][aspect] = aspect_results.get("results", [])
            company_results["total_results"] += len(aspect_results.get("results", []))
        except ExaSearchError as exc:
            company_results["aspects"][aspect] = {
                "error": str(exc),
                "results": [],
            }

    _log_search("search_company", company_name, success=True, result_count=company_results["total_results"])
    return company_results


def search_academic(
    query: str,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Search for academic papers and scholarly sources."""

    # Focus on academic and research domains
    academic_domains = [
        "scholar.google.com",
        "arxiv.org",
        "pubmed.ncbi.nlm.nih.gov",
        "jstor.org",
        "sciencedirect.com",
        "springer.com",
        "nature.com",
        "science.org",
        "ieee.org",
        "acm.org",
        "ncbi.nlm.nih.gov",
    ]

    try:
        result = search_exa(
            query,
            num_results=num_results or 10,
            include_domains=academic_domains,
        )
        _log_search("search_academic", query, success=True, result_count=len(result.get("results", [])))
        return result
    except ExaSearchError as exc:
        error_msg = str(exc)
        _log_search("search_academic", query, success=False, error=error_msg)
        return {
            "query": query,
            "results": [],
            "error": error_msg,
            "error_type": "search_unavailable",
        }
    except Exception as exc:
        error_msg = str(exc)
        _log_search("search_academic", query, success=False, error=error_msg)
        return {
            "query": query,
            "results": [],
            "error": f"Unexpected error: {error_msg}",
            "error_type": "unknown",
        }


__all__ = [
    "build_registry",
    "get_schemas",
    "search_web",
    "search_news",
    "research_topic",
    "search_company",
    "search_academic",
]
