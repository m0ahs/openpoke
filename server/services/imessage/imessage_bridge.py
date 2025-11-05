#!/usr/bin/env python3
"""
iMessage Bridge for Alyn

Receives messages from the Node.js iMessage watcher and forwards them
to the Alyn interaction agent for processing.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.interaction_agent.runtime import InteractionAgentRuntime
from logging_config import logger
from services.imessage import MessageContext, set_message_context


async def process_imessage(sender: str, text: str, timestamp: str) -> None:
    """
    Process an incoming iMessage by forwarding it to the interaction agent.

    Args:
        sender: Phone number or email of the sender
        text: Message content
        timestamp: ISO timestamp of when the message was received
    """
    logger.info(
        "imessage received",
        extra={
            "sender": sender,
            "message_length": len(text),
            "timestamp": timestamp
        }
    )

    try:
        # Set context so responses go to iMessage
        set_message_context(MessageContext(
            source="imessage",
            sender=sender,
            timestamp=timestamp
        ))

        runtime = InteractionAgentRuntime()

        # Execute the interaction agent with the user message
        # The runtime will handle tool calls, including sending responses
        await runtime.execute(user_message=text)

        logger.info("imessage processed successfully", extra={"sender": sender})
        print(f"Message from {sender} processed successfully")

    except ValueError as ve:
        logger.error("configuration error", extra={"error": str(ve)})
        print(f"Configuration error: {ve}", file=sys.stderr)
        sys.exit(1)

    except Exception as exc:
        logger.error(
            "imessage processing failed",
            extra={
                "sender": sender,
                "error": str(exc)
            }
        )
        print(f"Error processing message: {exc}", file=sys.stderr)
        sys.exit(1)


def main():
    """Parse command line arguments and process the iMessage."""
    parser = argparse.ArgumentParser(description="Process iMessage for Alyn")
    parser.add_argument("--sender", required=True, help="Sender phone/email")
    parser.add_argument("--text", required=True, help="Message text")
    parser.add_argument("--timestamp", required=True, help="ISO timestamp")

    args = parser.parse_args()

    # Run async processing
    asyncio.run(process_imessage(args.sender, args.text, args.timestamp))


if __name__ == "__main__":
    main()
