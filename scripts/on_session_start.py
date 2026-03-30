#!/usr/bin/env python3
"""SessionStart hook — resets per-session retry counters."""
import json, sys, os

sys.path.insert(0, os.path.dirname(__file__))
import state

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

session_id = data.get("session_id", "unknown")
state.record_session_start(session_id)
state.log(f"Session started: {session_id}")
