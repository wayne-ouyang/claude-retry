# claude-retry

A Claude Code plugin that automatically retries on API errors with exponential backoff.

No wrapper script needed — hooks directly into Claude Code's event system. When Claude Code hits an API error (overloaded, rate limit, network timeout, etc.), this plugin catches the failure, waits with exponential backoff, and injects a keypress to resume the conversation automatically. You walk away, and it keeps going.

## Install

Inside a Claude Code instance, run the following commands:

**Step 1: Add the marketplace**

```
/plugin marketplace add wayne-ouyang/claude-retry
```

**Step 2: Install the plugin**

```
/plugin install claude-retry
```

The plugin activates automatically on your next session.

To verify it's installed:

```
/plugin list
```

To uninstall:

```
/plugin remove claude-retry
```

## How It Works

The plugin registers two hooks:

1. **SessionStart** — resets retry counters when a new session begins
2. **StopFailure** — on API failure, records the error, sleeps with exponential backoff, then injects `\n` into Claude's stdin to trigger a retry

The enter-injection tries three methods in order:
- Write to Claude's PID fd/0 (found via process tree + lsof)
- Write to TTY
- TIOCSTI ioctl fallback

State is persisted to `~/.claude/claude-retry/state.json`, and failures are logged to `failures.jsonl` in the same directory.

## Configuration

All settings are optional environment variables. Add them to your shell profile (e.g. `~/.zshrc`) to persist:

| Variable | Default | Description |
|---|---|---|
| `CLAUDE_RETRY_DELAY` | `5` | Base delay in seconds |
| `CLAUDE_RETRY_BACKOFF` | `2` | Backoff multiplier |
| `CLAUDE_RETRY_MAX_DELAY` | `120` | Maximum delay cap in seconds |
| `CLAUDE_RETRY_MAX_RETRIES` | `0` | Max retries before giving up (0 = unlimited) |

Example:

```bash
export CLAUDE_RETRY_DELAY=10
export CLAUDE_RETRY_MAX_DELAY=60
export CLAUDE_RETRY_MAX_RETRIES=5
```

## Requirements

- Python 3 (stdlib only, no external dependencies)
- macOS or Linux

## License

MIT
