#!/usr/bin/env python3
"""
claude-retry — StopFailure hook

通用重试：找到 claude 父进程的 stdin fd，直接写入回车。
不依赖 TIOCSTI / osascript / xdotool，Linux + macOS 通用。
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
MAX_RETRIES = int(os.environ.get("CLAUDE_RETRY_MAX_RETRIES", "0"))  # 0 = 永远重试


def _backoff(attempt: int) -> float:
    return min(BASE_DELAY * (BACKOFF ** (attempt - 1)), MAX_DELAY)


def _find_claude_pid() -> int | None:
    """沿父进程链向上找名为 claude 的进程。"""
    pid = os.getpid()
    for _ in range(10):
        try:
            ppid = int(
                subprocess.check_output(
                    ["ps", "-o", "ppid=", "-p", str(pid)],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            )
        except Exception:
            break
        if ppid <= 1:
            break
        try:
            comm = subprocess.check_output(
                ["ps", "-o", "comm=", "-p", str(ppid)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            break
        if "claude" in comm.lower():
            return ppid
        pid = ppid
    return None


def _stdin_fd_path(pid: int) -> str | None:
    """返回进程 stdin 的 fd 路径（/proc 或 /dev/fd 风格）。"""
    # Linux
    p = Path(f"/proc/{pid}/fd/0")
    if p.exists():
        return str(p)
    # macOS: 用 lsof 找 fd 0 对应的设备
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
    """向 claude 进程的 stdin（pty slave）写入回车。"""
    # ── 方法 1：写 claude 父进程的 stdin fd ──────────────────────────
    claude_pid = _find_claude_pid()
    if claude_pid:
        fd_path = _stdin_fd_path(claude_pid)
        if fd_path:
            try:
                with open(fd_path, "wb") as f:
                    f.write(b"1231")
                print(
                    f"[claude-retry] wrote \\n to {fd_path} (pid={claude_pid})",
                    file=sys.stderr,
                )
                return True
            except Exception as e:
                print(f"[claude-retry] write fd failed: {e}", file=sys.stderr)

    # ── 方法 2：写当前进程自己的 tty（hook 和 claude 共享同一 pty）──
    try:
        tty = subprocess.check_output(
            ["tty"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if tty and tty != "not a tty" and Path(tty).exists():
            with open(tty, "wb") as f:
                f.write(b"1231")
            print(f"[claude-retry] wrote \\n to tty {tty}", file=sys.stderr)
            return True
    except Exception as e:
        print(f"[claude-retry] tty write failed: {e}", file=sys.stderr)

    # ── 方法 3：TIOCSTI（Linux / 旧 macOS）───────────────────────────
    try:
        tty = subprocess.check_output(
            ["tty"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if tty and Path(tty).exists():
            TIOCSTI = 0x5412 if sys.platform != "darwin" else 0x80017472
            with open(tty, "rb") as f:
                fcntl.ioctl(f, TIOCSTI, b"1231")
            print(f"[claude-retry] TIOCSTI → {tty}", file=sys.stderr)
            return True
    except Exception as e:
        print(f"[claude-retry] TIOCSTI failed: {e}", file=sys.stderr)

    return False


def main():
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
    print(
        f"[claude-retry] #{retry_num} error={error} — waiting {delay:.0f}s then retrying...",
        file=sys.stderr,
    )
    time.sleep(delay)

    if _inject_enter():
        print("[claude-retry] Enter injected ✓", file=sys.stderr)
    else:
        print("[claude-retry] WARNING: all inject methods failed", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
