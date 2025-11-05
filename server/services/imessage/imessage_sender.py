"""
iMessage Sender for Alyn

Provides a Python interface to send iMessages via the Node.js SDK.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from ...logging_config import logger


class IMessageSender:
    """Send iMessages via the Node.js imessage-kit SDK."""

    def __init__(self):
        """Initialize the iMessage sender."""
        self.node_script = Path(__file__).parent / "send_message.js"
        self.enabled = True

        # Check if Node.js is available
        try:
            subprocess.run(
                ["node", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Node.js not found - iMessage sending disabled")
            self.enabled = False

    async def send(self, recipient: str, message: str) -> bool:
        """
        Send an iMessage to a recipient.

        Args:
            recipient: Phone number or email address
            message: Message text to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("iMessage sending is disabled")
            return False

        try:
            # Call the Node.js script to send the message
            process = await asyncio.create_subprocess_exec(
                "node",
                str(self.node_script),
                recipient,
                message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(
                    "imessage sent",
                    extra={
                        "recipient": recipient,
                        "message_length": len(message)
                    }
                )
                return True
            else:
                error_msg = stderr.decode().strip()
                logger.error(
                    "imessage send failed",
                    extra={
                        "recipient": recipient,
                        "error": error_msg
                    }
                )
                return False

        except Exception as exc:
            logger.error(
                "imessage send error",
                extra={
                    "recipient": recipient,
                    "error": str(exc)
                }
            )
            return False


# Global sender instance
_sender: Optional[IMessageSender] = None


def get_sender() -> IMessageSender:
    """Get or create the global iMessage sender instance."""
    global _sender
    if _sender is None:
        _sender = IMessageSender()
    return _sender


async def send_imessage(recipient: str, message: str) -> bool:
    """
    Convenience function to send an iMessage.

    Args:
        recipient: Phone number or email address
        message: Message text to send

    Returns:
        True if message was sent successfully, False otherwise
    """
    sender = get_sender()
    return await sender.send(recipient, message)
