"""Telegram service for sending messages asynchronously."""

import os
from typing import Optional

import httpx

from ..logging_config import logger


class TelegramService:
    """Service for sending messages to Telegram users asynchronously."""

    def __init__(self):
        """Initialize Telegram service with bot token from environment."""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set - Telegram notifications disabled")

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def send_typing_action(self, chat_id: str) -> bool:
        """
        Send typing action to show the bot is processing.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if action was sent successfully, False otherwise
        """
        if not self.bot_token:
            return False

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/sendChatAction",
                json={
                    "chat_id": chat_id,
                    "action": "typing",
                }
            )
            return response.status_code == 200
        except Exception:
            # Typing action is not critical, don't log errors
            return False

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown"
    ) -> bool:
        """
        Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text to send
            parse_mode: Message formatting (Markdown or HTML)

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.bot_token:
            logger.error("Cannot send Telegram message - bot token not configured")
            return False

        # Telegram max message length is 4096 characters
        MAX_LENGTH = 4000  # Leave some margin
        if len(text) > MAX_LENGTH:
            logger.warning(
                f"Message too long ({len(text)} chars), truncating to {MAX_LENGTH}",
                extra={"chat_id": chat_id}
            )
            text = text[:MAX_LENGTH - 50] + "\n\n...(message tronqué car trop long)"

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                }
            )

            if response.status_code == 200:
                logger.info(
                    "Telegram message sent",
                    extra={
                        "chat_id": chat_id,
                        "text_length": len(text),
                    }
                )
                return True
            else:
                logger.error(
                    "Telegram API error",
                    extra={
                        "status_code": response.status_code,
                        "response": response.text[:200],
                    }
                )
                return False

        except Exception as exc:
            logger.error(
                "Failed to send Telegram message",
                extra={
                    "error": str(exc),
                    "chat_id": chat_id,
                }
            )
            return False

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global singleton instance
_telegram_service: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """Get the global Telegram service instance."""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service
