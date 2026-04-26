from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


def deep_get(obj: Any, paths: Iterable[str]) -> Any:
    for path in paths:
        cur = obj
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return None


def latest_record(records, time_paths) -> Optional[Dict[str, Any]]:
    usable = [r for r in records if isinstance(r, dict) and "error" not in r]
    if not usable:
        return None
    return sorted(usable, key=lambda r: str(deep_get(r, time_paths) or ""))[-1]


def seconds_to_hm(value: Any) -> str:
    try:
        sec = int(float(value))
    except Exception:
        return "n/a"
    h, rem = divmod(sec, 3600)
    return f"{h}h{rem // 60:02d}m"


def compact_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    rec = latest_record(data.get("recoveries") or [], ["created_at", "updated_at"])
    sleep = latest_record(data.get("sleeps") or [], ["end", "updated_at", "created_at"])
    cycle = latest_record(data.get("cycles") or [], ["end", "updated_at", "created_at"])
    workout = latest_record(data.get("workouts") or [], ["end", "updated_at", "created_at"])
    sleep_seconds = deep_get(sleep, ["score.stage_summary.total_in_bed_time_milli", "score.stage_summary.total_sleep_time_milli", "score.total_in_bed_time_milli"])
    if sleep_seconds is not None:
        try:
            sleep_seconds = int(sleep_seconds) / 1000 if int(sleep_seconds) > 100000 else int(sleep_seconds)
        except Exception:
            pass
    return {
        "fetched_at": data.get("fetched_at"),
        "range": data.get("range"),
        "recovery_percent": deep_get(rec, ["score.recovery_score", "score.recovery_percentage", "recovery_score"]),
        "hrv_rmssd_ms": deep_get(rec, ["score.hrv_rmssd_milli", "score.hrv_rmssd", "hrv_rmssd_milli"]),
        "resting_hr_bpm": deep_get(rec, ["score.resting_heart_rate", "resting_heart_rate"]),
        "sleep_duration": seconds_to_hm(sleep_seconds),
        "sleep_performance_percent": deep_get(sleep, ["score.sleep_performance_percentage", "score.sleep_performance", "sleep_performance_percentage"]),
        "sleep_efficiency_percent": deep_get(sleep, ["score.sleep_efficiency_percentage", "score.sleep_efficiency", "sleep_efficiency_percentage"]),
        "day_strain": deep_get(cycle, ["score.strain"]),
        "latest_workout_strain": deep_get(workout, ["score.strain"]),
        "counts": {k: len(data.get(k) or []) for k in ("cycles", "recoveries", "sleeps", "workouts")},
    }
