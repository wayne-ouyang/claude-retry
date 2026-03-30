#!/usr/bin/env python3
"""SessionStart hook — resets per-session retry counters."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import state

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

state.record_session_start(data.get("session_id", "unknown"))
