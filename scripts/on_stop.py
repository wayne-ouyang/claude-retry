#!/usr/bin/env python3
"""
claude-retry — Stop hook

Fires every time Claude finishes a response (Stop event).

Logic:
  1. If stop_hook_active → already in a forced retry loop, exit 0 to break it.
  2. Parse the transcript JSONL for API error patterns in recent entries.
  3. Error found → sleep(backoff), return {"decision": "block"} to force retry.
  4. No error → exit 0 (Claude stops normally).
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import state as st

# ── Config (env-overridable) ──────────────────────────────────────────────────
MAX_RETRIES = int(os.environ.get("CLAUDE_RETRY_MAX_RETRIES", "5"))
BASE_DELAY = float(os.environ.get("CLAUDE_RETRY_DELAY", "3"))
BACKOFF = float(os.environ.get("CLAUDE_RETRY_BACKOFF", "2"))
MAX_DELAY = float(os.environ.get("CLAUDE_RETRY_MAX_DELAY", "60"))

# ── API error patterns ────────────────────────────────────────────────────────
_ERROR_RE = re.compile(
    "|".join(
        [
            r"overloaded_error",
            r"rate.?limit",
            r"529",
            r"503",
            r"APIError",
            r"api_error",
            r'"error".*"type"',
            r"Request failed",
            r"Connection error",
            r"network.*error",
            r"timeout.*error",
            r"internal_server_error",
        ]
    ),
    re.IGNORECASE,
)


def _backoff(attempt: int) -> float:
    return min(BASE_DELAY * (BACKOFF ** (attempt - 1)), MAX_DELAY)


def _detect_error(transcript_path: str) -> str | None:
    if not transcript_path:
        return None
    p = Path(transcript_path)
    if not p.exists():
        return None
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None

    for raw in reversed(lines[-50:]):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if "error" in entry and entry["error"]:
            err = (
                json.dumps(entry["error"])
                if isinstance(entry["error"], dict)
                else str(entry["error"])
            )
            if _ERROR_RE.search(err):
                return err[:120]

        content = entry.get("content") or entry.get("message") or ""
        if isinstance(content, list):
            content = json.dumps(content)
        if isinstance(content, str):
            m = _ERROR_RE.search(content)
            if m:
                return content[max(0, m.start() - 20) : m.start() + 80]

    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    stop_hook_active = data.get("stop_hook_active", False)
    transcript_path = data.get("transcript_path", "")

    # Already retrying — let Claude stop to break the loop
    if stop_hook_active:
        sys.exit(0)

    error_text = _detect_error(transcript_path)

    if error_text is None:
        sys.exit(0)

    new_state = st.record_failure(session_id, error_text)
    retry_num = new_state["retry_count"]

    if retry_num > MAX_RETRIES:
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        f"claude-retry: gave up after {MAX_RETRIES} retries. "
                        f"Last error: {error_text[:100]}"
                    ),
                }
            )
        )
        sys.exit(0)

    time.sleep(_backoff(retry_num))

    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"claude-retry: API error on attempt {retry_num}/{MAX_RETRIES} — "
                    f"{error_text[:100]}. "
                    "Please retry your last request."
                ),
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
