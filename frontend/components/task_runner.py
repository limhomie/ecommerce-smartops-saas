"""Shared background task runner for Streamlit pages.

Provides a thread-safe store so LLM tasks keep running when users switch pages.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_tasks: dict[str, dict] = {}


def status(key: str) -> dict:
    with _lock:
        return _tasks.get(key, {}).copy()


def update(key: str, **kw):
    with _lock:
        if key not in _tasks:
            _tasks[key] = {}
        _tasks[key].update(kw)


def pending(key: str) -> bool:
    return status(key).get("status") == "running"


def launch(key: str, fn, *args):
    """Start fn(*args) in background. fn should call update() to report results."""
    update(key, status="running", progress=[], result=None, error=None)
    threading.Thread(target=_wrap, args=(key, fn, args), daemon=True).start()


def _wrap(key: str, fn, args: tuple):
    t0 = time.time()
    def log(msg: str):
        with _lock:
            if key in _tasks:
                _tasks[key].setdefault("progress", []).append(msg)
    try:
        result = fn(*args, log=log)
        update(key, status="done", result=result)
    except Exception as e:
        import traceback
        update(key, status="error", error=f"{e}\n{traceback.format_exc()}")
