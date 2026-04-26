from __future__ import annotations

import shutil
import time
from importlib.resources import files
from pathlib import Path
from typing import Iterable, List

import yaml

PLUGIN_NAME = "whoop-local-sync"
TOOLSET_NAME = "whoop"


def _dedupe(seq):
    out = []
    for item in seq or []:
        if item not in out:
            out.append(item)
    return out


def _plugin_source():
    return files("whoop_local_sync").joinpath("hermes_plugin")


def _copy_plugin(dest: Path) -> None:
    src = _plugin_source()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _patch_config(config_path: Path, platforms: Iterable[str]) -> Path:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        backup = config_path.with_name(f"config.yaml.bak-whoop-local-sync-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(config_path, backup)
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        backup = config_path.with_name(f"config.yaml.bak-whoop-local-sync-{time.strftime('%Y%m%d-%H%M%S')}")
        data = {}

    data.setdefault("plugins", {})
    data["plugins"].setdefault("enabled", [])
    data["plugins"]["enabled"] = _dedupe([*data["plugins"].get("enabled", []), PLUGIN_NAME])

    data.setdefault("platform_toolsets", {})
    data.setdefault("known_plugin_toolsets", {})
    for platform in platforms:
        data["platform_toolsets"].setdefault(platform, [])
        data["platform_toolsets"][platform] = _dedupe([*data["platform_toolsets"].get(platform, []), TOOLSET_NAME])
        data["known_plugin_toolsets"].setdefault(platform, [])
        data["known_plugin_toolsets"][platform] = _dedupe([*data["known_plugin_toolsets"].get(platform, []), TOOLSET_NAME])

    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return backup


def install_hermes_plugin(*, hermes_home: Path | str | None = None, enable: bool = False, platforms: Iterable[str] | None = None) -> dict:
    hermes_home = Path(hermes_home).expanduser() if hermes_home else Path.home() / ".hermes"
    platforms = list(platforms or ["cli", "whatsapp", "telegram"])
    plugin_dir = hermes_home / "plugins" / PLUGIN_NAME
    _copy_plugin(plugin_dir)
    result = {
        "ok": True,
        "plugin_dir": str(plugin_dir),
        "enabled": enable,
        "platforms": platforms,
        "next_steps": [
            "Add WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, and WHOOP_REDIRECT_URI to ~/.hermes/.env",
            "Restart Hermes gateway or start a fresh CLI session",
            "Run whoop_auth_url, approve in browser, then run whoop_callback with the returned code",
        ],
    }
    if enable:
        backup = _patch_config(hermes_home / "config.yaml", platforms)
        result["config_backup"] = str(backup)
    return result
