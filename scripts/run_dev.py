#!/usr/bin/env python3
"""One-click development environment launcher.

Starts the FastAPI backend and Streamlit frontend.
Run: D:/anaconda/python.exe scripts/run_dev.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    print("=" * 60)
    print("  E-Commerce SmartOps Agent — 开发环境启动")
    print("=" * 60)

    # Start FastAPI backend
    print("\n[1/2] 启动 FastAPI 后端 (http://localhost:8000)...")
    api_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.api.app:create_app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--factory",
        ],
        cwd=str(PROJECT_ROOT),
    )

    time.sleep(2)

    # Start Streamlit frontend
    print("[2/2] 启动 Streamlit 前端 (http://localhost:8501)...")
    streamlit_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            "frontend/app.py",
            "--server.port", "8501",
        ],
        cwd=str(PROJECT_ROOT),
    )

    print("\n" + "=" * 60)
    print("  后端 API:  http://localhost:8000")
    print("  API 文档:  http://localhost:8000/docs")
    print("  前端界面:  http://localhost:8501")
    print("=" * 60)
    print("\n按 Ctrl+C 停止所有服务...\n")

    try:
        api_proc.wait()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        api_proc.terminate()
        streamlit_proc.terminate()
        api_proc.wait()
        streamlit_proc.wait()
        print("已停止。")


if __name__ == "__main__":
    main()
