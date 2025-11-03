"""Background scheduler that watches trigger definitions and executes them."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

from ..agents.execution_agent.batch_manager import ExecutionBatchManager
from ..agents.execution_agent.runtime import ExecutionResult
from ..logging_config import logger
from .triggers import TriggerRecord, get_trigger_service
from .triggers.utils import parse_iso


UTC = timezone.utc


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class TriggerScheduler:
    """Polls stored triggers and launches execution agents when due."""

    def __init__(self, poll_interval_seconds: float = 10.0) -> None:
        self._poll_interval = poll_interval_seconds
        self._service = get_trigger_service()
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._in_flight: Set[int] = set()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                return
            loop = asyncio.get_running_loop()
            self._running = True
            self._task = loop.create_task(self._run(), name="trigger-scheduler")
            logger.info("Trigger scheduler started", extra={"interval": self._poll_interval})

    async def stop(self) -> None:
        async with self._lock:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None
                logger.info("Trigger scheduler stopped")

    async def _run(self) -> None:
        logger.info("Trigger scheduler loop starting")
        try:
            while self._running:
                logger.info("Trigger scheduler polling cycle")
                await self._poll_once()
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Trigger scheduler loop crashed", extra={"error": str(exc)})

    async def _poll_once(self) -> None:
        logger.info("Starting trigger poll")
        now = _utc_now()
        # Look for triggers due in the next 30 seconds to account for polling interval
        look_ahead = now + timedelta(seconds=30)
        due_triggers = self._service.get_due_triggers(before=look_ahead)

        # Debug: Log all triggers for the Rappels personnels agent
        all_triggers = []
        try:
            all_triggers = self._service.list_triggers(agent_name="Rappels personnels")
        except Exception as e:
            logger.warning(f"Could not list triggers: {e}")

        logger.info(
            f"Found {len(due_triggers)} due triggers, {len(all_triggers)} total triggers for Rappels personnels",
            extra={
                "now": _isoformat(now),
                "look_ahead": _isoformat(look_ahead),
                "due_count": len(due_triggers),
                "total_count": len(all_triggers),
                "trigger_details": [
                    {
                        "id": t.id,
                        "next_trigger": t.next_trigger,
                        "status": t.status,
                        "payload": t.payload[:50] + "..." if len(t.payload) > 50 else t.payload
                    } for t in all_triggers
                ]
            },
        )

        if not due_triggers:
            return

        for trigger in due_triggers:
            if trigger.id in self._in_flight:
                logger.info(
                    "Trigger already in flight",
                    extra={"trigger_id": trigger.id, "agent": trigger.agent_name}
                )
                continue

            # Only execute if actually due (within 5 seconds of now)
            next_fire = parse_iso(trigger.next_trigger) if trigger.next_trigger else None
            if next_fire and (next_fire - now) > timedelta(seconds=5):
                logger.info(
                    "Trigger not yet due",
                    extra={
                        "trigger_id": trigger.id,
                        "next_fire": trigger.next_trigger,
                        "seconds_until_due": (next_fire - now).total_seconds()
                    }
                )
                continue

            self._in_flight.add(trigger.id)
            asyncio.create_task(self._execute_trigger(trigger), name=f"trigger-{trigger.id}")

    async def _execute_trigger(self, trigger: TriggerRecord) -> None:
        try:
            fired_at = _utc_now()
            instructions = self._format_instructions(trigger, fired_at)

            logger.info(
                "Dispatching trigger",
                extra={
                    "trigger_id": trigger.id,
                    "agent": trigger.agent_name,
                    "scheduled_for": trigger.next_trigger,
                    "fired_at": _isoformat(fired_at),
                    "payload_preview": trigger.payload[:100] + "..." if len(trigger.payload) > 100 else trigger.payload
                },
            )

            execution_manager = ExecutionBatchManager()
            result = await execution_manager.execute_agent(
                trigger.agent_name,
                instructions,
            )

            if result.success:
                logger.info(
                    "Trigger completed successfully",
                    extra={
                        "trigger_id": trigger.id,
                        "agent": trigger.agent_name,
                        "response_length": len(result.response) if result.response else 0
                    }
                )
                self._handle_success(trigger, fired_at)
            else:
                error_text = result.error or result.response or "Unknown error"
                logger.warning(
                    "Trigger execution failed",
                    extra={
                        "trigger_id": trigger.id,
                        "agent": trigger.agent_name,
                        "error": error_text[:200] + "..." if len(error_text) > 200 else error_text
                    },
                )
                self._handle_failure(trigger, fired_at, error_text)
        except Exception as exc:
            error_msg = f"Unexpected error during trigger execution: {str(exc)}"
            logger.exception(
                "Trigger execution failed unexpectedly",
                extra={"trigger_id": trigger.id, "agent": trigger.agent_name, "error": error_msg},
            )
            self._handle_failure(trigger, _utc_now(), error_msg)
        finally:
            self._in_flight.discard(trigger.id)

    def _handle_success(self, trigger: TriggerRecord, fired_at: datetime) -> None:
        logger.info(
            "Trigger completed",
            extra={"trigger_id": trigger.id, "agent": trigger.agent_name},
        )
        self._service.schedule_next_occurrence(trigger, fired_at=fired_at)

    def _handle_failure(self, trigger: TriggerRecord, fired_at: datetime, error: str) -> None:
        logger.warning(
            "Trigger execution failed",
            extra={
                "trigger_id": trigger.id,
                "agent": trigger.agent_name,
                "error": error,
            },
        )
        self._service.record_failure(trigger, error)
        if trigger.recurrence_rule:
            self._service.schedule_next_occurrence(trigger, fired_at=fired_at)
        else:
            self._service.clear_next_fire(trigger.id, agent_name=trigger.agent_name)

    def _format_instructions(self, trigger: TriggerRecord, fired_at: datetime) -> str:
        scheduled_for = trigger.next_trigger or _isoformat(fired_at)
        metadata_lines = [f"Trigger ID: {trigger.id}"]
        if trigger.recurrence_rule:
            metadata_lines.append(f"Recurrence: {trigger.recurrence_rule}")
        if trigger.timezone:
            metadata_lines.append(f"Timezone: {trigger.timezone}")
        if trigger.start_time:
            metadata_lines.append(f"Start Time (UTC): {trigger.start_time}")

        metadata = "\n".join(f"- {line}" for line in metadata_lines)
        return (
            f"Trigger fired at {_isoformat(fired_at)} (UTC).\n"
            f"Scheduled occurrence time: {scheduled_for}.\n\n"
            f"Metadata:\n{metadata}\n\n"
            f"Payload:\n{trigger.payload}"
        )


_scheduler_instance: Optional[TriggerScheduler] = None


def get_trigger_scheduler() -> TriggerScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TriggerScheduler()
    return _scheduler_instance


__all__ = ["TriggerScheduler", "get_trigger_scheduler"]
