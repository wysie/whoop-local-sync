# Hermes Plugin Wrapper

This plugin is bundled inside the `whoop-local-sync` Python package.

Recommended install:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install "git+https://github.com/Wysie/whoop-local-sync.git"
~/.hermes/hermes-agent/venv/bin/whoop-local install-hermes-plugin --enable --platform cli --platform whatsapp --platform telegram
```

The installer copies this plugin to:

```text
~/.hermes/plugins/whoop-local-sync
```

and, with `--enable`, patches `~/.hermes/config.yaml` after creating a backup.

Manual install is still possible:

```bash
mkdir -p ~/.hermes/plugins/whoop-local-sync
cp -R plugins/hermes/* ~/.hermes/plugins/whoop-local-sync/
```

Then enable `whoop-local-sync` under `plugins.enabled` and add the `whoop` toolset to your target platform toolsets.

## Freshness

`whoop_latest` calls `whoop-local latest --refresh-if-stale` by default.

Default behavior:

- cache missing: fetch first
- cache older than 30 minutes: fetch first
- refresh window: last 7 days

Override per tool call with `refresh_if_stale`, `max_age_minutes`, and `refresh_days`, or set environment defaults:

```bash
WHOOP_AUTO_REFRESH_ON_LATEST=true
WHOOP_REFRESH_MAX_AGE_MINUTES=30
WHOOP_REFRESH_DAYS=7
```
