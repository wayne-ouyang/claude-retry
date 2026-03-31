#!/usr/bin/env python3
"""
claude-retry — StopFailure hook
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import state as st

BASE_DELAY = float(os.environ.get("CLAUDE_RETRY_DELAY", "5"))
BACKOFF = float(os.environ.get("CLAUDE_RETRY_BACKOFF", "2"))
MAX_DELAY = float(os.environ.get("CLAUDE_RETRY_MAX_DELAY", "120"))
MAX_RETRIES = int(os.environ.get("CLAUDE_RETRY_MAX_RETRIES", "0"))
INJECT_COMMAND_TEMPLATE = os.environ.get(
    "CLAUDE_RETRY_INJECT_COMMAND",
    "tmux send-keys -t {pane_id} Up && sleep 0.2 && tmux send-keys -t {pane_id} Enter",
)


def _backoff(attempt: int) -> float:
    """
    第一次 attempt=1 时直接返回 0，后续按指数退避
    """
    if attempt <= 1:
        return 0
    return min(BASE_DELAY * (BACKOFF ** (attempt - 2)), MAX_DELAY)


def _inject_retry() -> bool:
    """
    执行可配置的重试注入命令。
    默认等价于:
    tmux send-keys -t <current-pane> Up && sleep 0.2 && tmux send-keys -t <current-pane> Enter
    """
    try:
        pane_id = subprocess.check_output(
            ["tmux", "display-message", "-p", "#{pane_id}"],
            text=True,
        ).strip()
        inject_command = INJECT_COMMAND_TEMPLATE.format(pane_id=pane_id)
        subprocess.run(inject_command, shell=True, check=True)
        st.log(f"inject command -> pane {pane_id}: {inject_command!r} ✓")
        return True
    except Exception as e:
        st.log(f"inject command failed: {e}")
    return False


def main():
    st.log("StopFailure hook triggered")
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    error = data.get("error", "unknown")
    error_detail = data.get("error_details", "")
    full_error = f"{error}: {error_detail}" if error_detail else error

    new_state = st.record_failure(session_id, full_error)
    retry_num = new_state["retry_count"]

    if MAX_RETRIES > 0 and retry_num > MAX_RETRIES:
        st.reset_retries(session_id)
        retry_num = 1

    delay = _backoff(retry_num)
    st.log(f"#{retry_num} error={error} delay={delay:.0f}s session={session_id}")
    time.sleep(delay)

    if not _inject_retry():
        st.log("WARNING: inject methods failed")


if __name__ == "__main__":
    main()
