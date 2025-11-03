# Known Issues

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
