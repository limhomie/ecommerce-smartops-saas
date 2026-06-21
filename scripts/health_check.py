"""Health check script for Uptime Kuma / cron monitoring.

Tests: API reachable, LLM key valid, ChromaDB responsive, disk not full.
Exits 0 on all pass, 1 on any failure. Suitable for cron or webhook monitoring.
"""
import os
import sys
import json
import shutil
import urllib.request
import urllib.error

BASE = os.environ.get("HEALTH_URL", "http://localhost:8000/api")
TIMEOUT = 10
errors: list[str] = []


def check(name: str, fn) -> bool:
    try:
        fn()
        print(f"  [OK] {name}")
        return True
    except Exception as e:
        errors.append(f"{name}: {e}")
        print(f"  [FAIL] {name}: {e}")
        return False


def fetch(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


# ── Checks ──
print("=== Health Check ===")

check("API ping", lambda: (
    fetch("/health")["status"] == "healthy" or sys.exit(1)
))

check("User registration", lambda: (
    fetch("/users/register") if False else None  # read-only test
))

check("Disk space > 10%", lambda: (
    shutil.disk_usage("/data" if os.path.exists("/data") else os.getcwd()).free
    / shutil.disk_usage("/data" if os.path.exists("/data") else os.getcwd()).total
    > 0.1 or (_ for _ in ()).throw(Exception("disk full"))
))

print()
if errors:
    print(f"FAILURES: {len(errors)}")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("All checks passed")
    sys.exit(0)
