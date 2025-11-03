#!/usr/bin/env python3
"""Test script for trigger system functionality."""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add the server directory to the path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from services.triggers import get_trigger_service
from services.trigger_scheduler import get_trigger_scheduler
from services.execution.log_store import ExecutionAgentLogStore
from logging_config import configure_logging

configure_logging()

async def test_trigger_system():
    """Test the trigger system with a simple 10-second delay trigger."""

    print("🚀 Starting trigger system test...")

    # Get services
    trigger_service = get_trigger_service()
    scheduler = get_trigger_scheduler()

    # Start the scheduler
    await scheduler.start()
    print("✅ Trigger scheduler started")

    # Create a test trigger that should fire in 10 seconds
    test_payload = "Test trigger execution - this should run automatically"
    fire_time = datetime.utcnow() + timedelta(seconds=10)

    print(f"📅 Creating test trigger to fire at {fire_time.isoformat()}")

    trigger = trigger_service.create_trigger(
        agent_name="test-agent",
        payload=test_payload,
        start_time=fire_time.isoformat(),
        status="active"
    )

    print(f"✅ Created trigger ID: {trigger.id}")
    print(f"   Next fire time: {trigger.next_trigger}")
    print(f"   Status: {trigger.status}")

    # Wait for the trigger to execute
    print("⏳ Waiting 15 seconds for trigger execution...")
    await asyncio.sleep(15)

    # Check if trigger was executed by looking at logs
    log_store = ExecutionAgentLogStore(Path("server/data/execution_agents"))
    recent_logs = log_store.load_recent("test-agent", limit=20)

    trigger_executed = False
    for timestamp, tag, description in recent_logs:
        if test_payload in description:
            print(f"✅ Trigger executed! Log entry: {description}")
            trigger_executed = True
            break

    if not trigger_executed:
        print("❌ Trigger was not executed")
        # List all triggers to see current state
        triggers = trigger_service.list_triggers(agent_name="test-agent")
        print(f"📋 Current triggers for test-agent: {len(triggers)}")
        for t in triggers:
            print(f"   ID: {t.id}, Next: {t.next_trigger}, Status: {t.status}, Error: {t.last_error}")

    # Clean up
    await scheduler.stop()
    print("🛑 Trigger scheduler stopped")

    return trigger_executed

if __name__ == "__main__":
    result = asyncio.run(test_trigger_system())
    if result:
        print("🎉 Test PASSED: Trigger system works correctly")
    else:
        print("💥 Test FAILED: Trigger system has issues")
        sys.exit(1)