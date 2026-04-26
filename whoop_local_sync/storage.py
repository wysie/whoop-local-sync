from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict

SENSITIVE_KEYS = {"client_secret", "access_token", "refresh_token", "token", "api_key", "password"}


def redact_secret(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact_secret(v)
        return out
    if isinstance(obj, list):
        return [redact_secret(v) for v in obj]
    return obj


class LocalStore:
    def __init__(self, data_dir: os.PathLike | str):
        self.data_dir = Path(data_dir).expanduser()
        self.raw_dir = self.data_dir / "raw"
        self.latest_file = self.data_dir / "latest.json"
        self.index_file = self.data_dir / "backfill_index.json"
        self.token_file = self.data_dir / "token.json"
        self.db_file = self.data_dir / "whoop.sqlite"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def write_json_private(self, path: Path, obj: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass

    def save_token(self, token: Dict[str, Any]) -> None:
        self.write_json_private(self.token_file, token)

    def load_token(self) -> Dict[str, Any]:
        return json.loads(self.token_file.read_text(encoding="utf-8"))

    def write_chunk(self, data: Dict[str, Any], start_iso: str, end_iso: str, *, update_latest: bool = False) -> Path:
        path = self.raw_dir / f"backfill_{start_iso[:10]}_{end_iso[:10]}.json"
        self.write_json_private(path, data)
        if update_latest:
            self.write_json_private(self.latest_file, data)
        return path

    def save_latest(self, data: Dict[str, Any]) -> None:
        self.write_json_private(self.latest_file, data)

    def save_index(self, index: Dict[str, Any]) -> None:
        self.write_json_private(self.index_file, redact_secret(index))

    def load_index(self) -> Dict[str, Any]:
        if not self.index_file.exists():
            return {"chunks": [], "failures": []}
        data = json.loads(self.index_file.read_text(encoding="utf-8"))
        data.setdefault("chunks", [])
        data.setdefault("failures", [])
        return data

    def connect(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_file)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                endpoint TEXT NOT NULL,
                record_id TEXT NOT NULL,
                range_start TEXT,
                range_end TEXT,
                timestamp TEXT,
                raw_json TEXT NOT NULL,
                PRIMARY KEY(endpoint, record_id)
            )
            """
        )
        return conn

    def upsert_records(self, data: Dict[str, Any]) -> None:
        conn = self.connect()
        try:
            start = (data.get("range") or {}).get("start")
            end = (data.get("range") or {}).get("end")
            rows = []
            for endpoint in ("cycles", "recoveries", "sleeps", "workouts"):
                for record in data.get(endpoint) or []:
                    if not isinstance(record, dict) or record.get("error"):
                        continue
                    rid = str(record.get("id") or record.get("cycle_id") or record.get("sleep_id") or record.get("v1_id") or hash(json.dumps(record, sort_keys=True)))
                    timestamp = record.get("start") or record.get("end") or record.get("created_at") or record.get("updated_at")
                    rows.append((endpoint, rid, start, end, timestamp, json.dumps(record, sort_keys=True)))
            conn.executemany(
                """
                INSERT INTO records(endpoint, record_id, range_start, range_end, timestamp, raw_json)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(endpoint, record_id) DO UPDATE SET
                    range_start=excluded.range_start,
                    range_end=excluded.range_end,
                    timestamp=excluded.timestamp,
                    raw_json=excluded.raw_json
                """,
                rows,
            )
            conn.commit()
        finally:
            conn.close()

    def record_count(self) -> int:
        conn = self.connect()
        try:
            return int(conn.execute("SELECT COUNT(*) FROM records").fetchone()[0])
        finally:
            conn.close()
