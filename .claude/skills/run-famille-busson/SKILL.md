---
name: run-famille-busson
description: Build, run, and drive the famille-busson Django app — start the dev server, log in as a seeded user, click through pages, and take screenshots. Use when asked to start the app, run it, take a screenshot of a page, or verify a UI change actually renders.
---

famille-busson is a server-rendered Django app (Bootstrap 5, no JS framework,
no separate frontend build). There's no `chromium-cli` in this environment, so
it's driven directly via the Playwright REPL at
`.claude/skills/run-famille-busson/driver.mjs` — same shape (pipe a script to
stdin, `nav`/`click`/`screenshot`), just hand-rolled.

All paths below are relative to the repo root.

## Prerequisites

- `uv` (Python/Django side — already required by the project, see `dev-commands`).
- Node.js + npm (driver only — not a runtime dependency of the Django app itself).

Install the driver's dependency once:

```bash
cd .claude/skills/run-famille-busson && npm install
npx playwright install chromium   # only needed once per machine; skipped if already cached
cd -
```

## Build / Setup

```bash
uv sync
uv run python manage.py migrate
```

If `db.sqlite3` doesn't exist yet or has no data, seed it (see `dev-commands`):

```bash
uv run python manage.py populate_dev_data
```

## Run (agent path)

Start the dev server in the background and wait for it to be ready:

```bash
nohup uv run python manage.py runserver 127.0.0.1:8000 --noreload > /tmp/famille-busson-server.log 2>&1 &
timeout 30 bash -c 'until curl -sf http://127.0.0.1:8000/healthz > /dev/null; do sleep 1; done'
```

Drive it by piping a script to the REPL's stdin (no tmux available in this
environment — a single heredoc call is the primary pattern here, same as a
`chromium-cli` session):

```bash
node .claude/skills/run-famille-busson/driver.mjs <<'EOF'
launch
login admin@example.com admin
ss 01-landing
goto /annuaire/
ss 02-annuaire
console --errors
quit
EOF
```

Screenshots land in `.shots/` at the repo root (override with `SCREENSHOT_DIR`).
Login credentials (from `populate_dev_data`, see `dev-commands`):
- Superuser: `admin@example.com` / `admin` — **redirects to `/annuaire/profile/create/`**, it has no `Person` profile (see Gotchas).
- Regular user: `paul.bernard.0@example.com` / `dev` (any of the 20 seeded accounts, password `dev`) — goes straight to the `/annuaire/` dashboard.

For iterative debugging, run the driver as a long-lived process (`node driver.mjs`,
no heredoc) and pipe individual commands to its stdin one at a time instead of
closing it after one batch.

### Commands

| command | what it does |
|---|---|
| `launch` | launch headless Chromium |
| `goto <path-or-url>` | navigate (bare paths resolve against `http://127.0.0.1:8000`) |
| `ss [name]` | full-page screenshot → `.shots/<name>.png` |
| `click <css-sel>` | click element |
| `click-text <text>` | click the first element containing this text |
| `fill <css-sel> <text>` | fill an input |
| `type <text>` / `press <key>` | keyboard input |
| `wait <css-sel>` | wait for element, 10s timeout |
| `eval <js>` | evaluate in the page, print JSON |
| `text [css-sel]` | print innerText (whole page if no selector) |
| `login [email] [password]` | fill + submit `/annuaire/login/` (defaults to the admin creds) |
| `console [--errors]` | print buffered browser console output |
| `quit` | close the browser, exit |

Stop the server (Windows/Git Bash — no `lsof` here, `netstat` + `taskkill`
stand in for it; on Linux/macOS use `lsof -ti:8000 -sTCP:LISTEN | xargs -r kill`):

```bash
netstat -ano | grep ':8000.*LISTENING'   # note the PID in the last column
taskkill //PID <pid> //F
```

## Run (human path)

```bash
uv run python manage.py runserver
```
Opens on `http://127.0.0.1:8000/`. Ctrl-C to stop.

## Test

```bash
uv run --group test pytest
```
Full suite is slow (~25 min per CLAUDE.md — a known, tracked anomaly, not
expected). Use the `/test-select` skill to scope to changed files instead of
running the whole suite.

## Gotchas

- **`uv sync` (no `--group test`) uninstalls pytest and friends** if they
  were already installed — it syncs to exactly the default group. Running
  the Build section right before `/test-select` or `pytest` will make the
  test run fail on import errors; re-run `uv sync --group test` first.
- **The seeded superuser has no `Person` profile.** Logging in as
  `admin@example.com` redirects straight to `/annuaire/profile/create/`
  instead of the dashboard — `annuaire`'s post-save signal only auto-links a
  `Person` to an `Account` when a `Person` with a matching email already
  exists (see CLAUDE.md §5), and the fixture doesn't create one for the
  superuser. Use a regular seeded account (`paul.bernard.0@example.com` /
  `dev`) when you need to see the actual dashboard.
- **The driver must serialize commands.** `readline` fires `line` events for
  every buffered line synchronously (a whole heredoc lands in one batch)
  without waiting for the previous async command handler to finish — without
  the promise-chain queue in `driver.mjs`, `goto`/`ss`/`login` piped right
  after `launch` all race against a still-null `page`. If you extend the
  driver, keep adding new commands to `COMMANDS` (the queue already covers
  them) rather than bypassing the queue.
- **No `tmux` on this machine.** The generic advice to wrap REPL drivers in
  tmux for iterative use doesn't apply here — piping one heredoc per batch of
  commands is the working pattern; for genuinely interactive iteration, run
  `node driver.mjs` as a long-lived foreground/background process and write
  to its stdin directly.

## Troubleshooting

- **`curl: (7) Failed to connect` after starting the server:** the health
  poll loop just needs more time on first boot (SQLite + migrations) — it
  isn't a fixed `sleep`, so re-check `/tmp/famille-busson-server.log` for the
  actual error before assuming it's a timing issue.
- **Port 8000 already in use:** a previous run's server is still up — find
  and kill it with the `netstat`/`taskkill` sequence above before relaunching.
- **`ERROR: launch first` on every command:** the driver wasn't given time to
  serialize — confirms you're running an old copy of `driver.mjs` without the
  promise-chain queue (see Gotchas); pull the current version.
