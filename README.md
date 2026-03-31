# claude-retry

A Claude Code plugin that automatically retries on API errors with exponential backoff.

No wrapper script needed — hooks directly into Claude Code's event system. When Claude Code hits an API error (overloaded, rate limit, network timeout, etc.), this plugin catches the failure, waits with exponential backoff, and runs a configurable command to resume the conversation automatically. You walk away, and it keeps going.

> **Requires tmux** — the default retry injection command targets the current tmux pane. Claude Code must be running inside a tmux session.

## Setup

Install tmux if needed:

```bash
# macOS
brew install tmux

# Debian / Ubuntu
sudo apt install tmux
```

Enable mouse support (for scroll wheel, click to select pane, etc.):

```bash
tmux set -g mouse on
```

Or add it to `~/.tmux.conf` to persist across sessions:

```bash
echo 'set -g mouse on' >> ~/.tmux.conf
```

Then start a tmux session and launch Claude inside it:

```bash
# start a tmux session
tmux

# run claude code
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
2. **StopFailure** — on API failure, records the error, sleeps with exponential backoff, then runs a configurable inject command to trigger a retry

State is persisted to `~/.claude/claude-retry/state.json`, and failures are logged to `failures.jsonl` in the same directory.

## Requirements

- Python 3 (stdlib only, no external dependencies)
- tmux
- macOS or Linux

## Configuration

All settings are optional environment variables. Add them to your shell profile (e.g. `~/.zshrc`) to persist:

| Variable                      | Default                                                                            | Description                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `CLAUDE_RETRY_DELAY`          | `5`                                                                                | Base delay in seconds                                             |
| `CLAUDE_RETRY_BACKOFF`        | `2`                                                                                | Backoff multiplier                                                |
| `CLAUDE_RETRY_MAX_DELAY`      | `120`                                                                              | Maximum delay cap in seconds                                      |
| `CLAUDE_RETRY_MAX_RETRIES`    | `0`                                                                                | Max retries before giving up (0 = unlimited)                      |
| `CLAUDE_RETRY_INJECT_COMMAND` | `tmux send-keys -t {pane_id} Up && sleep 0.2 && tmux send-keys -t {pane_id} Enter` | Full command template used to trigger retry; supports `{pane_id}` |

Example:

```bash
export CLAUDE_RETRY_DELAY=10
export CLAUDE_RETRY_MAX_DELAY=60
export CLAUDE_RETRY_MAX_RETRIES=5
export CLAUDE_RETRY_INJECT_COMMAND="tmux send-keys -t {pane_id} Up && sleep 0.2 && tmux send-keys -t {pane_id} Enter"
```

## License

MIT
