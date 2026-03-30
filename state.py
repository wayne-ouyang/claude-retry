#!/usr/bin/env python3
"""Shared state store — ~/.claude/retry-guardian/state.json"""
import json
import time
from pathlib import Path

DATA_DIR = Path.home() / ".claude" / "retry-guardian"


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _path():
    return DATA_DIR / "state.json"


def _log():
    return DATA_DIR / "failures.jsonl"


def _default():
    return {
        "status": "idle",
        "retry_count": 0,
        "total_failures_session": 0,
        "last_failure_ts": None,
        "last_failure_error": None,
        "last_recovery_ts": None,
        "session_id": None,
    }


def load() -> dict:
    _ensure()
    p = _path()
    if not p.exists():
        return _default()
    try:
        return json.loads(p.read_text())
    except Exception:
        return _default()


def save(s: dict):
    _ensure()
    _path().write_text(json.dumps(s, indent=2))


def record_failure(session_id: str, error: str) -> dict:
    s = load()
    s["status"] = "retrying"
    s["retry_count"] = s.get("retry_count", 0) + 1
    s["total_failures_session"] = s.get("total_failures_session", 0) + 1
    s["last_failure_ts"] = time.time()
    s["last_failure_error"] = error[:200] if error else "unknown"
    s["session_id"] = session_id
    save(s)
    entry = {
        "ts": s["last_failure_ts"],
        "session_id": session_id,
        "error": s["last_failure_error"],
        "retry_count": s["retry_count"],
    }
    with open(_log(), "a") as f:
        f.write(json.dumps(entry) + "\n")
    return s


def record_recovery() -> dict:
    s = load()
    s["status"] = "recovered"
    s["retry_count"] = 0
    s["last_recovery_ts"] = time.time()
    save(s)
    return s


def record_clean_stop(session_id: str) -> dict:
    s = _default()
    s["session_id"] = session_id
    s["status"] = "idle"
    save(s)
    return s


def record_gave_up() -> dict:
    s = load()
    s["status"] = "gave_up"
    save(s)
    return s


def record_session_start(session_id: str) -> dict:
    s = _default()
    s["session_id"] = session_id
    save(s)
    return s
