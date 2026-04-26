import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from whoop_local_sync.backfill import BackfillConfig, chunk_backwards, should_stop_for_empty_streak
from whoop_local_sync.oauth import build_auth_url, token_payload
from whoop_local_sync.storage import LocalStore, redact_secret
from whoop_local_sync.cli import should_refresh_latest


def test_build_auth_url_uses_redirect_scopes_and_state():
    url = build_auth_url(
        client_id="client-123",
        redirect_uri="http://127.0.0.1:8787/callback",
        scopes=["offline", "read:profile"],
        state="abc",
    )
    assert url.startswith("https://api.prod.whoop.com/oauth/oauth2/auth?")
    assert "client_id=client-123" in url
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A8787%2Fcallback" in url
    assert "scope=offline+read%3Aprofile" in url
    assert "state=abc" in url


def test_token_payload_uses_client_secret_post_not_basic_auth():
    payload = token_payload(
        grant_type="authorization_code",
        client_id="cid",
        client_secret="secret",
        code="code123",
        redirect_uri="http://127.0.0.1:8787/callback",
    )
    assert payload["client_id"] == "cid"
    assert payload["client_secret"] == "secret"
    assert payload["grant_type"] == "authorization_code"
    assert "Authorization" not in payload


def test_chunk_backwards_walks_from_now_to_floor():
    chunks = list(chunk_backwards(
        cursor_end=datetime(2026, 4, 26, tzinfo=timezone.utc),
        floor=datetime(2026, 1, 1, tzinfo=timezone.utc),
        chunk_days=30,
    ))
    assert chunks[0][0].isoformat().startswith("2026-03-27")
    assert chunks[0][1].isoformat().startswith("2026-04-26")
    assert chunks[-1][0].isoformat().startswith("2026-01-01")


def test_empty_streak_stop_requires_configured_consecutive_empties():
    cfg = BackfillConfig(empty_stop=3)
    assert should_stop_for_empty_streak(2, cfg) is False
    assert should_stop_for_empty_streak(3, cfg) is True


def test_local_store_writes_chunk_index_and_sqlite_without_leaking_secret(tmp_path):
    store = LocalStore(tmp_path)
    data = {
        "range": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-31T00:00:00Z"},
        "cycles": [{"id": 1, "start": "2026-01-01T00:00:00Z"}],
        "recoveries": [],
        "sleeps": [],
        "workouts": [],
    }
    raw = store.write_chunk(data, "2026-01-01T00:00:00Z", "2026-01-31T00:00:00Z")
    assert raw.exists()
    store.upsert_records(data)
    assert store.record_count() == 1
    store.save_index({"client_secret": "super-secret", "ok": True})
    text = (tmp_path / "backfill_index.json").read_text()
    assert "super-secret" not in text
    assert "[REDACTED]" in text


def test_redact_secret_masks_sensitive_keys():
    obj = {"client_secret": "abc", "nested": {"refresh_token": "***", "safe": "ok"}}
    assert redact_secret(obj)["client_secret"] == "[REDACTED]"
    assert redact_secret(obj)["nested"]["refresh_token"] == "[REDACTED]"
    assert redact_secret(obj)["nested"]["safe"] == "ok"


def test_should_refresh_latest_when_missing_or_stale(tmp_path):
    latest = tmp_path / "latest.json"
    now = 1_000_000
    assert should_refresh_latest(latest, max_age_minutes=30, now=now) is True

    latest.write_text("{}")
    os.utime(latest, (now - 10 * 60, now - 10 * 60))
    assert should_refresh_latest(latest, max_age_minutes=30, now=now) is False

    os.utime(latest, (now - 31 * 60, now - 31 * 60))
    assert should_refresh_latest(latest, max_age_minutes=30, now=now) is True


def test_should_refresh_latest_can_be_disabled(tmp_path):
    latest = tmp_path / "latest.json"
    now = 1_000_000
    assert should_refresh_latest(latest, max_age_minutes=30, now=now, enabled=False) is False
