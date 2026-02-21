#!/usr/bin/env node
/**
 * Jitsi Meeting Assistant – Bot runner
 *
 * Launches a headless browser that loads the capture page. The capture page
 * joins your self-hosted Jitsi meeting and streams per-participant audio to
 * the backend WebSocket for transcription (output: "Speaker name : text").
 *
 * Usage:
 *   node runner.js [options]
 *
 * Options (env or CLI):
 *   JITSI_DOMAIN   (default: meet.jit.si) – your self-hosted Jitsi domain, e.g. meet.yourdomain.com
 *   ROOM_NAME     (default: MeetingMonitor) – Jitsi room name
 *   BOT_NAME      (default: Meeting Assistant) – display name of the bot in the meeting
 *   BACKEND_URL   (default: http://localhost:8000) – backend base URL (capture page and WS)
 *
 * Example:
 *   JITSI_DOMAIN=meet.mycompany.com ROOM_NAME=DailyStandup node runner.js
 */

const { chromium } = require('playwright');

const JITSI_DOMAIN = process.env.JITSI_DOMAIN || 'meet.jit.si';
const ROOM_NAME = process.env.ROOM_NAME || 'MeetingMonitor';
const BOT_NAME = process.env.BOT_NAME || 'Meeting Assistant';
const BACKEND_URL = (process.env.BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '');
const MEETING_ID = process.env.MEETING_ID || '';

const capturePath = '/static/jitsi-bot/capture.html';
const wsUrl = BACKEND_URL.replace(/^http/, 'ws') + '/api/v1/ws/jitsi-live';
let captureUrl =
  BACKEND_URL +
  capturePath +
  '?jitsi_domain=' +
  encodeURIComponent(JITSI_DOMAIN) +
  '&room=' +
  encodeURIComponent(ROOM_NAME) +
  '&bot_name=' +
  encodeURIComponent(BOT_NAME) +
  '&ws_url=' +
  encodeURIComponent(wsUrl);
if (MEETING_ID) captureUrl += '&meeting_id=' + encodeURIComponent(MEETING_ID);

async function main() {
  console.log('Starting Jitsi Meeting Assistant bot...');
  console.log('  Jitsi domain:', JITSI_DOMAIN);
  console.log('  Room:', ROOM_NAME);
  console.log('  Bot name:', BOT_NAME);
  console.log('  Capture URL:', captureUrl);
  console.log('');

  const browser = await chromium.launch({
    headless: process.env.HEADLESS !== '0',
    args: ['--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'],
  });

  const context = await browser.newContext({
    permissions: ['microphone'],
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  page.on('console', (msg) => {
    const text = msg.text();
    if (text) console.log('[Browser]', text);
  });

  await page.goto(captureUrl, { waitUntil: 'networkidle', timeout: 30000 }).catch((e) => {
    console.error('Failed to open capture page. Is the backend running at', BACKEND_URL, '?', e.message);
    process.exit(1);
  });

  console.log('Bot page loaded. Join the same Jitsi room from another device to see transcriptions.');
  console.log('Press Ctrl+C to stop.\n');

  await new Promise(() => {}); // run until process exit
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
