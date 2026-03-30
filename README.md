# ⚡ retry-guardian

> A Claude Code plugin that automatically retries on API errors — no wrapper script needed. Just install and it works inside every Claude Code session.

```
✦ Opus 4.5  ██████░░░░ 58%  $0.23  ⏱ 2m14s  my-project  ⎇ main  ✓ healthy
✦ Opus 4.5  ████████░░ 79%  $1.42  ⏱ 8m02s  my-project  ⎇ main  ↺ retry #2 — overloaded_error
✦ Opus 4.5  ██████░░░░ 58%  $1.43  ⏱ 8m14s  my-project  ⎇ main  ✓ recovered (2 retries)
```

---

## Install

```
/plugin marketplace add your-username/retry-guardian
/plugin install retry-guardian@retry-guardian
```

Done. No restart needed. The plugin activates immediately.

---

## How it works

The plugin uses the **`Stop` hook** — which fires every time Claude finishes a response. The hook reads the session transcript to detect API error patterns. If one is found, it returns `{"decision": "block"}` to force Claude to retry automatically, with exponential backoff.

```
Claude responds
    ↓
Stop hook fires (on_stop.py)
    ↓
Parse transcript for API error patterns
    ├── No error  → exit 0  (Claude stops normally)
    └── Error found
            ↓
        Check retry count
            ├── Under limit → sleep(backoff) → {"decision": "block", "reason": "retry now"}
            │                                        ↓
            │                              Claude retries automatically
            └── Over limit  → block with "gave up" message
```

The `stop_hook_active` flag (set by Claude Code when a Stop hook has already blocked once) is always checked first to prevent infinite loops.

---

## What the HUD shows

| Segment | Description |
|---------|-------------|
| `✦ Opus 4.5` | Current model |
| `██████░░░░ 58%` | Context window — green → yellow → red |
| `$0.23` | Running session cost |
| `⏱ 2m14s` | Session duration |
| `my-project` | Current directory |
| `⎇ main` | Git branch |
| `✓ healthy` | No errors this session |
| `↺ retry #N — error` | Actively retrying with error hint |
| `✓ recovered (N retries)` | Recovered after N retries |
| `✗ gave up after N retries` | Max retries exceeded |

---

## Configuration

Tune retry behaviour via environment variables before starting Claude Code:

```bash
export GUARDIAN_MAX_RETRIES=5    # default: 5
export GUARDIAN_DELAY=3          # initial backoff delay in seconds (default: 3)
export GUARDIAN_BACKOFF=2        # exponential multiplier (default: 2)
export GUARDIAN_MAX_DELAY=60     # max delay cap in seconds (default: 60)
claude
```

Backoff schedule (defaults): `3s → 6s → 12s → 24s → 48s`

---

## Slash commands

| Command | Description |
|---------|-------------|
| `/retry-guardian:status` | Show current retry state and recent failures |

---

## Logs

```bash
cat ~/.claude/retry-guardian/state.json        # current state
cat ~/.claude/retry-guardian/failures.jsonl    # full failure history
```

---

## Requirements

- Claude Code v1.0.80+
- Python 3.8+
- `git` optional (for branch in HUD)
