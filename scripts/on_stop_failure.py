#!/usr/bin/env python3
"""
claude-retry — StopFailure hook
"""
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import state as st

BASE_DELAY = float(os.environ.get("CLAUDE_RETRY_DELAY", "5"))
BACKOFF = float(os.environ.get("CLAUDE_RETRY_BACKOFF", "2"))
MAX_DELAY = float(os.environ.get("CLAUDE_RETRY_MAX_DELAY", "120"))
MAX_RETRIES = int(os.environ.get("CLAUDE_RETRY_MAX_RETRIES", "0"))

cmd = b"\x1b[A\n"


def _backoff(attempt: int) -> float:
    return min(BASE_DELAY * (BACKOFF ** (attempt - 1)), MAX_DELAY)


def _find_claude_pid() -> int | None:
    pid = os.getpid()
    for _ in range(10):
        try:
            out = subprocess.check_output(
                ["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            break
        parts = out.split(None, 1)
        if len(parts) < 2:
            break
        ppid = int(parts[0])
        comm = parts[1]
        if ppid <= 1:
            break
        if "claude" in comm.lower():
            return ppid
        pid = ppid
    return None


def _stdin_fd_path(pid: int) -> str | None:
    p = Path(f"/proc/{pid}/fd/0")
    if p.exists():
        return str(p)
    try:
        out = subprocess.check_output(
            ["lsof", "-a", "-p", str(pid), "-d", "0", "-Fn"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            if line.startswith("n"):
                path = line[1:].strip()
                if path and Path(path).exists():
                    return path
    except Exception:
        pass
    return None


def _inject_enter() -> bool:
    claude_pid = _find_claude_pid()
    if claude_pid:
        fd_path = _stdin_fd_path(claude_pid)
        if fd_path:
            try:
                with open(fd_path, "wb") as f:
                    f.write(cmd)
                st.log(f"wrote cmd to {fd_path} (pid={claude_pid}) ✓")
                return True
            except Exception as e:
                st.log(f"write fd failed: {e}")

    try:
        tty = subprocess.check_output(
            ["tty"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        tty = None

    if tty and tty != "not a tty" and Path(tty).exists():
        try:
            with open(tty, "wb") as f:
                f.write(cmd)
            st.log(f"wrote cmd to tty {tty} ✓")
            return True
        except Exception as e:
            st.log(f"tty write failed: {e}")

        try:
            TIOCSTI = 0x5412 if sys.platform != "darwin" else 0x80017472
            with open(tty, "rb") as f:
                fcntl.ioctl(f, TIOCSTI, cmd)
            st.log(f"TIOCSTI → {tty} ✓")
            return True
        except Exception as e:
            st.log(f"TIOCSTI failed: {e}")

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

    if not _inject_enter():
        st.log("WARNING: all inject methods failed")


if __name__ == "__main__":
    main()
