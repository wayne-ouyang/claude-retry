# claude-retry

A Claude Code plugin that automatically retries on API errors with exponential backoff.

No wrapper script needed — hooks directly into Claude Code's event system. When Claude Code hits an API error (overloaded, rate limit, network timeout, etc.), this plugin catches the failure, waits with exponential backoff, and injects a keypress to resume the conversation automatically. You walk away, and it keeps going.

> **Requires tmux** — the plugin uses tmux's `send-keys` to inject keypresses. Claude Code must be running inside a tmux session.

## Setup

Install tmux if needed:

```bash
# macOS
brew install tmux

# Debian / Ubuntu
sudo apt install tmux
```

Then start a tmux session and launch Claude inside it:

```bash
tmux new -s claude
claude
```

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

The plugin activates automatically on your next session. To activate it in the current session without restarting, run:

```
/reload-plugins
```

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
2. **StopFailure** — on API failure, records the error, sleeps with exponential backoff, then injects `\n` via tmux `send-keys` to trigger a retry

State is persisted to `~/.claude/claude-retry/state.json`, and failures are logged to `failures.jsonl` in the same directory.

## Requirements

- Python 3 (stdlib only, no external dependencies)
- tmux
- macOS or Linux

## Configuration

All settings are optional environment variables. Add them to your shell profile (e.g. `~/.zshrc`) to persist:

| Variable                   | Default | Description                                  |
| -------------------------- | ------- | -------------------------------------------- |
| `CLAUDE_RETRY_DELAY`       | `5`     | Base delay in seconds                        |
| `CLAUDE_RETRY_BACKOFF`     | `2`     | Backoff multiplier                           |
| `CLAUDE_RETRY_MAX_DELAY`   | `120`   | Maximum delay cap in seconds                 |
| `CLAUDE_RETRY_MAX_RETRIES` | `0`     | Max retries before giving up (0 = unlimited) |
| `CLAUDE_RETRY_TEXT`        | `retry` | Custom text to input on retry                |

Example:

```bash
export CLAUDE_RETRY_DELAY=10
export CLAUDE_RETRY_MAX_DELAY=60
export CLAUDE_RETRY_MAX_RETRIES=5
export CLAUDE_RETRY_TEXT="retry"
```

## License

MIT
