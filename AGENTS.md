# Agent-assisted setup guide

This file is for Hermes Agent or another local coding agent. A user should be able to point an agent at this repository and say: "Set this up for me." Follow these steps and do not guess credentials.

## Goal

Install `whoop-local-sync` into the user's Hermes Agent Python environment, enable the bundled Hermes plugin, guide the user through WHOOP OAuth, run an initial local fetch/backfill, and verify that the plugin tools work.

## Safety rules

- Do not print, commit, upload, or summarize WHOOP client secrets, OAuth codes, refresh tokens, access tokens, SQLite databases, raw exports, `latest.json`, `backfill_index.json`, or `.env` files.
- Keep all WHOOP data local. Default Hermes data directory: `~/.hermes/whoop/`.
- Never commit files under `~/.hermes/whoop/`.
- If credentials are missing, ask the user for the WHOOP OAuth client ID and client secret, or ask them to add those values to `~/.hermes/.env`. Do not invent placeholders and proceed as if authenticated.
- If a command would overwrite an existing token, database, raw archive, or checkpoint, state exactly what file is affected before doing it.

## Prerequisites

The user needs a WHOOP Developer App.

Developer portal:

```text
https://developer.whoop.com/
```

Redirect / callback URL:

```text
http://127.0.0.1:8787/callback
```

Recommended scopes:

```text
offline
read:profile
read:body_measurement
read:cycles
read:recovery
read:sleep
read:workout
```

WHOOP webhooks are not required. This project is pull-based by default.

## Quick agent prompt

If the user pastes this file or points you at this repo, this is the intended task:

```text
Install whoop-local-sync into Hermes Agent's own Python environment, run the bundled plugin installer with --enable for cli/whatsapp/telegram unless I specify different platforms, configure WHOOP_* variables in ~/.hermes/.env without revealing secrets, generate the WHOOP auth URL, exchange the OAuth code I provide, run a recent fetch and bounded backfill, verify status/latest, and tell me what passed.
```

## 1. Locate Hermes and its Python environment

Prefer Hermes' own virtualenv when it exists:

```bash
if [ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]; then
  HERMES_PYTHON="$HOME/.hermes/hermes-agent/venv/bin/python"
else
  HERMES_PYTHON="$(command -v python3)"
fi
printf 'Using Python: %s\n' "$HERMES_PYTHON"
```

If the user has a custom Hermes profile or custom installation path, use the Python executable for that Hermes runtime.

## 2. Install this package into Hermes' Python environment

From GitHub:

```bash
"$HERMES_PYTHON" -m pip install "git+https://github.com/Wysie/whoop-local-sync.git"
```

From a local checkout:

```bash
"$HERMES_PYTHON" -m pip install -e /path/to/whoop-local-sync
```

Verify the CLI is importable:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli --help
```

## 3. Configure credentials in `~/.hermes/.env`

Required variables:

```bash
WHOOP_CLIENT_ID="..."
WHOOP_CLIENT_SECRET="..."
WHOOP_REDIRECT_URI="http://127.0.0.1:8787/callback"
```

Recommended freshness variables:

```bash
WHOOP_AUTO_REFRESH_ON_LATEST="true"
WHOOP_REFRESH_MAX_AGE_MINUTES="30"
WHOOP_REFRESH_DAYS="7"
```

Optional data directory override:

```bash
WHOOP_DATA_DIR="$HOME/.hermes/whoop"
```

Agent behaviour:

1. Check whether `~/.hermes/.env` exists.
2. If variables are missing, ask the user for the missing values or ask them to edit the file manually.
3. When writing values, append/update only the `WHOOP_*` lines.
4. Do not print the secret value after writing it.

## 4. Install and enable the bundled Hermes Agent plugin

Install into Hermes' plugin directory and enable the `whoop` toolset.

Default platforms match the common gateway setup:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli install-hermes-plugin \
  --enable \
  --platform cli \
  --platform whatsapp \
  --platform telegram
```

If the user only wants CLI, use:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli install-hermes-plugin --enable --platform cli
```

After installing, restart Hermes gateway or start a fresh Hermes CLI/session before expecting new tools to appear.

Useful restart command when available:

```bash
hermes gateway restart
```

or ask the user to send `/restart` from their gateway chat.

## 5. Authorize WHOOP

Generate an authorization URL:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli auth-url
```

Ask the user to open the URL, approve access, and copy the `code=...` query parameter from the final redirected URL.

Exchange the code locally:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli callback --code 'PASTE_CODE_HERE'
```

Expected local token path:

```text
~/.hermes/whoop/token.json
```

## 6. Run initial local sync

Fetch recent data first so latest answers work immediately:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli fetch --days 7
```

Then run a bounded historical backfill:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli backfill --max-chunks 24 --sleep-seconds 2
```

For a deeper all-time backfill, keep rerunning without `--no-resume`; it resumes from `~/.hermes/whoop/backfill_index.json`.

## 7. Verify setup

Run:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli status
"$HERMES_PYTHON" -m whoop_local_sync.cli latest --refresh-if-stale --max-age-minutes 30 --refresh-days 7
```

If running inside Hermes after a restart, verify plugin tools:

```text
whoop_status
whoop_auth_url
whoop_callback
whoop_fetch
whoop_backfill
whoop_latest
```

A good final report should include:

- package installed successfully
- plugin installed and enabled platforms
- token saved locally
- recent fetch command and result
- bounded backfill command and result
- status summary
- latest summary if available
- any failed endpoints and their exact API errors

## 8. Optional local daily refresh

Do not schedule background jobs without user consent. If the user wants the local cache warmed automatically, create a local-only daily Hermes cron job or system cron that runs:

```bash
"$HERMES_PYTHON" -m whoop_local_sync.cli fetch --days 7
```

Recommended delivery for Hermes cron: local only, no chat spam.

## Troubleshooting

### Missing credentials

Add `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, and `WHOOP_REDIRECT_URI` to `~/.hermes/.env`, then restart Hermes gateway or start a new CLI session.

### Redirect URI mismatch

The redirect URI in `~/.hermes/.env` must exactly match the WHOOP Developer App callback URL. Recommended:

```text
http://127.0.0.1:8787/callback
```

### Cloudflare / browser signature errors

WHOOP endpoints can reject non-browser-looking clients. This package sends a normal browser-like User-Agent and lets `WHOOP_USER_AGENT` override it.

### Rate limits during backfill

The client retries HTTP 429/5xx with backoff. If a long backfill fails, rerun the same command; it resumes from checkpoint.

### Plugin installed but tools missing

Restart Hermes gateway or start a new Hermes session. Tool and plugin changes do not reliably appear mid-session.

### Data locations

```text
~/.hermes/whoop/token.json
~/.hermes/whoop/latest.json
~/.hermes/whoop/whoop.sqlite
~/.hermes/whoop/raw/
~/.hermes/whoop/backfill_index.json
```
