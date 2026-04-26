from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_TOOLSET = "whoop"


def _run(args, timeout=300):
    cmd = [sys.executable, "-m", "whoop_local_sync.cli", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "command": " ".join(cmd)}


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def register(ctx):
    ctx.register_tool(
        name="whoop_status",
        toolset=_TOOLSET,
        schema={"name": "whoop_status", "description": "Check local WHOOP sync status.", "parameters": {"type": "object", "properties": {}}},
        handler=lambda args=None, **kw: _json(_run(["status"], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Check WHOOP status",
        emoji="⌚",
    )

    ctx.register_tool(
        name="whoop_auth_url",
        toolset=_TOOLSET,
        schema={"name": "whoop_auth_url", "description": "Generate WHOOP OAuth URL.", "parameters": {"type": "object", "properties": {"state": {"type": "string", "default": "whoop-local-sync"}}}},
        handler=lambda args=None, **kw: _json(_run(["auth-url", "--state", (args or {}).get("state", "whoop-local-sync")], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Generate WHOOP OAuth URL",
        emoji="🔐",
    )

    def callback(args=None, **kw):
        code = (args or {}).get("code")
        if not code:
            return _json({"ok": False, "error": "code is required"})
        return _json(_run(["callback", "--code", code], timeout=120))

    ctx.register_tool(
        name="whoop_callback",
        toolset=_TOOLSET,
        schema={"name": "whoop_callback", "description": "Exchange WHOOP OAuth code for token.", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
        handler=callback,
        check_fn=lambda: True,
        requires_env=[],
        description="Exchange WHOOP OAuth code",
        emoji="✅",
    )

    def fetch(args=None, **kw):
        args = args or {}
        cmd = ["fetch", "--days", str(int(args.get("days", 7)))]
        if args.get("start"):
            cmd += ["--start", args["start"]]
        if args.get("end"):
            cmd += ["--end", args["end"]]
        return _json(_run(cmd, timeout=300))

    ctx.register_tool(
        name="whoop_fetch",
        toolset=_TOOLSET,
        schema={"name": "whoop_fetch", "description": "Fetch recent WHOOP data.", "parameters": {"type": "object", "properties": {"days": {"type": "integer", "default": 7}, "start": {"type": "string"}, "end": {"type": "string"}}}},
        handler=fetch,
        check_fn=lambda: True,
        requires_env=[],
        description="Fetch WHOOP data",
        emoji="📈",
    )

    def backfill(args=None, **kw):
        args = args or {}
        cmd = ["backfill"]
        for k, flag in [("chunk_days", "--chunk-days"), ("empty_stop", "--empty-stop"), ("floor", "--floor"), ("max_chunks", "--max-chunks"), ("sleep_seconds", "--sleep-seconds")]:
            if args.get(k) is not None:
                cmd += [flag, str(args[k])]
        if args.get("no_resume"):
            cmd.append("--no-resume")
        return _json(_run(cmd, timeout=1800))

    ctx.register_tool(
        name="whoop_backfill",
        toolset=_TOOLSET,
        schema={"name": "whoop_backfill", "description": "Backfill WHOOP history backwards with checkpoint/resume.", "parameters": {"type": "object", "properties": {"chunk_days": {"type": "integer", "default": 30}, "empty_stop": {"type": "integer", "default": 12}, "floor": {"type": "string", "default": "2015-01-01T00:00:00Z"}, "max_chunks": {"type": "integer"}, "sleep_seconds": {"type": "number", "default": 2}, "no_resume": {"type": "boolean", "default": False}}}},
        handler=backfill,
        check_fn=lambda: True,
        requires_env=[],
        description="Backfill WHOOP history",
        emoji="⏪",
    )

    ctx.register_tool(
        name="whoop_latest",
        toolset=_TOOLSET,
        schema={"name": "whoop_latest", "description": "Read latest local WHOOP summary, auto-refreshing first when cache is stale if enabled.", "parameters": {"type": "object", "properties": {"json": {"type": "boolean", "default": False}, "refresh_if_stale": {"type": "boolean", "default": True}, "max_age_minutes": {"type": "integer", "default": 30}, "refresh_days": {"type": "integer", "default": 7}}}},
        handler=lambda args=None, **kw: _json(_run(["latest"] + (["--json"] if (args or {}).get("json") else []) + (["--refresh-if-stale"] if (args or {}).get("refresh_if_stale", True) else []) + (["--max-age-minutes", str((args or {}).get("max_age_minutes"))] if (args or {}).get("max_age_minutes") is not None else []) + (["--refresh-days", str((args or {}).get("refresh_days"))] if (args or {}).get("refresh_days") is not None else []), timeout=300)),
        check_fn=lambda: True,
        requires_env=[],
        description="Read latest WHOOP data",
        emoji="📄",
    )
