from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Tuple


@dataclass
class BackfillConfig:
    chunk_days: int = 30
    empty_stop: int = 12
    floor: str = "2015-01-01T00:00:00Z"
    sleep_seconds: float = 2.0


def parse_iso(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def chunk_backwards(*, cursor_end: dt.datetime, floor: dt.datetime, chunk_days: int) -> Iterator[Tuple[dt.datetime, dt.datetime]]:
    if chunk_days <= 0:
        raise ValueError("chunk_days must be > 0")
    cursor_end = cursor_end.astimezone(dt.timezone.utc)
    floor = floor.astimezone(dt.timezone.utc)
    while cursor_end > floor:
        chunk_start = max(floor, cursor_end - dt.timedelta(days=chunk_days))
        yield chunk_start, cursor_end
        cursor_end = chunk_start


def should_stop_for_empty_streak(empty_streak: int, config: BackfillConfig) -> bool:
    return empty_streak >= config.empty_stop


def count_records(data: Dict) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for key in ("cycles", "recoveries", "sleeps", "workouts"):
        records = data.get(key) or []
        counts[key] = len([r for r in records if isinstance(r, dict) and "error" not in r])
    counts["total"] = sum(counts.values())
    return counts


def endpoint_errors(data: Dict) -> Dict[str, List[str]]:
    errors: Dict[str, List[str]] = {}
    for key in ("cycles", "recoveries", "sleeps", "workouts"):
        vals = [str(r["error"]) for r in data.get(key) or [] if isinstance(r, dict) and r.get("error")]
        if vals:
            errors[key] = vals
    return errors
