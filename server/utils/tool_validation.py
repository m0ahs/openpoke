"""Shared tool validation utilities for agents."""

from typing import List, Set


def split_known_tools(name: str, known_tools: Set[str]) -> List[str]:
    """
    Attempt to split a concatenated tool name into known tool identifiers.

    This function tries to detect when an LLM has hallucinated a concatenated
    tool name by greedily matching against known tool names from longest to shortest.

    Args:
        name: The potentially concatenated tool name
        known_tools: Set of valid tool names to match against

    Returns:
        List of individual tool names if the input is a concatenation,
        empty list if no valid split is found

    Examples:
        >>> split_known_tools("send_message_to_agentsend_draft",
        ...                   {"send_message_to_agent", "send_draft"})
        ['send_message_to_agent', 'send_draft']

        >>> split_known_tools("gmail_send_email",
        ...                   {"gmail_send_email"})
        []  # Single valid tool, not a concatenation
    """
    remaining = name
    result: List[str] = []
    sorted_tools = sorted(known_tools, key=len, reverse=True)

    while remaining:
        match = next((tool for tool in sorted_tools if remaining.startswith(tool)), None)
        if match is None:
            return []
        result.append(match)
        remaining = remaining[len(match):]

    return result


def get_interaction_tool_names() -> Set[str]:
    """
    Get the set of known interaction agent tool names.

    Returns:
        Set of valid interaction agent tool names
    """
    return {
        "send_message_to_agent",
        "send_message_to_user",
        "send_draft",
        "wait",
        "remove_agent",
    }


def get_execution_tool_names() -> Set[str]:
    """
    Get the set of known execution agent tool names.

    This dynamically imports and extracts tool names from the execution agent
    tool registry to avoid circular imports.

    Returns:
        Set of valid execution agent tool names
    """
    from ..agents.execution_agent.tools import get_tool_schemas

    tool_names: Set[str] = set()
    schemas = get_tool_schemas()

    for schema in schemas:
        if "function" in schema and "name" in schema["function"]:
            tool_names.add(schema["function"]["name"])

    return tool_names


def get_all_known_tool_names() -> Set[str]:
    """
    Get the combined set of all known tool names from both agents.

    Returns:
        Set of all valid tool names
    """
    return get_interaction_tool_names() | get_execution_tool_names()


__all__ = [
    "split_known_tools",
    "get_interaction_tool_names",
    "get_execution_tool_names",
    "get_all_known_tool_names",
]
