#!/usr/bin/env python3
"""
retry-guardian statusline — reads Status JSON from stdin, prints one ANSI line.

✦ Opus 4.5  ██████░░░░ 58%  $0.23  ⏱ 2m14s  my-project  ⎇ main  ✓ healthy
✦ Opus 4.5  ████████░░ 79%  $1.42  ⏱ 8m02s  my-project  ⎇ main  ↺ retry #2 — overloaded_error
✦ Opus 4.5  ██████░░░░ 58%  $1.43  ⏱ 8m14s  my-project  ⎇ main  ✓ recovered (2 retries)
"""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
try:
    import state as _sm; _st = _sm.load()
except Exception:
    _st = {"status": "idle", "retry_count": 0, "last_failure_ts": None,
           "last_failure_error": None, "total_failures_session": 0}

def _c(code, t): return f"\033[{code}m{t}\033[0m"
def bold(t):  return _c("1", t)
def dim(t):   return _c("2", t)
def green(t): return _c("32", t)
def yellow(t):return _c("33", t)
def red(t):   return _c("31", t)
def cyan(t):  return _c("36", t)
def blue(t):  return _c("34", t)
def orange(t):return _c("38;5;208", t)

def ctx_bar(pct):
    filled = round(pct / 100 * 10)
    bar = "█" * filled + "░" * (10 - filled)
    col = green if pct < 50 else (yellow if pct < 80 else red)
    return f"{col(bar)} {col(f'{pct:.0f}%')}"

def ago(ts):
    if not ts: return ""
    d = int(time.time() - ts)
    return f"{d}s ago" if d < 60 else f"{d//60}m ago"

def git_branch():
    try:
        r = subprocess.run(["git","branch","--show-current"],
                           capture_output=True, text=True, timeout=1)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception: return ""

def dur(ms):
    if not ms: return ""
    s = int(ms/1000)
    return f"{s}s" if s < 60 else f"{s//60}m{s%60:02d}s"

def retry_seg():
    status = _st.get("status", "idle")
    count  = _st.get("retry_count", 0)
    err    = (_st.get("last_failure_error") or "").split(":")[0][:30]
    total  = _st.get("total_failures_session", 0)
    ts     = _st.get("last_failure_ts")

    if status in ("idle",) and count == 0:
        return green("✓ healthy")
    if status == "retrying":
        parts = [yellow(f"↺ retry #{count}")]
        if err: parts.append(dim(f"— {err}"))
        if ts:  parts.append(dim(f"({ago(ts)})"))
        return " ".join(parts)
    if status == "recovered":
        suf = dim(f" ({total} retries)") if total else ""
        return green("✓ recovered") + suf
    if status == "gave_up":
        return red(f"✗ gave up after {total} retries")
    return green("✓ healthy")

def main():
    try: data = json.load(sys.stdin)
    except Exception: data = {}

    model   = (data.get("model") or {}).get("display_name") or "Claude"
    ws      = data.get("workspace") or {}
    cwd     = os.path.basename(ws.get("current_dir") or os.getcwd()) or "."
    cost_d  = data.get("cost") or {}
    cost    = cost_d.get("total_cost_usd") or 0.0
    dur_ms  = cost_d.get("total_duration_ms") or 0
    ctx_pct = (data.get("context_window") or {}).get("used_percentage") or 0.0

    sep    = dim(" │ ")
    branch = git_branch()
    d      = dur(dur_ms)

    parts = [bold(orange(f"✦ {model}")), ctx_bar(ctx_pct), cyan(f"${cost:.2f}")]
    if d:      parts.append(dim(f"⏱ {d}"))
    parts.append(dim(cwd))
    if branch: parts.append(blue(f"⎇ {branch}"))
    parts.append(retry_seg())
    print(sep.join(parts))

if __name__ == "__main__":
    main()
