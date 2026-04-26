from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

from .backfill import BackfillConfig, chunk_backwards, count_records, endpoint_errors, iso_z, parse_iso, should_stop_for_empty_streak
from .client import WhoopClient
from .oauth import DEFAULT_REDIRECT_URI, DEFAULT_SCOPES, build_auth_url, load_dotenv
from .storage import LocalStore
from .summary import compact_summary


def data_dir() -> Path:
    return Path(os.environ.get("WHOOP_DATA_DIR") or (Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "whoop"))


def load_creds():
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    load_dotenv(hermes_home / ".env")
    client_id = os.environ.get("WHOOP_CLIENT_ID", "").strip()
    client_secret = os.environ.get("WHOOP_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get("WHOOP_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip() or DEFAULT_REDIRECT_URI
    if not client_id or not client_secret:
        raise SystemExit("Missing WHOOP_CLIENT_ID/WHOOP_CLIENT_SECRET in env or ~/.hermes/.env")
    return client_id, client_secret, redirect_uri


def client_from_token(store: LocalStore) -> WhoopClient:
    client_id, client_secret, redirect_uri = load_creds()
    tok = store.load_token()
    if int(tok.get("expires_at") or 0) <= int(time.time()):
        refreshed = WhoopClient(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri).refresh_token(tok["refresh_token"])
        if "refresh_token" not in refreshed:
            refreshed["refresh_token"] = tok.get("refresh_token")
        refreshed["saved_at"] = int(time.time())
        refreshed["expires_at"] = int(time.time()) + int(refreshed.get("expires_in") or 0) - 60
        store.save_token(refreshed)
        tok = refreshed
    return WhoopClient(access_token=tok["access_token"], client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)


def cmd_auth_url(args):
    client_id, _, redirect_uri = load_creds()
    print(build_auth_url(client_id=client_id, redirect_uri=redirect_uri, scopes=args.scopes or DEFAULT_SCOPES, state=args.state))


def cmd_callback(args):
    store = LocalStore(data_dir())
    client_id, client_secret, redirect_uri = load_creds()
    tok = WhoopClient(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri).exchange_code(args.code)
    tok["saved_at"] = int(time.time())
    if "expires_in" in tok:
        tok["expires_at"] = int(time.time()) + int(tok.get("expires_in") or 0) - 60
    store.save_token(tok)
    print(json.dumps({"ok": True, "token_file": str(store.token_file), "expires_in": tok.get("expires_in")}, indent=2))


def cmd_fetch(args):
    store = LocalStore(data_dir())
    end = parse_iso(args.end) if args.end else dt.datetime.now(dt.timezone.utc)
    start = parse_iso(args.start) if args.start else end - dt.timedelta(days=args.days)
    data = client_from_token(store).fetch_range(iso_z(start), iso_z(end))
    errors = endpoint_errors(data)
    if errors:
        raise SystemExit(json.dumps({"ok": False, "errors": errors}, indent=2))
    store.save_latest(data)
    store.write_chunk(data, iso_z(start), iso_z(end), update_latest=True)
    store.upsert_records(data)
    print(json.dumps({"ok": True, "summary": compact_summary(data), "record_count": store.record_count()}, indent=2))


def cmd_backfill(args):
    store = LocalStore(data_dir())
    cfg = BackfillConfig(chunk_days=args.chunk_days, empty_stop=args.empty_stop, floor=args.floor, sleep_seconds=args.sleep_seconds)
    idx = store.load_index() if not args.no_resume else {"chunks": [], "failures": []}
    cursor = parse_iso(idx.get("next_end")) if idx.get("next_end") and not args.no_resume else dt.datetime.now(dt.timezone.utc)
    floor = parse_iso(cfg.floor)
    empty_streak = int(idx.get("empty_streak") or 0) if not args.no_resume else 0
    chunks_done = 0
    records_total = 0
    client = client_from_token(store)
    stopped_reason = None
    for start, end in chunk_backwards(cursor_end=cursor, floor=floor, chunk_days=cfg.chunk_days):
        if args.max_chunks is not None and chunks_done >= args.max_chunks:
            stopped_reason = "max_chunks"
            break
        start_iso, end_iso = iso_z(start), iso_z(end)
        data = client.fetch_range(start_iso, end_iso)
        errors = endpoint_errors(data)
        if errors:
            failure = {"start": start_iso, "end": end_iso, "errors": errors, "at": iso_z(dt.datetime.now(dt.timezone.utc))}
            idx.setdefault("failures", []).append(failure)
            store.save_index(idx)
            raise SystemExit(json.dumps({"ok": False, "failure": failure}, indent=2))
        counts = count_records(data)
        raw = store.write_chunk(data, start_iso, end_iso, update_latest=(chunks_done == 0 and not idx.get("next_end")))
        store.upsert_records(data)
        empty_streak = empty_streak + 1 if counts["total"] == 0 else 0
        chunk = {"start": start_iso, "end": end_iso, "counts": counts, "raw_path": str(raw), "empty_streak_after": empty_streak}
        idx.setdefault("chunks", []).append(chunk)
        idx.update({"next_end": start_iso, "empty_streak": empty_streak, "last_chunk": chunk, "chunk_days": cfg.chunk_days, "empty_stop": cfg.empty_stop, "floor": cfg.floor})
        store.save_index(idx)
        chunks_done += 1
        records_total += counts["total"]
        print(f"Backfilled {start_iso} -> {end_iso}: {counts['total']} records", flush=True)
        if should_stop_for_empty_streak(empty_streak, cfg):
            stopped_reason = "consecutive_empty_chunks"
            break
        if cfg.sleep_seconds > 0:
            time.sleep(cfg.sleep_seconds)
    stopped_reason = stopped_reason or "floor_reached"
    idx.update({"stopped_reason": stopped_reason, "completed_at": iso_z(dt.datetime.now(dt.timezone.utc))})
    store.save_index(idx)
    print(json.dumps({"ok": True, "stopped_reason": stopped_reason, "chunks_done": chunks_done, "records_total": records_total, "record_count": store.record_count()}, indent=2))


def cmd_status(args):
    store = LocalStore(data_dir())
    print(json.dumps({
        "ok": True,
        "data_dir": str(store.data_dir),
        "has_token": store.token_file.exists(),
        "latest_exists": store.latest_file.exists(),
        "raw_files": len(list(store.raw_dir.glob("*.json"))) if store.raw_dir.exists() else 0,
        "record_count": store.record_count(),
    }, indent=2))


def cmd_latest(args):
    store = LocalStore(data_dir())
    if not store.latest_file.exists():
        raise SystemExit("No latest.json found; run fetch first")
    data = json.loads(store.latest_file.read_text())
    print(json.dumps(data if args.json else compact_summary(data), indent=2))


def cmd_install_hermes_plugin(args):
    from .hermes_install import install_hermes_plugin

    result = install_hermes_plugin(
        hermes_home=Path(args.hermes_home).expanduser() if args.hermes_home else None,
        enable=args.enable,
        platforms=args.platform or ["cli", "whatsapp", "telegram"],
    )
    print(json.dumps(result, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="whoop-local")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("auth-url")
    p.add_argument("--state", default="whoop-local-sync")
    p.add_argument("--scopes", nargs="*")
    p.set_defaults(func=cmd_auth_url)
    p = sub.add_parser("callback")
    p.add_argument("--code", required=True)
    p.set_defaults(func=cmd_callback)
    p = sub.add_parser("fetch")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--start")
    p.add_argument("--end")
    p.set_defaults(func=cmd_fetch)
    p = sub.add_parser("backfill")
    p.add_argument("--chunk-days", type=int, default=30)
    p.add_argument("--empty-stop", type=int, default=12)
    p.add_argument("--floor", default="2015-01-01T00:00:00Z")
    p.add_argument("--max-chunks", type=int)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--sleep-seconds", type=float, default=2.0)
    p.set_defaults(func=cmd_backfill)
    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("latest")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_latest)
    p = sub.add_parser("install-hermes-plugin", help="Install bundled Hermes plugin into ~/.hermes/plugins/whoop-local-sync")
    p.add_argument("--hermes-home", help="Hermes home directory; defaults to ~/.hermes")
    p.add_argument("--enable", action="store_true", help="Patch config.yaml to enable plugin and whoop toolset")
    p.add_argument("--platform", action="append", help="Platform to enable whoop toolset for; repeatable. Defaults to cli, whatsapp, telegram")
    p.set_defaults(func=cmd_install_hermes_plugin)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
