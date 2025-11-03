# Known Issues

## Google Calendar Integration - Tool Names Not Found (404)

**Status:** 🔴 Active Issue  
**Date Reported:** November 4, 2025  
**Severity:** Critical - Calendar tools cannot execute

### Problem Description

Calendar tool execution fails with 404 error:
```
composio_client.NotFoundError: Error code: 404
Tool GOOGLECALENDAR_LIST_EVENTS not found
```

The tool names we're using (`GOOGLECALENDAR_LIST_EVENTS`, `GOOGLECALENDAR_CREATE_EVENT`, etc.) don't match the actual tool names in Composio's GOOGLECALENDAR toolkit.

### Error Example

```
2025-11-03 23:52:36 - ERROR - Calendar tool execution failed: GOOGLECALENDAR_LIST_EVENTS
composio_client.NotFoundError: Tool GOOGLECALENDAR_LIST_EVENTS not found
```

### Root Cause

We assumed standard tool naming conventions, but Composio may use different names for Calendar tools. Need to discover the actual tool names available in the GOOGLECALENDAR toolkit.

### Solution

**Step 1: Discover Available Tools**

Run the discovery script:
```bash
cd /Users/josephmbaibisso/conductor/openpoke/.conductor/tokyo
python discover_calendar_tools.py
```

This will:
- Query Composio API for all GOOGLECALENDAR tools
- Print tool names and descriptions
- Save results to `composio_calendar_tools.txt`

**Step 2: Update Tool Mappings**

Once you have the correct tool names, update the mappings in:
`server/agents/execution_agent/tools/gcalendar.py`

Change the `composio_action` values:
```python
def _calendar_list_events(agent_name: str, **kwargs: Any) -> Dict[str, Any]:
    return _execute_calendar_action(
        agent_name=agent_name,
        tool_name="calendar_list_events",
        composio_action="ACTUAL_COMPOSIO_TOOL_NAME_HERE",  # Update this
        arguments=kwargs,
    )
```

### Alternative Solutions

**Option 1: Use Composio's Web UI**
1. Go to https://composio.dev/
2. Navigate to GOOGLECALENDAR toolkit
3. View "Tools & Trigger Types" tab
4. Copy exact tool names

**Option 2: Check Composio Documentation**
- Review https://docs.composio.dev/toolkits/google-calendar
- Look for official tool name conventions

### Files to Update

After discovering correct names:
- `server/agents/execution_agent/tools/gcalendar.py` - Update all `composio_action` values
- Test each tool individually

### Current Tool Mappings (INCORRECT)

```python
"calendar_create_event" → "GOOGLECALENDAR_CREATE_EVENT" ❌
"calendar_list_events" → "GOOGLECALENDAR_LIST_EVENTS" ❌
"calendar_update_event" → "GOOGLECALENDAR_UPDATE_EVENT" ❌
"calendar_delete_event" → "GOOGLECALENDAR_DELETE_EVENT" ❌
"calendar_find_free_time" → "GOOGLECALENDAR_FIND_FREE_TIME" ❌
```

---

## Google Calendar Integration - Configuration Required

**Status:** ⚙️ Configuration Issue  
**Date Reported:** November 4, 2025  
**Severity:** High - Blocks Calendar connection

### Problem Description

Calendar connection fails with "Failed to initiate Calendar connect" because `COMPOSIO_CALENDAR_AUTH_CONFIG_ID` environment variable is not set.

### Symptoms

Frontend shows:
```
Not connected
Failed to initiate Calendar connect
```

Backend logs show:
```
COMPOSIO_CALENDAR_AUTH_CONFIG_ID not configured
```

### Solution

**Required Setup:**

1. **Get Calendar Auth Config ID from Composio:**
   - Login to https://composio.dev/
   - Navigate to Integrations → Google Calendar
   - Create or copy your Calendar Auth Config ID

2. **Set Environment Variable:**

   Add to your `.env` file:
   ```bash
   COMPOSIO_CALENDAR_AUTH_CONFIG_ID=your_calendar_auth_config_id_here
   ```

   Or in Railway/production:
   ```bash
   railway variables set COMPOSIO_CALENDAR_AUTH_CONFIG_ID=your_id_here
   ```

3. **Restart the backend server:**
   ```bash
   # Development
   cd server && python app.py
   
   # Production (Railway auto-restarts)
   ```

### Verification

After configuration:
```bash
# Test connection endpoint
curl -X POST http://localhost:8001/api/v1/calendar/connect \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}'

# Should return redirect_url, not error
```

---

## Google Calendar Integration - Composio execute_action Bug

**Status:** 🔴 Active Issue  
**Date Reported:** November 4, 2025  
**Severity:** Medium - Connection works but metadata fetch fails

### Problem Description

Google Calendar OAuth connection via Composio succeeds, but the backend crashes when trying to execute `GOOGLECALENDAR_LIST_CALENDARS` to fetch calendar metadata (email, calendar list).

### Symptoms

- ✅ OAuth flow completes successfully
- ✅ Account shows as "ACTIVE" in Composio
- ❌ `execute_action` fails when calling any Calendar tool
- ❌ Email/calendar list cannot be retrieved
- Frontend shows: "Email unavailable" or "Connected (email unavailable - Composio execute_action bug)"

### Root Cause

This is a **backend configuration issue on Composio's side**, NOT a permissions problem. The account is properly connected, but the `execute_action` endpoint has a bug that prevents tool execution.

### Current Workaround

```python
# server/services/gcalendar/client.py
# Returns connection success even without email
return JSONResponse({
    "ok": True,
    "status": "active",
    "email": email or "Connected (email unavailable - Composio execute_action bug)",
    "warning": "Calendar connected but unable to fetch email due to Composio backend issue"
})
```

The system gracefully handles the error and still marks the calendar as connected.

### Error Logs

Check backend logs for:
```
Composio execute_action error when fetching calendar list
Tool: GOOGLECALENDAR_LIST_CALENDARS
composio_bug: execute_action failure - backend config issue
```

### Required Fix

**Dev Action Required:**
1. Check Composio backend configuration
2. Verify `COMPOSIO_CALENDAR_AUTH_CONFIG_ID` is correctly set
3. Review Composio API integration settings
4. Test `execute_action` endpoint directly
5. Contact Composio support if config is correct

### Files Affected

- `server/services/gcalendar/client.py` - Error handling and workaround
- `server/agents/execution_agent/tools/gcalendar.py` - Calendar tools (all affected)
- `web/components/SettingsModal.tsx` - Shows warning message

### Testing

```bash
# Test Calendar connection
curl -X POST http://localhost:8001/api/v1/calendar/status \
  -H "Content-Type: application/json" \
  -d '{"user_id": "your-user-id"}'

# Check logs for execute_action errors
tail -f logs/server.log | grep "execute_action"
```

### Related

- Initial implementation: Commit `c5f3e74`
- Email fetch attempt: Commit `a0290c3`
- Graceful error handling: Current commit

---

## Other Known Issues

_None at this time._
