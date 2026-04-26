# Hermes Plugin Wrapper

This plugin is bundled inside the `whoop-local-sync` Python package.

Recommended install:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install "git+https://github.com/YOUR_USER/whoop-local-sync.git"
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
