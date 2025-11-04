"""Interaction Agent Runtime - handles LLM calls for user and agent turns."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .agent import build_system_prompt, prepare_message_with_history
from .tools import ToolResult, get_tool_schemas, handle_tool_call, _split_known_tools
from .reminder_parser import ReminderMessageParser, ReminderMessageType
from ..tool_parsing import parse_tool_calls, ParsedToolCall
from ..tool_formatting import format_tool_result
from ...config import get_settings
from ...services.conversation import (
    get_conversation_log,
    get_duplicate_detector,
    get_working_memory_log,
)
from ...openrouter_client import request_chat_completion
from ...logging_config import logger
from ...utils.exceptions import AgentExecutionError, OpenPokeError, ToolExecutionError
from ...utils.json_utils import safe_json_dump, safe_json_load


@dataclass
class InteractionResult:
    """Result from the interaction agent."""

    success: bool
    response: str
    error: Optional[str] = None
    execution_agents_used: int = 0


@dataclass
class _LoopSummary:
    """Aggregate information produced by the interaction loop."""

    last_assistant_text: str = ""
    user_messages: List[str] = field(default_factory=list)
    tool_names: List[str] = field(default_factory=list)
    execution_agents: Set[str] = field(default_factory=set)


class InteractionAgentRuntime:
    """Manages the interaction agent's request processing."""

    MAX_TOOL_ITERATIONS = 8

    # Initialize interaction agent runtime with settings and service dependencies
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openrouter_api_key
        self.model = settings.interaction_agent_model
        self.settings = settings
        self.conversation_log = get_conversation_log()
        self.working_memory_log = get_working_memory_log()
        self.tool_schemas = get_tool_schemas()
        self.reminder_parser = ReminderMessageParser()


        # Initialize duplicate detector with settings
        self.duplicate_detector = get_duplicate_detector(
            cache_size=settings.duplicate_detection_cache_size,
            time_window_seconds=settings.duplicate_detection_time_window,
        )

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable."
            )

    # Main entry point for processing user messages through the LLM interaction loop
    async def execute(self, user_message: str) -> InteractionResult:
        """Handle a user-authored message."""

        logger.info(
            "Processing user message",
            extra={"message_preview": user_message[:100], "message_length": len(user_message)}
        )

        # Check for duplicate user messages using DuplicateDetector
        user_msg_dict = {"role": "user", "content": user_message}
        if self.duplicate_detector.check_and_mark(user_msg_dict, role="user"):
            logger.info("Duplicate user message detected, skipping processing")
            return InteractionResult(
                success=True,
                response="",
                execution_agents_used=0,
            )

        try:
            transcript_before = await self._load_conversation_transcript()
            await self.conversation_log.record_user_message(user_message)

            system_prompt = build_system_prompt()
            messages = prepare_message_with_history(
                user_message, transcript_before, message_type="user"
            )

            logger.debug("Starting interaction loop for user message")
            summary = await self._run_interaction_loop(system_prompt, messages)

            final_response = self._finalize_response(summary)

            if final_response:
                if self._should_emit_assistant_reply(final_response):
                    if not summary.user_messages:
                        await self.conversation_log.record_reply(final_response)
                else:
                    final_response = ""

            return InteractionResult(
                success=True,
                response=final_response,
                execution_agents_used=len(summary.execution_agents),
            )

        except json.JSONDecodeError as exc:
            # Handle JSON parsing errors
            logger.warning(
                "Interaction agent JSON decode error",
                extra={"error": str(exc), "doc": exc.doc[:100] if hasattr(exc, 'doc') else None}
            )
            return InteractionResult(
                success=False,
                response="",
                error=f"JSON parsing failed: {str(exc)}",
            )
        except (ValueError, KeyError, TypeError) as exc:
            # Handle expected data validation errors
            logger.warning(
                "Interaction agent data validation error",
                extra={"error": str(exc), "error_type": type(exc).__name__}
            )
            return InteractionResult(
                success=False,
                response="",
                error=f"Invalid data: {str(exc)}",
            )
        except AgentExecutionError as exc:
            # Handle agent-specific errors
            logger.error(
                "Interaction agent execution failed",
                extra={"error": str(exc), "agent": exc.agent_name, "details": exc.details},
                exc_info=True
            )
            return InteractionResult(
                success=False,
                response="",
                error=str(exc),
            )
        except OpenPokeError as exc:
            logger.error(
                "Interaction agent unexpected domain error",
                extra={"error": str(exc), "error_type": type(exc).__name__},
                exc_info=True,
            )
            return InteractionResult(
                success=False,
                response="",
                error=str(exc),
            )

    # Handle incoming messages from execution agents and generate appropriate responses
    async def handle_agent_message(self, agent_message: str) -> InteractionResult:
        """Process a status update emitted by an execution agent."""

        logger.info(f"Interaction agent received agent message: {agent_message[:100]}...")

        # Check for duplicate agent messages using DuplicateDetector
        agent_msg_dict = {"role": "execution_agent", "content": agent_message}
        if self.duplicate_detector.check_and_mark(agent_msg_dict, role="execution_agent"):
            logger.info("Duplicate agent message detected, skipping processing")
            return InteractionResult(
                success=True,
                response="",
                execution_agents_used=0,
            )

        # Special handling for reminder-related messages using structured parser
        parsed_reminder = self.reminder_parser.parse(agent_message)

        if parsed_reminder.message_type == ReminderMessageType.NOTIFICATION:
            reminder_text = self.reminder_parser.format_notification(parsed_reminder)
            await self.conversation_log.record_reply(reminder_text)
            return InteractionResult(
                success=True,
                response=reminder_text,
                execution_agents_used=1,
            )

        if parsed_reminder.message_type == ReminderMessageType.CREATION:
            creation_message = self.reminder_parser.format_creation(parsed_reminder)
            await self.conversation_log.record_reply(creation_message)
            return InteractionResult(
                success=True,
                response=creation_message,
                execution_agents_used=1,
            )

        if parsed_reminder.message_type == ReminderMessageType.GENERAL:
            response = self.reminder_parser.format_general(parsed_reminder)
            await self.conversation_log.record_reply(response)
            return InteractionResult(
                success=True,
                response=response,
                execution_agents_used=1,
            )

        try:
            transcript_before = await self._load_conversation_transcript()
            await self.conversation_log.record_agent_message(agent_message)

            system_prompt = build_system_prompt()
            messages = prepare_message_with_history(
                agent_message, transcript_before, message_type="agent"
            )

            logger.debug("Starting interaction loop for agent message")
            summary = await self._run_interaction_loop(system_prompt, messages)

            final_response = self._finalize_response(summary)

            if final_response:
                if self._should_emit_assistant_reply(final_response):
                    if not summary.user_messages:
                        await self.conversation_log.record_reply(final_response)
                else:
                    final_response = ""

            return InteractionResult(
                success=True,
                response=final_response,
                execution_agents_used=len(summary.execution_agents),
            )

        except json.JSONDecodeError as exc:
            # Handle JSON parsing errors
            logger.warning(
                "Interaction agent (agent message) JSON decode error",
                extra={"error": str(exc), "doc": exc.doc[:100] if hasattr(exc, 'doc') else None}
            )
            return InteractionResult(
                success=False,
                response="",
                error=f"JSON parsing failed: {str(exc)}",
            )
        except (ValueError, KeyError, TypeError) as exc:
            # Handle expected data validation errors
            logger.warning(
                "Interaction agent (agent message) data validation error",
                extra={"error": str(exc), "error_type": type(exc).__name__}
            )
            return InteractionResult(
                success=False,
                response="",
                error=f"Invalid data: {str(exc)}",
            )
        except AgentExecutionError as exc:
            # Handle agent-specific errors
            logger.error(
                "Interaction agent (agent message) execution failed",
                extra={"error": str(exc), "agent": exc.agent_name, "details": exc.details},
                exc_info=True
            )
            return InteractionResult(
                success=False,
                response="",
                error=str(exc),
            )
        except OpenPokeError as exc:
            logger.error(
                "Interaction agent (agent message) unexpected domain error",
                extra={"error": str(exc), "error_type": type(exc).__name__},
                exc_info=True,
            )
            return InteractionResult(
                success=False,
                response="",
                error=str(exc),
            )

    # Core interaction loop that handles LLM calls and tool executions until completion
    async def _run_interaction_loop(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
    ) -> _LoopSummary:
        """Iteratively query the LLM until it issues a final response."""

        summary = _LoopSummary()

        for iteration in range(self.MAX_TOOL_ITERATIONS):
            response = await self._make_llm_call(system_prompt, messages)
            assistant_message = self._extract_assistant_message(response)

            assistant_content = (assistant_message.get("content") or "").strip()
            if assistant_content:
                summary.last_assistant_text = assistant_content

            raw_tool_calls = assistant_message.get("tool_calls") or []
            parsed_tool_calls = self._parse_tool_calls(raw_tool_calls)

            assistant_entry: Dict[str, Any] = {
                "role": "assistant",
                "content": assistant_message.get("content", "") or "",
            }
            if raw_tool_calls:
                assistant_entry["tool_calls"] = raw_tool_calls
            messages.append(assistant_entry)

            if not parsed_tool_calls:
                break

            for tool_call in parsed_tool_calls:
                summary.tool_names.append(tool_call.name)

                if tool_call.name == "send_message_to_agent":
                    agent_name = tool_call.arguments.get("agent_name")
                    if isinstance(agent_name, str) and agent_name:
                        summary.execution_agents.add(agent_name)

                result = self._execute_tool(tool_call)

                if result.user_message:
                    summary.user_messages.append(result.user_message)

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.identifier or tool_call.name,
                    "content": self._format_tool_result(tool_call, result),
                }
                messages.append(tool_message)
        else:
            raise RuntimeError("Reached tool iteration limit without final response")

        if not summary.user_messages and not summary.last_assistant_text:
            logger.warning("Interaction loop exited without assistant content")

        return summary

    def _should_emit_assistant_reply(self, reply: str) -> bool:
        """Return True if reply is non-empty and not a recent duplicate."""

        if not reply.strip():
            return False

        candidate = {"role": "assistant", "content": reply}
        if self.duplicate_detector.check_and_mark(candidate, role="assistant"):
            logger.warning(
                "Duplicate assistant reply detected",
                extra={"content_preview": reply[:160]},
            )
            return False

        return True

    # Load conversation history, preferring summarized version if available
    async def _load_conversation_transcript(self) -> str:
        if self.settings.summarization_enabled:
            rendered = self.working_memory_log.render_transcript()
            if rendered.strip():
                return rendered
        return await self.conversation_log.load_transcript()

    # Execute API call to OpenRouter with system prompt, messages, and tool schemas
    async def _make_llm_call(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Make an LLM call via OpenRouter."""

        logger.debug(
            "Interaction agent calling LLM",
            extra={"model": self.model, "tools": len(self.tool_schemas)},
        )
        return await request_chat_completion(
            model=self.model,
            messages=messages,
            system=system_prompt,
            api_key=self.api_key,
            tools=self.tool_schemas,
        )

    # Extract the assistant's message from the OpenRouter API response structure
    def _extract_assistant_message(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Return the assistant message from the raw response payload."""

        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("LLM response did not include an assistant message")
        return message

    # Convert raw LLM tool calls into structured ParsedToolCall objects with validation
    def _parse_tool_calls(self, raw_tool_calls: List[Dict[str, Any]]) -> List[ParsedToolCall]:
        """Normalize tool call payloads from the LLM."""
        from .tools import _KNOWN_TOOL_NAMES
        return parse_tool_calls(raw_tool_calls, _KNOWN_TOOL_NAMES)

    # Parse and validate tool arguments from various formats (dict, JSON string, etc.)
    def _parse_tool_arguments(
        self, raw_arguments: Any
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """Convert tool arguments into a dictionary, reporting errors."""
        return safe_json_load(raw_arguments)

    # Execute tool calls with error handling and logging, returning standardized results
    def _execute_tool(self, tool_call: ParsedToolCall) -> ToolResult:
        """Execute a tool call and convert low-level errors into structured results."""

        if "__invalid_arguments__" in tool_call.arguments:
            error = tool_call.arguments["__invalid_arguments__"]
            self._log_tool_invocation(tool_call, stage="rejected", detail={"error": error})
            return ToolResult(success=False, payload={"error": error})

        try:
            self._log_tool_invocation(tool_call, stage="start")
            result = handle_tool_call(tool_call.name, tool_call.arguments)
        except ToolExecutionError as exc:
            logger.error(
                "Tool execution failed",
                extra={"tool": tool_call.name, "error": str(exc)},
                exc_info=True,
            )
            self._log_tool_invocation(
                tool_call,
                stage="error",
                detail={"error": str(exc)},
            )
            return ToolResult(success=False, payload={"error": str(exc)})
        except OpenPokeError as exc:
            logger.error(
                "Tool raised domain error",
                extra={"tool": tool_call.name, "error": str(exc)},
                exc_info=True,
            )
            self._log_tool_invocation(
                tool_call,
                stage="error",
                detail={"error": str(exc)},
            )
            return ToolResult(success=False, payload={"error": str(exc)})

        if not isinstance(result, ToolResult):
            logger.warning(
                "Tool did not return ToolResult; coercing",
                extra={"tool": tool_call.name},
            )
            wrapped = ToolResult(success=True, payload=result)
            self._log_tool_invocation(tool_call, stage="done", result=wrapped)
            return wrapped

        status = "success" if result.success else "error"
        logger.debug(
            "Tool executed",
            extra={
                "tool": tool_call.name,
                "status": status,
            },
        )
        self._log_tool_invocation(tool_call, stage="done", result=result)
        return result

    # Format tool execution results into JSON for LLM consumption
    def _format_tool_result(self, tool_call: ParsedToolCall, result: ToolResult) -> str:
        """Render a tool execution result back to the LLM."""
        return format_tool_result(
            tool_call.name,
            result.success,
            result.payload,
            tool_call.arguments,
        )

    # Log tool execution stages (start, done, error) with structured metadata
    def _log_tool_invocation(
        self,
        tool_call: ParsedToolCall,
        *,
        stage: str,
        result: Optional[ToolResult] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit structured logs for tool lifecycle events."""

        cleaned_args = {
            key: value
            for key, value in tool_call.arguments.items()
            if key != "__invalid_arguments__"
        }

        log_payload: Dict[str, Any] = {
            "tool": tool_call.name,
            "stage": stage,
            "arguments": cleaned_args,
        }

        if result is not None:
            log_payload["success"] = result.success
            if result.payload is not None:
                log_payload["payload"] = result.payload

        if detail:
            log_payload.update(detail)

        if stage == "done":
            logger.info(f"Tool '{tool_call.name}' completed")
        elif stage in {"error", "rejected"}:
            logger.warning(f"Tool '{tool_call.name}' {stage}")
        else:
            logger.debug(f"Tool '{tool_call.name}' {stage}")

    # Determine final user-facing response from interaction loop summary
    def _finalize_response(self, summary: _LoopSummary) -> str:
        """Decide what text should be exposed to the user as the final reply."""

        if summary.user_messages:
            return summary.user_messages[-1]

        return summary.last_assistant_text

