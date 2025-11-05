"""
Message Context for iMessage Integration

Provides thread-local context to track the source of incoming messages
so responses can be sent via the appropriate channel (HTTP vs iMessage).
"""

import contextvars
from dataclasses import dataclass
from typing import Optional


@dataclass
class MessageContext:
    """Context information about the current message being processed."""

    source: str  # "http" or "imessage"
    sender: Optional[str] = None  # Phone number or email for iMessage
    timestamp: Optional[str] = None  # ISO timestamp


# Context variable for tracking message source across async calls
_message_context: contextvars.ContextVar[Optional[MessageContext]] = contextvars.ContextVar(
    "message_context",
    default=None
)


def set_message_context(context: MessageContext) -> None:
    """Set the message context for the current async context."""
    _message_context.set(context)


def get_message_context() -> Optional[MessageContext]:
    """Get the current message context, if any."""
    return _message_context.get()


def clear_message_context() -> None:
    """Clear the message context."""
    _message_context.set(None)
