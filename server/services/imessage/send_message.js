#!/usr/bin/env node

/**
 * Simple script to send an iMessage
 * Usage: node send_message.js <recipient> <message>
 */

import { IMessageSDK } from '@photon-ai/imessage-kit';

const [recipient, message] = process.argv.slice(2);

if (!recipient || !message) {
  console.error('Usage: node send_message.js <recipient> <message>');
  process.exit(1);
}

const sdk = new IMessageSDK({
  debug: false,
  timeout: 10000
});

try {
  await sdk.send(recipient, message);
  console.log(`✉️  Message sent to ${recipient}`);
  process.exit(0);
} catch (error) {
  console.error(`❌ Failed to send message: ${error.message}`);
  process.exit(1);
}
