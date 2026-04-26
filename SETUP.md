# Hermes Agent setup for whoop-local-sync

This guide is for installing `whoop-local-sync` as a Hermes Agent plugin, so Hermes can answer questions such as:

- "what's my recovery today?"
- "how much did I sleep yesterday?"
- "fetch latest WHOOP"
- "show WHOOP status"

The integration is local-first:

- WHOOP OAuth tokens are stored locally.
- WHOOP data is stored locally under `~/.hermes/whoop` by default.
- Raw WHOOP data is not written into Hermes long-term memory.

## Quick agent prompt

If you are asking Hermes Agent to install this for you, paste this prompt:

```text
Install https://github.com/Wysie/whoop-local-sync as a Hermes Agent plugin.
Follow SETUP.md from the repository.
Use the Hermes venv at ~/.hermes/hermes-agent/venv if it exists.
Install the package, run `whoop-local install-hermes-plugin --enable --platform cli --platform whatsapp --platform telegram`, configure WHOOP environment variables in ~/.hermes/.env, verify plugin discovery/status, and tell me the WHOOP auth URL I need to open.
Do not commit or print my WHOOP client secret, OAuth token, latest.json, raw data, or SQLite database.
```

## Prerequisites

1. Hermes Agent installed locally.
2. A WHOOP developer app from https://developer.whoop.com/.
3. The WHOOP app configured with this redirect/callback URL:

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

Webhook URL is not required. This project is pull-based by default.

## 1. Install into the Hermes Python environment

Use Hermes' Python environment so the plugin can import the package:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install "git+https://github.com/Wysie/whoop-local-sync.git"
```

If your Hermes venv is somewhere else, use that Python instead.

## 2. Install and enable the bundled Hermes plugin

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local install-hermes-plugin \
  --enable \
  --platform cli \
  --platform whatsapp \
  --platform telegram
```

This copies plugin files into:

```text
~/.hermes/plugins/whoop-local-sync
```

With `--enable`, it also backs up and patches `~/.hermes/config.yaml`:

- adds `whoop-local-sync` to `plugins.enabled`
- adds the `whoop` toolset to selected platforms
- records `whoop` under `known_plugin_toolsets`

Restart Hermes gateway, or start a fresh Hermes CLI session, after installation.

## 3. Configure environment variables

When running as a Hermes plugin, put these in Hermes' environment file:

```bash
~/.hermes/.env
```

Add:

```bash
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=replace-me
WHOOP_REDIRECT_URI=http://127.0.0.1:8787/callback

# Optional, but recommended freshness defaults
WHOOP_AUTO_REFRESH_ON_LATEST=true
WHOOP_REFRESH_MAX_AGE_MINUTES=30
WHOOP_REFRESH_DAYS=7
```

Do not commit this file. It contains secrets.

### Variable meanings

- `WHOOP_CLIENT_ID`: WHOOP developer app client ID.
- `WHOOP_CLIENT_SECRET`: WHOOP developer app client secret.
- `WHOOP_REDIRECT_URI`: must exactly match the WHOOP developer app redirect/callback URL.
- `WHOOP_AUTO_REFRESH_ON_LATEST=true`: lets `whoop-local latest` auto-fetch if cache is stale.
- `WHOOP_REFRESH_MAX_AGE_MINUTES=30`: stale threshold before refreshing.
- `WHOOP_REFRESH_DAYS=7`: when refreshing, re-sync the last 7 days to catch late edits.

## 4. Restart Hermes

After installing the plugin or changing `~/.hermes/.env`, restart Hermes gateway if you use WhatsApp/Telegram/other gateway platforms.

Exact restart command depends on how Hermes is run. Common options:

```bash
# If using a foreground gateway process, stop and start it again.
hermes gateway run

# If managed by a user service, restart that service.
systemctl --user restart hermes-gateway
```

If you only use Hermes CLI, start a new CLI session.

## 5. Authorize WHOOP

Generate an auth URL:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local auth-url
```

Or ask Hermes:

```text
Generate my WHOOP auth URL
```

Open the URL, approve access, and copy the `code=...` value from the redirected URL.

Exchange the code:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local callback --code 'PASTE_CODE_HERE'
```

Or ask Hermes to call `whoop_callback` with the code.

## 6. Fetch recent data

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local fetch --days 7
```

Check status:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local status
```

Read latest:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local latest --refresh-if-stale
```

## 7. Backfill historical data

Backfill walks backwards in chunks and resumes from `~/.hermes/whoop/backfill_index.json`.

Recommended first backfill:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local backfill \
  --chunk-days 30 \
  --empty-stop 12 \
  --sleep-seconds 2
```

Useful limited/safe backfill:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local backfill \
  --max-chunks 24 \
  --sleep-seconds 2
```

Why `empty-stop 12`? WHOOP history can have long gaps, and API errors/rate limits should not be mistaken for empty history.

## 8. Optional daily cron

You do not need webhooks for the usual setup. A daily pull plus stale-cache guard is enough for most sleep/recovery queries.

Recommended MVP cron:

```cron
30 7 * * * WHOOP_DATA_DIR=$HOME/.hermes/whoop $HOME/.hermes/hermes-agent/venv/bin/whoop-local fetch --days 7
```

Optional weekly reconciliation:

```cron
0 3 * * 0 WHOOP_DATA_DIR=$HOME/.hermes/whoop $HOME/.hermes/hermes-agent/venv/bin/whoop-local backfill --max-chunks 24 --sleep-seconds 2
```

## 9. Verify Hermes plugin tools

After restart, Hermes should expose the `whoop` toolset with tools like:

- `whoop_status`
- `whoop_auth_url`
- `whoop_callback`
- `whoop_fetch`
- `whoop_backfill`
- `whoop_latest`

Try asking Hermes:

```text
show WHOOP status
```

Expected healthy state after OAuth/fetch:

- token exists
- latest exists
- SQLite record count is greater than zero after fetch/backfill

## Troubleshooting

### Missing credentials

Error:

```text
Missing WHOOP_CLIENT_ID/WHOOP_CLIENT_SECRET in env or ~/.hermes/.env
```

Fix: add credentials to `~/.hermes/.env`, then restart Hermes gateway or open a new CLI session.

### Plugin not visible in Hermes

Run installer again:

```bash
~/.hermes/hermes-agent/venv/bin/whoop-local install-hermes-plugin --enable --platform cli --platform whatsapp --platform telegram
```

Then restart Hermes gateway.

### Redirect URI mismatch

The WHOOP developer app redirect URL and `WHOOP_REDIRECT_URI` must match exactly:

```text
http://127.0.0.1:8787/callback
```

### Rate limits during backfill

The client retries HTTP 429/5xx with backoff. If a long backfill fails, rerun the same command; it resumes from checkpoint.

## Data locations

Default Hermes plugin data directory:

```text
~/.hermes/whoop
```

Important files:

```text
token.json              OAuth token, chmod 600
latest.json             latest fetched WHOOP JSON
whoop.sqlite            deduped SQLite archive
backfill_index.json     checkpoint/resume metadata
raw/                    raw chunk JSON archive
```

Do not commit these files.
