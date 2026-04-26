# whoop-local-sync

Local-first WHOOP OAuth sync, historical backfill, SQLite archiving, and optional Hermes Agent plugin wrapper.

This project was built for people who want their WHOOP data stored locally instead of pushed into a SaaS dashboard or long-term LLM memory.

## Features

- Official WHOOP OAuth authorization-code flow
- Uses `client_secret_post`, matching default WHOOP developer app auth settings
- Browser-like User-Agent for Cloudflare-protected WHOOP endpoints
- Fetches profile, body measurement, cycles, recovery, sleep, and workouts
- Backfills backwards from now in checkpointed chunks
- Retry/backoff for HTTP 429/5xx
- JSON raw chunk archive
- SQLite `records` table with endpoint/type, record ID, range, timestamp, and raw JSON
- Dedupe by `(endpoint, record_id)`
- Local-only by default
- Optional Hermes Agent plugin example under `plugins/hermes/`

## WHOOP Developer App Setup

Create an app at https://developer.whoop.com/ and configure:

Redirect URL / Callback URL:

```text
http://127.0.0.1:8787/callback
```

Scopes:

```text
offline
read:profile
read:body_measurement
read:cycles
read:recovery
read:sleep
read:workout
```

Webhook URL is not required for this project. This is a pull-based sync tool.

## Install

Development install:

```bash
git clone https://github.com/YOUR_USER/whoop-local-sync.git
cd whoop-local-sync
python -m pip install -e '.[dev]'
```

## Configuration

Set credentials in your shell or `.env` loaded by your wrapper:

```bash
export WHOOP_CLIENT_ID='...'
export WHOOP_CLIENT_SECRET='...'
export WHOOP_REDIRECT_URI='http://127.0.0.1:8787/callback'
```

Storage location:

```bash
export WHOOP_DATA_DIR="$HOME/.whoop-local-sync"
```

If `WHOOP_DATA_DIR` is not set, the CLI defaults to:

```text
$HERMES_HOME/whoop
```

or:

```text
~/.hermes/whoop
```

## CLI

Generate auth URL:

```bash
whoop-local auth-url
```

Open the URL, approve, then copy the `code=...` from the redirected URL.

Exchange code for token:

```bash
whoop-local callback --code 'PASTE_CODE'
```

Fetch recent data:

```bash
whoop-local fetch --days 7
```

Backfill history backwards:

```bash
whoop-local backfill --chunk-days 30 --empty-stop 12 --sleep-seconds 2
```

Read status:

```bash
whoop-local status
```

Read latest summary:

```bash
whoop-local latest
```

Read latest raw JSON:

```bash
whoop-local latest --json
```

## Backfill Behaviour

Default backfill walks backwards from the current date:

1. Fetch previous 30-day chunk
2. Save raw JSON chunk
3. Upsert records into SQLite
4. Checkpoint progress in `backfill_index.json`
5. Continue backwards until one of:
   - `empty_stop` consecutive empty chunks
   - configured floor date, default `2015-01-01T00:00:00Z`
   - optional `--max-chunks` safety cap

Why not stop after one empty chunk? WHOOP history can have wear gaps, subscription gaps, or API gaps. Consecutive empty chunks are safer.

## Cron Example

Daily recent sync:

```cron
30 7 * * * WHOOP_DATA_DIR=$HOME/.whoop-local-sync /path/to/whoop-local fetch --days 7
```

Weekly slow backfill/resume:

```cron
0 3 * * 0 WHOOP_DATA_DIR=$HOME/.whoop-local-sync /path/to/whoop-local backfill --max-chunks 24 --sleep-seconds 2
```

## Data Files

Inside `WHOOP_DATA_DIR`:

```text
token.json              OAuth token, chmod 600
latest.json             latest fetched JSON
backfill_index.json     checkpoint/resume metadata, redacted
whoop.sqlite            SQLite archive
raw/                    raw chunk JSON files
```

## SQLite Schema

`records` table:

```sql
CREATE TABLE records (
  endpoint TEXT NOT NULL,
  record_id TEXT NOT NULL,
  range_start TEXT,
  range_end TEXT,
  timestamp TEXT,
  raw_json TEXT NOT NULL,
  PRIMARY KEY(endpoint, record_id)
);
```

## Hermes Plugin

See `plugins/hermes/` for a minimal wrapper that registers WHOOP tools in Hermes Agent.

## Privacy & Safety

- Do not commit `.env`, `token.json`, `latest.json`, `whoop.sqlite`, or `raw/` files.
- Raw WHOOP health data stays local.
- Do not dump daily raw health metrics into LLM long-term memory.
- Only retain durable patterns if the user explicitly wants that.
- Secrets are redacted before writing checkpoint metadata.

## Development

```bash
python -m pytest -q
python -m whoop_local_sync.cli status
```

## License

MIT
