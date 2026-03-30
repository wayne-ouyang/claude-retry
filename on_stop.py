#!/usr/bin/env python3
"""
retry-guardian — Stop hook
─────────────────────────────────────────────────────────────────────────────
Fires every time Claude finishes a response (Stop event).

Logic:
  1. If stop_hook_active → we're already in a forced retry, let Claude stop
     (prevents infinite loops).
  2. Parse the transcript JSONL to find the most recent assistant message.
  3. If that message contains an API error pattern → block Stop and tell
     Claude to retry, with exponential backoff.
  4. Otherwise → exit 0 (let Claude stop normally).

State is persisted to ~/.claude/retry-guardian/state.json so the statusline
can reflect retry health in real time.
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
MAX_RETRIES  = int(os.environ.get("GUARDIAN_MAX_RETRIES", "5"))
BASE_DELAY   = float(os.environ.get("GUARDIAN_DELAY", "3"))
BACKOFF      = float(os.environ.get("GUARDIAN_BACKOFF", "2"))
MAX_DELAY    = float(os.environ.get("GUARDIAN_MAX_DELAY", "60"))

# ── API error patterns to detect in transcript ────────────────────────────────
API_ERROR_PATTERNS = [
    r"overloaded_error",
    r"rate.?limit",
    r"529",               # Anthropic overload HTTP status
    r"503",               # Service unavailable
    r"APIError",
    r"api_error",
    r'"error".*"type"',
    r"Request failed",
    r"Connection error",
    r"network.*error",
    r"timeout.*error",
    r"internal_server_error",
]
_ERROR_RE = re.compile("|".join(API_ERROR_PATTERNS), re.IGNORECASE)


def _backoff(attempt: int) -> float:
    return min(BASE_DELAY * (BACKOFF ** (attempt - 1)), MAX_DELAY)


def _detect_api_error_in_transcript(transcript_path: str) -> str | None:
    """
    Read the last few lines of the transcript JSONL.
    Return the error text if an API error is found, else None.
    """
    if not transcript_path:
        return None
    p = Path(transcript_path)
    if not p.exists():
        return None

    # Read last 50 lines (enough to cover the most recent turn)
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        recent = lines[-50:]
    except Exception:
        return None

    # Look for error signals in recent entries
    for raw in reversed(recent):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue

        # Direct error field in entry
        if "error" in entry and entry["error"]:
            err = json.dumps(entry["error"]) if isinstance(entry["error"], dict) else str(entry["error"])
            if _ERROR_RE.search(err):
                return err[:120]

        # Error text inside content blocks
        content = entry.get("content") or entry.get("message") or ""
        if isinstance(content, list):
            content = json.dumps(content)
        if isinstance(content, str) and _ERROR_RE.search(content):
            match = _ERROR_RE.search(content)
            return content[max(0, match.start()-20):match.start()+80]

    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    session_id      = data.get("session_id", "unknown")
    stop_hook_active = data.get("stop_hook_active", False)
    transcript_path  = data.get("transcript_path", "")

    # ── Guard: already retrying, allow stop to break the loop ────────────────
    if stop_hook_active:
        st.record_recovery()
        sys.exit(0)

    # ── Load current state ────────────────────────────────────────────────────
    current = st.load()

    # ── Detect API error in transcript ────────────────────────────────────────
    error_text = _detect_api_error_in_transcript(transcript_path)

    if error_text is None:
        # No error — clean stop, reset state
        if current.get("retry_count", 0) > 0:
            st.record_recovery()
        else:
            st.record_clean_stop(session_id)
        sys.exit(0)

    # ── API error detected ────────────────────────────────────────────────────
    new_state = st.record_failure(session_id, error_text)
    retry_num = new_state["retry_count"]

    if retry_num > MAX_RETRIES:
        # Too many retries — let Claude stop and report
        st.record_gave_up()
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"retry-guardian: Gave up after {MAX_RETRIES} retries. "
                f"Last error: {error_text[:100]}. "
                "Please check your API status or try again later."
            )
        }))
        sys.exit(0)

    delay = _backoff(retry_num)
    time.sleep(delay)

    # Block Stop → Claude will read this reason and retry
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"retry-guardian: API error detected (attempt {retry_num}/{MAX_RETRIES}). "
            f"Error: {error_text[:100]}. "
            f"Please retry your last request now."
        )
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
