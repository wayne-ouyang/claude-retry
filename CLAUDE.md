# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-retry** is a Claude Code plugin that automatically retries on API errors via the `StopFailure` hook with exponential backoff. No wrapper script needed — hooks directly into Claude Code's event system.

## Architecture

Two hook handlers plus shared state:

- **SessionStart** (`scripts/on_session_start.py`) — resets retry counters
- **StopFailure** (`scripts/on_stop_failure.py`) — records failure, sleeps with exponential backoff, then runs `tmux send-keys` with configurable arguments to trigger retry
- **State** (`scripts/state.py`) — persists to `~/.claude/claude-retry/state.json`, logs failures to `failures.jsonl`

### Config (env vars)

- `CLAUDE_RETRY_DELAY` — base delay seconds (default: 5)
- `CLAUDE_RETRY_BACKOFF` — multiplier (default: 2)
- `CLAUDE_RETRY_MAX_DELAY` — cap seconds (default: 120)
- `CLAUDE_RETRY_MAX_RETRIES` — max before reset (default: 0 = unlimited)
- `CLAUDE_RETRY_SEND_KEYS` — arguments for `tmux send-keys` after the internally added target pane (default: `retry Enter`)

### Plugin Registration

- `.claude-plugin/plugin.json` — plugin identity
- `.claude-plugin/marketplace.json` — marketplace listing
- `hooks/hooks.json` — hook event bindings (uses `$CLAUDE_PLUGIN_DIR`)

## Running Scripts

```bash
echo '{"session_id":"test"}' | python3 scripts/on_session_start.py
echo '{"session_id":"test","error":"overloaded"}' | python3 scripts/on_stop_failure.py
```

Python 3 stdlib only — no external dependencies.
