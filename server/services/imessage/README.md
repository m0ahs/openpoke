# iMessage Integration for Alyn

This module enables Alyn to communicate via iMessage on macOS using the `@photon-ai/imessage-kit` SDK.

## Architecture

```
┌─────────────┐
│   iMessage  │  (User sends message)
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ imessage_watcher.js  │  (Node.js - monitors incoming messages)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ imessage_bridge.py   │  (Python - forwards to Alyn backend)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────────────┐
│ InteractionAgentRuntime      │  (Processes message with LLM)
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────┐
│ send_message_to_user │  (Tool detects iMessage context)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ imessage_sender.py   │  (Python → Node.js bridge)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ send_message.js      │  (Node.js - sends via iMessage)
└──────┬───────────────┘
       │
       ▼
┌─────────────┐
│   iMessage  │  (User receives response)
└─────────────┘
```

## Components

### 1. `imessage_watcher.js`
- Polls for new iMessage messages every 2 seconds
- Filters out already-processed messages and self-sent messages
- Spawns Python bridge to process each new message
- Can also send messages directly

### 2. `imessage_bridge.py`
- CLI script that receives message data (sender, text, timestamp)
- Sets message context for the async processing chain
- Forwards message to InteractionAgentRuntime
- Logs processing results

### 3. `message_context.py`
- Thread-local context variable to track message source
- Allows tools to determine if response should go via iMessage
- Stores sender information for reply routing

### 4. `imessage_sender.py`
- Python interface to send iMessages
- Spawns Node.js subprocess to execute send_message.js
- Async-compatible with proper error handling

### 5. `send_message.js`
- Simple Node.js script to send a single iMessage
- Called by imessage_sender.py as subprocess

## Setup

### 1. System Requirements
- macOS with iMessage configured
- Node.js installed
- Full Disk Access granted to your IDE/terminal

### 2. Grant Full Disk Access
1. Open **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Add your IDE (e.g., Cursor, VSCode) or Terminal app
3. Restart your IDE/Terminal after granting access

### 3. Install Dependencies
```bash
npm install
```

This installs:
- `@photon-ai/imessage-kit` - iMessage SDK
- `better-sqlite3` - SQLite adapter for Node.js

### 4. Test the Watcher
```bash
npm run watch
```

Send yourself an iMessage and verify it's detected.

## Usage

### Starting the iMessage Service

```bash
# Start the watcher (monitors incoming messages)
npm run watch
```

Or run directly:
```bash
node server/services/imessage/imessage_watcher.js
```

### Sending Messages Programmatically

From Python:
```python
from server.services.imessage import send_imessage

# Send a message
await send_imessage("+1234567890", "Hello from Alyn!")
```

From Node.js:
```bash
node server/services/imessage/send_message.js "+1234567890" "Hello!"
```

## How It Works

1. **Incoming Message Flow:**
   - User sends iMessage to your Mac
   - `imessage_watcher.js` detects new message via polling
   - Watcher spawns `imessage_bridge.py` with message data
   - Bridge sets `MessageContext(source="imessage", sender=...)`
   - Bridge calls `InteractionAgentRuntime.execute(user_message)`
   - Interaction agent processes message (LLM, tools, etc.)

2. **Outgoing Response Flow:**
   - Interaction agent calls `send_message_to_user(message)`
   - Tool checks `get_message_context()`
   - If context.source == "imessage", tool calls `send_imessage()`
   - `imessage_sender.py` spawns `send_message.js`
   - Node.js script sends message via iMessage SDK
   - User receives response in iMessage

## Message Context

The `MessageContext` is a context variable that tracks:
- **source**: "imessage" or "http"
- **sender**: Phone number or email (for iMessage)
- **timestamp**: ISO timestamp of original message

This context is automatically set by `imessage_bridge.py` and consumed by `send_message_to_user` to route responses correctly.

## Debugging

### Enable Debug Logging

In `imessage_watcher.js`:
```javascript
const sdk = new iMessageSDK({
  debug: true,  // Enable verbose logging
  // ...
});
```

### Check Processed Messages
The watcher maintains a set of processed message IDs to avoid duplicates. If messages aren't being processed:
1. Check the watcher console output
2. Verify Full Disk Access is granted
3. Ensure iMessage is configured on your Mac

### Test Message Sending
```bash
# Test sending directly
node server/services/imessage/send_message.js "your-number" "test message"
```

## Integration with Alyn

The iMessage integration is designed to work seamlessly with existing Alyn features:

- **Email tools**: Work normally, responses go to iMessage when appropriate
- **Calendar tools**: User receives calendar updates via iMessage
- **Execution agents**: All background tasks work the same
- **Conversation log**: All messages are logged normally
- **Dual mode**: HTTP and iMessage can both be active simultaneously

## Limitations

- **macOS only**: Requires macOS with iMessage
- **Polling-based**: Not real-time (2-second poll interval)
- **No attachments yet**: Currently text-only (can be extended)
- **Single Mac**: Watcher must run on the Mac receiving messages

## Future Enhancements

- [ ] Support for sending images/attachments
- [ ] Webhook-based notifications instead of polling
- [ ] Multi-user support (different phone numbers)
- [ ] Read receipts and typing indicators
- [ ] Group chat support
- [ ] Message reactions

## Troubleshooting

### "Permission denied" errors
→ Grant Full Disk Access to your IDE/Terminal

### Messages not being detected
→ Check that iMessage is working normally on your Mac
→ Verify the watcher is running (`npm run watch`)

### Responses not being sent
→ Check logs for errors from `imessage_sender.py`
→ Test sending manually with `send_message.js`

### Duplicate messages
→ The watcher tracks processed message IDs
→ Restart the watcher to reset the cache if needed
