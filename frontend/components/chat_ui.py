"""Chat UI — multi-agent with background execution. Switch pages freely."""

from __future__ import annotations

import json
import sys
import os
import time
import threading

import streamlit as st
import httpx

# ── Fix import path at module level (before any threads) ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

from langchain_core.messages import HumanMessage
from config.settings import Settings
from src.llm import set_llm
from src.llm.factory import create_llm_from_settings
from src.agent.supervisor.planner import plan_task
from src.agent.graph import build_graph

# ── Thread-safe task store ──
_lock = threading.Lock()
_pending: dict[str, dict] = {}


def _task_read(sid: str) -> dict:
    with _lock:
        return _pending.get(sid, {}).copy()


def _task_write(sid: str, **kw):
    with _lock:
        if sid not in _pending:
            _pending[sid] = {}
        _pending[sid].update(kw)


def _init_llm():
    s = Settings()
    llm = create_llm_from_settings(s)
    set_llm(llm)
    return llm, s


def render_chat(api_url: str):
    st.subheader("Agent 对话")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

    sid = st.session_state.session_id
    task = _task_read(sid)

    # ── History (with scroll anchors on user messages) ──
    user_anchors: list[tuple[str, str]] = []  # (anchor_id, preview_text)
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                anchor = f"chat_msg_{i}"
                st.markdown(
                    f'<div id="{anchor}" style="scroll-margin-top:80px;height:0"></div>',
                    unsafe_allow_html=True,
                )
                preview = msg["content"][:35] + ("…" if len(msg["content"]) > 35 else "")
                user_anchors.append((anchor, preview))
            st.markdown(msg["content"])
            if msg.get("charts"):
                cols = st.columns(min(len(msg["charts"]), 2))
                for ci, cs in enumerate(msg["charts"]):
                    with cols[ci % 2]:
                        try:
                            st.plotly_chart(cs, use_container_width=True,
                                          key=f"h_{i}_{ci}_{abs(hash(msg['content']))%100000}")
                        except Exception:
                            pass

    # ── Auto-scroll to bottom + hover context panel ──
    _inject_scroll_to_bottom()
    if user_anchors:
        _render_context_panel(user_anchors)

    # ── Running? ──
    if task.get("status") == "running":
        prog = task.get("progress", [])
        with st.chat_message("assistant"):
            with st.container():
                st.info("Agent 正在后台执行... 可以切换页面，不会中断。")
                if prog:
                    with st.expander("实时进度", expanded=True):
                        for line in prog[-10:]:
                            st.caption(line)
        time.sleep(1.5)
        st.rerun()

    # ── Done? ──
    if task.get("status") == "done":
        result = task.get("result", {})
        _task_write(sid, status="delivered")

        report = result.get("final_report", "") or result.get("generated_content", "")
        charts = result.get("charts", [])
        actions = result.get("action_items", [])

        with st.chat_message("assistant"):
            if report:
                st.markdown(report)
            if charts:
                st.divider()
                st.subheader("数据可视化")
                cc = st.columns(min(len(charts), 2))
                for i, cs in enumerate(charts):
                    with cc[i % 2]:
                        try:
                            st.plotly_chart(cs, use_container_width=True, key=f"rc_{i}_{time.time()}")
                        except Exception as e:
                            st.caption(f"图表 {i+1}: {e}")
            if actions:
                with st.expander("行动建议"):
                    for a in actions:
                        st.markdown(f"- {a}")
            st.caption(f"耗时: {result.get('_elapsed', '?')}")

        st.session_state.messages.append({"role": "assistant", "content": report, "charts": charts})
        st.rerun()

    # ── Error? ──
    if task.get("status") == "error":
        err = task.get("error", "未知")
        _task_write(sid, status="delivered")
        with st.chat_message("assistant"):
            st.error(f"执行出错: {err[:500]}")
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {err[:200]}"})
        st.rerun()

    # ── Input ──
    running = task.get("status") == "running"

    st.caption("快速指令：")
    cols = st.columns(3)
    presets = [
        "帮我分析上周转化率为什么下降",
        "为有机棉T恤生成Facebook广告脚本",
        "查询包裹 YT202506130001 的物流状态",
    ]
    triggered = None
    for i, p in enumerate(presets):
        if cols[i].button(p, key=f"pre_{i}", use_container_width=True, disabled=running):
            triggered = p

    user_input = st.chat_input("输入您的运营需求...", disabled=running)
    if triggered:
        user_input = triggered

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        _task_write(sid, status="running", progress=[], result=None, error=None)
        threading.Thread(target=_run_agent, args=(user_input, sid), daemon=True).start()
        st.rerun()


def _run_agent(user_input: str, sid: str):
    t0 = time.time()

    def log(msg: str):
        with _lock:
            if sid in _pending:
                _pending[sid].setdefault("progress", []).append(msg)

    try:
        llm, settings = _init_llm()
        log(f"[{time.time()-t0:.0f}s] 模型: {settings.llm_provider}/{settings.llm_model} 开始拆解任务...")

        result = plan_task({"task_description": user_input}, llm)
        subtasks = result.get("subtasks", [])

        for s in subtasks:
            log(f"  → {s.get('agent','?').replace('_',' ')}: {s.get('description','')[:80]}")

        graph = build_graph()
        init = {
            "messages": [HumanMessage(content=user_input)],
            "user_id": "local", "session_id": sid,
            "task_description": user_input,
            "subtasks": subtasks, "current_task_index": 0,
            "tool_results": {}, "generated_content": "",
            "final_report": "", "action_items": [],
            "step_count": 0, "charts": [], "error": "", "next_agent": "",
            "cache_hit": False,
        }
        cfg = {"configurable": {"thread_id": sid}, "recursion_limit": 12}

        final: dict = {}
        all_charts = []

        for event in graph.stream(init, cfg):
            for node_name, node_out in event.items():
                label = _nl(node_name, node_out)
                log(f"[{time.time()-t0:.0f}s] {label}")
                if node_out and "charts" in node_out:
                    all_charts.extend(node_out["charts"])
                if node_out:
                    final.update(node_out)

        final["charts"] = all_charts
        final["_elapsed"] = f"{time.time()-t0:.0f}秒"
        _task_write(sid, status="done", result=final)

    except Exception as e:
        import traceback
        _task_write(sid, status="error", error=f"{e}\n{traceback.format_exc()}")


def _inject_scroll_to_bottom() -> None:
    """Auto-scroll the chat viewport to the bottom on page load."""
    st.markdown(
        """
        <script>
        (function() {
            const el = window.parent.document.querySelector(
                '.stMain [data-testid="stVerticalBlock"]'
            );
            if (el) el.scrollTop = el.scrollHeight;
            // Also try window scroll as fallback
            setTimeout(function() {
                window.scrollTo(0, document.body.scrollHeight);
            }, 100);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def _render_context_panel(anchors: list[tuple[str, str]]) -> None:
    """Right-side floating panel — collapsed bar, expands on hover with
    clickable user-question shortcuts that jump to the corresponding
    message anchor.
    """
    items_html = ""
    for anchor_id, preview in anchors:
        safe_preview = preview.replace("'", "\\'").replace('"', "&quot;")
        items_html += (
            f'<a class="ctx-item" href="#{anchor_id}" '
            f'title="{safe_preview}">{preview}</a>'
        )

    st.markdown(
        f"""
        <style>
        html {{ scroll-behavior: smooth; }}
        .ctx-panel {{
            position: fixed;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 8px;
            max-height: 60vh;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px 0 0 4px;
            transition: width 0.25s ease, padding 0.25s ease, box-shadow 0.25s ease;
            overflow: hidden;
            z-index: 9999;
            cursor: pointer;
        }}
        .ctx-panel:hover {{
            width: 220px;
            padding: 10px 12px;
            background: #ffffff;
            box-shadow: -4px 0 20px rgba(0,0,0,0.12);
            border: 1px solid #e8e8e8;
            border-right: none;
            overflow-y: auto;
        }}
        .ctx-panel::before {{
            content: "◀";
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 10px;
            transition: opacity 0.15s ease;
        }}
        .ctx-panel:hover::before {{
            opacity: 0;
        }}
        .ctx-item {{
            display: block;
            padding: 7px 10px;
            font-size: 13px;
            color: #333 !important;
            text-decoration: none !important;
            cursor: pointer;
            border-radius: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            transition: background 0.15s;
        }}
        .ctx-item:hover {{
            background: #f0f2ff;
            color: #1a1a1a;
        }}
        .ctx-panel:hover .ctx-header {{
            display: block;
        }}
        .ctx-header {{
            display: none;
            font-size: 12px;
            color: #999;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid #eee;
        }}
        </style>
        <div class="ctx-panel">
            <div class="ctx-header">📋 对话上下文</div>
            {items_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _nl(node_name: str, _output: dict) -> str:
    return {
        "planner": "拆解任务",
        "advance": "下一步",
        "conversion_analyst": "分析转化率和流量数据",
        "competitor_analyst": "搜索竞品价格和促销",
        "sentiment_analyst": "分析社交媒体舆情",
        "content_factory": "生成产品文案和广告素材",
        "sop_executor": "执行自动化流程",
        "report_generator": "汇总生成分析报告",
        "check_cache": "查询缓存",
        "write_cache": "写入缓存",
    }.get(node_name, f"执行: {node_name}")
