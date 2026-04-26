# Hermes Plugin Wrapper

This folder is a minimal Hermes Agent user-plugin wrapper for `whoop-local-sync`.

Install the Python package into the Hermes venv first:

```bash
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python -e /path/to/whoop-local-sync
```

Then copy or symlink this folder into:

```text
~/.hermes/plugins/whoop-local-sync
```

Enable it in `~/.hermes/config.yaml` under `plugins.enabled`, then enable the `whoop` toolset for the target platform.

The plugin shells out to:

```bash
python -m whoop_local_sync.cli ...
```

so it uses the same Python interpreter as the running Hermes process.
