"""Structured developer log: one JSON object per line in data/devlog.jsonl.

Everything the app does lands here in a machine- and human-readable form so it
can be read back later to diagnose problems, spot hidden issues, and flag
inconsistencies. Event kinds you'll see:

  search_start / search_end   a full search run and its outcome
  provider_health             which flight sources were reachable
  bot_action                  a button tap or command in the Telegram bot
  bot_search_launch / _done / _error   a group search from the bot
  result                      a saved/updated deal
  flag                        a raised concern worth reviewing
  log                         every log_info / log_warning / log_error line

Fully fail-soft: writing the dev log must never crash the app.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime

_PATH = os.path.join("data", "devlog.jsonl")
_LOCK = threading.Lock()
_MAX_BYTES = 5 * 1024 * 1024      # cap the file
_KEEP_LINES = 4000                # after the cap, keep the most recent lines


def _rotate_if_big() -> None:
    try:
        if os.path.exists(_PATH) and os.path.getsize(_PATH) > _MAX_BYTES:
            with open(_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines[-_KEEP_LINES:])
    except Exception:
        pass


def event(kind: str, msg: str = "", **fields) -> None:
    """Append one structured event. Extra keyword fields are stored as-is
    (anything not JSON-serializable is stringified)."""
    try:
        os.makedirs("data", exist_ok=True)
        rec = {"ts": datetime.now().isoformat(timespec="seconds"), "kind": kind}
        if msg:
            rec["msg"] = msg
        for k, v in fields.items():
            try:
                json.dumps(v)
                rec[k] = v
            except Exception:
                rec[k] = str(v)
        line = json.dumps(rec, ensure_ascii=False)
        with _LOCK:
            with open(_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            _rotate_if_big()
    except Exception:
        pass  # logging must never break the app


def flag(msg: str, **fields) -> None:
    """Record a concern / possible inconsistency to review later."""
    event("flag", msg, **fields)


def tail(n: int = 200) -> str:
    """Return the last n lines (handy for a quick read)."""
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""
