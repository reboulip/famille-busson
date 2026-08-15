// REPL driver for famille-busson (Django + Bootstrap 5, server-rendered pages).
// No chromium-cli available in this environment, so this drives a real headless
// Chromium directly via Playwright. Run under tmux, send-keys one command at a
// time, capture-pane for output — same shape as chromium-cli.
import { chromium } from 'playwright';
import * as readline from 'node:readline';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE_URL = process.env.APP_URL || 'http://127.0.0.1:8000';
const SHOT_DIR = process.env.SCREENSHOT_DIR || path.resolve(process.cwd(), '.shots');
fs.mkdirSync(SHOT_DIR, { recursive: true });

let browser = null;
let page = null;
const consoleLog = [];

const COMMANDS = {
  async launch() {
    if (browser) return console.log('already launched');
    browser = await chromium.launch({ args: ['--no-sandbox'] });
    page = await (await browser.newContext()).newPage();
    page.on('console', (msg) => consoleLog.push({ type: msg.type(), text: msg.text() }));
    page.on('pageerror', (err) => consoleLog.push({ type: 'pageerror', text: String(err) }));
    console.log('launched.');
  },

  async goto(pathOrUrl) {
    if (!page) return console.log('ERROR: launch first');
    const url = /^https?:\/\//.test(pathOrUrl) ? pathOrUrl : BASE_URL + pathOrUrl;
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded' });
    console.log('goto', url, '→', resp?.status());
  },

  async ss(name) {
    if (!page) return console.log('ERROR: launch first');
    const f = path.join(SHOT_DIR, (name || `ss-${Date.now()}`) + '.png');
    await page.screenshot({ path: f, fullPage: true });
    console.log('screenshot:', f);
  },

  async click(sel) {
    if (!page) return console.log('ERROR: launch first');
    try { await page.click(sel, { timeout: 5000 }); console.log('click', sel, '→ OK'); }
    catch (e) { console.log('click', sel, '→ ERROR:', e.message.split('\n')[0]); }
  },

  async 'click-text'(text) {
    if (!page) return console.log('ERROR: launch first');
    try { await page.getByText(text, { exact: false }).first().click({ timeout: 5000 }); console.log('click-text', JSON.stringify(text), '→ OK'); }
    catch (e) { console.log('click-text', JSON.stringify(text), '→ ERROR:', e.message.split('\n')[0]); }
  },

  async fill(args) {
    if (!page) return console.log('ERROR: launch first');
    const [sel, ...rest] = args.split(' ');
    const value = rest.join(' ');
    try { await page.fill(sel, value, { timeout: 5000 }); console.log('fill', sel, '→ OK'); }
    catch (e) { console.log('fill', sel, '→ ERROR:', e.message.split('\n')[0]); }
  },

  async type(text) { if (page) await page.keyboard.type(text, { delay: 20 }); },
  async press(key) { if (page) await page.keyboard.press(key); },

  async wait(sel) {
    if (!page) return console.log('ERROR: launch first');
    try { await page.waitForSelector(sel, { timeout: 10_000 }); console.log('found:', sel); }
    catch { console.log('TIMEOUT:', sel); }
  },

  async eval(expr) {
    if (!page) return console.log('ERROR: launch first');
    try { console.log(JSON.stringify(await page.evaluate(expr))); }
    catch (e) { console.log('ERROR:', e.message); }
  },

  async text(sel) {
    if (!page) return console.log('ERROR: launch first');
    console.log(await page.evaluate(
      (s) => (s ? document.querySelector(s) : document.body)?.innerText ?? '(null)',
      sel || null,
    ));
  },

  // Convenience: log in through the real form at /annuaire/login/ instead of
  // hand-writing the click/fill sequence every time. Credentials per the
  // dev-commands skill's populate_dev_data fixtures.
  async login(args) {
    if (!page) return console.log('ERROR: launch first');
    const [email, password] = (args || 'admin@example.com admin').split(' ');
    await page.goto(BASE_URL + '/annuaire/login/', { waitUntil: 'domcontentloaded' });
    await page.fill('input[name="username"]', email);
    await page.fill('input[name="password"]', password);
    await Promise.all([
      page.waitForLoadState('domcontentloaded'),
      page.click('button[type="submit"]'),
    ]);
    console.log('login', email, '→ now at', page.url());
  },

  console(filter) {
    const rows = filter === '--errors'
      ? consoleLog.filter((m) => m.type === 'error' || m.type === 'pageerror')
      : consoleLog;
    if (!rows.length) return console.log('(no console output)');
    for (const m of rows) console.log(`[${m.type}]`, m.text);
  },

  async quit() { if (browser) await browser.close().catch(() => {}); browser = null; page = null; },
  help() { console.log('commands:', Object.keys(COMMANDS).join(', ')); },
};

const rl = readline.createInterface({ input: process.stdin, output: process.stdout, prompt: 'driver> ' });

// readline emits 'line' synchronously for every buffered line (e.g. a whole heredoc)
// without waiting for an async listener to finish — without this queue, "launch"
// (async, ~1s) and the commands piped right after it would all fire concurrently
// against a still-null `page`. Chaining onto one promise serializes them.
let queue = Promise.resolve();

rl.on('line', (line) => {
  queue = queue.then(async () => {
    const [cmd, ...rest] = line.trim().split(/\s+/);
    if (!cmd) return;
    const fn = COMMANDS[cmd];
    if (!fn) { console.log('unknown:', cmd, '— try: help'); return; }
    try { await fn(rest.join(' ')); } catch (e) { console.log('ERROR:', e.message); }
    if (!rl.closed) rl.prompt();
    if (cmd === 'quit') process.exit(0);
  }).catch((e) => console.log('QUEUE ERROR:', e.message));
});
rl.on('close', () => { queue = queue.then(async () => { await COMMANDS.quit(); process.exit(0); }); });

console.log('famille-busson driver — "help" for commands, "launch" to start');
rl.prompt();
