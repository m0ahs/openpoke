"""Telegram-specific routes for handling bot messages."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents.interaction_agent import InteractionAgentRuntime
from ..logging_config import logger

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramMessageRequest(BaseModel):
    """Request model for Telegram messages."""
    message: str
    chat_id: str


class TelegramMessageResponse(BaseModel):
    """Response model for Telegram messages."""
    response: str
    success: bool
    error: str | None = None


@router.post("/message", response_model=TelegramMessageResponse)
async def handle_telegram_message(request: TelegramMessageRequest) -> TelegramMessageResponse:
    """
    Handle incoming Telegram messages.

    This endpoint is specifically designed for the Telegram watcher to send messages
    and receive responses without CORS restrictions.
    """
    try:
        logger.info(
            "Telegram message received",
            extra={
                "chat_id": request.chat_id,
                "message_length": len(request.message),
                "message_preview": request.message[:100]
            }
        )

        runtime = InteractionAgentRuntime()
        result = await runtime.execute(user_message=request.message)

        # Always return a response, even on errors
        if result.response and result.response.strip():
            return TelegramMessageResponse(
                response=result.response,
                success=result.success,
                error=result.error
            )

        # If no response but success (e.g., wait tool used)
        if result.success:
            return TelegramMessageResponse(
                response="Je n'ai pas généré de réponse pour ce message. Peut-être que c'était un doublon.",
                success=True,
                error=None
            )

        # If error but no response message
        error_msg = result.error or "Une erreur s'est produite"
        return TelegramMessageResponse(
            response=f"Désolé, j'ai rencontré un problème : {error_msg}",
            success=False,
            error=error_msg
        )

    except Exception as e:
        logger.exception("Error handling Telegram message", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
