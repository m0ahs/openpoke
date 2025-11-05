#!/usr/bin/env node

/**
 * iMessage Watcher for Alyn
 *
 * Monitors incoming iMessage messages and forwards them to the Python backend
 * for processing by the Alyn interaction agent.
 */

import { IMessageSDK } from '@photon-ai/imessage-kit';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const POLL_INTERVAL = 2000; // Check for new messages every 2 seconds
const PYTHON_BRIDGE_PATH = join(__dirname, 'imessage_bridge.py');
const VENV_PYTHON = join(__dirname, '../../../.venv/bin/python');

class AlynIMessageWatcher {
  constructor() {
    this.sdk = new IMessageSDK({
      debug: true,
      concurrency: 5,
      timeout: 30000
    });

    this.processedMessageIds = new Set();
    this.lastCheckTime = Date.now();

    console.log('🚀 Alyn iMessage Watcher initialized');
  }

  /**
   * Forward message to Python backend via the bridge
   */
  async forwardToPython(message) {
    return new Promise((resolve, reject) => {
      const pythonProcess = spawn(VENV_PYTHON, [
        PYTHON_BRIDGE_PATH,
        '--sender', message.sender,
        '--text', message.text,
        '--timestamp', message.date.toISOString()
      ]);

      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          console.log(`✅ Message processed: ${stdout.trim()}`);
          resolve(stdout);
        } else {
          console.error(`❌ Python bridge error: ${stderr}`);
          reject(new Error(stderr));
        }
      });

      pythonProcess.on('error', (err) => {
        console.error(`❌ Failed to spawn Python process: ${err.message}`);
        reject(err);
      });
    });
  }

  /**
   * Process a new iMessage
   */
  async processMessage(message) {
    // Skip if already processed
    if (this.processedMessageIds.has(message.id)) {
      return;
    }

    // Skip messages from self
    if (message.is_from_me) {
      this.processedMessageIds.add(message.id);
      return;
    }

    // Skip messages older than last check
    if (message.date < new Date(this.lastCheckTime)) {
      this.processedMessageIds.add(message.id);
      return;
    }

    console.log(`\n📨 New message from ${message.sender}:`);
    console.log(`   "${message.text}"`);

    try {
      await this.forwardToPython({
        sender: message.sender,
        text: message.text,
        date: message.date,
        chatId: message.chat_id
      });

      this.processedMessageIds.add(message.id);

      // Cleanup old message IDs to prevent memory leak
      if (this.processedMessageIds.size > 1000) {
        const idsArray = Array.from(this.processedMessageIds);
        this.processedMessageIds = new Set(idsArray.slice(-500));
      }
    } catch (error) {
      console.error(`❌ Error processing message: ${error.message}`);
    }
  }

  /**
   * Start watching for new messages
   */
  async start() {
    console.log(`\n👀 Watching for iMessages (polling every ${POLL_INTERVAL}ms)...`);
    console.log('📱 Send a message to this Mac via iMessage to test\n');

    // Start polling loop
    setInterval(async () => {
      try {
        // Get recent messages (last 5 minutes)
        const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

        const result = await this.sdk.getMessages({
          limit: 50,
          after: fiveMinutesAgo
        });

        // Process new messages
        const messages = result.messages || result || [];
        for (const message of messages) {
          await this.processMessage(message);
        }

        // Update last check time
        this.lastCheckTime = Date.now();
      } catch (error) {
        console.error(`❌ Error checking messages: ${error.message}`);
      }
    }, POLL_INTERVAL);
  }

  /**
   * Send a message via iMessage
   */
  async sendMessage(recipient, text) {
    try {
      await this.sdk.send(recipient, text);
      console.log(`✉️  Sent to ${recipient}: "${text}"`);
      return true;
    } catch (error) {
      console.error(`❌ Failed to send message: ${error.message}`);
      return false;
    }
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n👋 Shutting down Alyn iMessage Watcher...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n\n👋 Shutting down Alyn iMessage Watcher...');
  process.exit(0);
});

// Start the watcher
const watcher = new AlynIMessageWatcher();
watcher.start().catch(error => {
  console.error(`❌ Fatal error: ${error.message}`);
  process.exit(1);
});

// Export for use as module
export default AlynIMessageWatcher;
