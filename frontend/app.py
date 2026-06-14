"""E-Commerce SmartOps Agent — Streamlit entry point.

Run: streamlit run frontend/app.py
"""

from __future__ import annotations

import sys, os, random, hashlib, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])

import streamlit as st

st.set_page_config(
    page_title="E-Commerce SmartOps Agent",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init ──
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# ── Header ──
st.title("E-Commerce SmartOps Agent")
st.caption("电商智能体运营系统 — 数据分析 · 竞品监控 · 内容工厂 · 自动化 SOP · 知识库 RAG")

# ── System status bar ──
try:
    from config.settings import Settings as _S
    _settings = _S()
    llm_status = f"{_settings.llm_provider}/{_settings.llm_model}"
except Exception:
    llm_status = "mock"

try:
    from src.memory.vector_store import VectorStore
    from src.memory.long_term import LongTermMemory
    _ltm = LongTermMemory(VectorStore(_S()))
    _stats = _ltm.get_stats()
    kb_total = sum(_stats.values())
    kb_status = f"{kb_total} 块 · {len(_stats)} 库"
except Exception:
    kb_status = "离线"

s1, s2, s3, s4 = st.columns(4)
s1.caption(f"LLM: {llm_status}")
s2.caption(f"知识库: {kb_status}")
s3.caption("引擎: LangGraph + ChromaDB")
s4.caption("前端: Streamlit")

# ── Period selector + dynamic metrics ──
PERIOD_DATA = {
    "本周": {"conversion": 2.1, "prev": 3.4, "aov": 45.60, "prev_aov": 43.30,
             "orders": 534, "prev_orders": 623, "visitors": 25430, "prev_visitors": 24200},
    "上周": {"conversion": 3.4, "prev": 3.1, "aov": 43.30, "prev_aov": 44.10,
             "orders": 623, "prev_orders": 580, "visitors": 18320, "prev_visitors": 18700},
    "本月": {"conversion": 2.7, "prev": 2.9, "aov": 44.80, "prev_aov": 43.90,
             "orders": 2150, "prev_orders": 2300, "visitors": 79600, "prev_visitors": 79300},
}

def _make_custom(start: dt.date, end: dt.date) -> dict:
    days = (end - start).days + 1
    seed = int(hashlib.md5(f"{start}{end}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    base_conv = round(rng.uniform(2.0, 3.5), 1)
    base_aov = round(rng.uniform(40, 50), 2)
    base_ord = int(rng.uniform(50, 120)) * days
    base_vis = int(rng.uniform(2000, 5000)) * days
    return {"conversion": base_conv, "prev": round(base_conv+rng.uniform(-0.5,1.0),1),
            "aov": base_aov, "prev_aov": round(base_aov+rng.uniform(-3,3),2),
            "orders": base_ord, "prev_orders": int(base_ord*rng.uniform(0.85,1.2)),
            "visitors": base_vis, "prev_visitors": int(base_vis*rng.uniform(0.8,1.1))}

c1, c2 = st.columns([1, 5])
with c1:
    period = st.selectbox("时间范围", ["本周", "上周", "本月", "自定义"], label_visibility="collapsed")
if period == "自定义":
    c_a, c_b = st.columns(2)
    with c_a: sd = st.date_input("开始", dt.date.today()-dt.timedelta(7), label_visibility="collapsed")
    with c_b: ed = st.date_input("结束", dt.date.today(), label_visibility="collapsed")
    d = _make_custom(sd, ed)
else:
    d = PERIOD_DATA.get(period, PERIOD_DATA["本周"])

def _d(cur, prev, unit=""):
    diff = cur - prev
    pct = round(diff/prev*100, 1) if prev else 0
    arrow = "↑" if diff > 0 else "↓" if diff < 0 else ""
    return f"{arrow} {abs(pct)}%" if not unit else f"{arrow} {abs(diff)}{unit}"

def _color(cur, prev, inverse=False):
    up = cur >= prev
    return "normal" if (up and not inverse) or (not up and inverse) else "inverse"

m1, m2, m3, m4 = st.columns(4)
m1.metric("转化率", f"{d['conversion']}%", _d(d["conversion"], d["prev"]),
          delta_color=_color(d["conversion"], d["prev"]))
m2.metric("客单价", f"${d['aov']:.2f}", _d(d["aov"], d["prev_aov"]),
          delta_color=_color(d["aov"], d["prev_aov"]))
m3.metric(f"{period}订单", f"{d['orders']:,}", _d(d["orders"], d["prev_orders"], unit="单"),
          delta_color=_color(d["orders"], d["prev_orders"]))
m4.metric(f"{period}访客", f"{d['visitors']:,}", _d(d["visitors"], d["prev_visitors"], unit="人"),
          delta_color="normal")

st.divider()

# ── Quick actions ──
st.subheader("快速操作")

q1, q2, q3, q4 = st.columns(4)

with q1:
    with st.container(border=True):
        st.markdown("📊 **数据诊断**")
        st.caption("Agent 分析运营异常")
        if st.button("去诊断", use_container_width=True):
            st.switch_page("pages/02_chat.py")

with q2:
    with st.container(border=True):
        st.markdown("✍️ **内容工厂**")
        st.caption("AI 生成文案/广告/SEO")
        if st.button("去生成", use_container_width=True):
            st.switch_page("pages/03_content.py")

with q3:
    with st.container(border=True):
        st.markdown("📋 **分析报告**")
        st.caption("AI 自动生成运营报告")
        if st.button("去报告", use_container_width=True):
            st.switch_page("pages/05_reports.py")

with q4:
    with st.container(border=True):
        st.markdown("📚 **知识库**")
        st.caption("搜索/上传/同步竞品数据")
        if st.button("去知识库", use_container_width=True):
            st.switch_page("pages/04_knowledge.py")

st.divider()

# ── System overview ──
st.subheader("系统架构")

tab_a, tab_b = st.tabs(["架构图", "模块说明"])

with tab_a:
    st.markdown("""
```
┌─────────────────────────────────────────┐
│              Streamlit 前端              │
│  仪表盘 │ Agent对话 │ 内容工厂 │ 报告    │
├─────────────────────────────────────────┤
│          LangGraph Agent 引擎            │
│  Planner → 转化分析 │ 竞品分析 │ 舆情   │
│           → 内容工厂 │ SOP执行 │ 报告   │
├─────────────────────────────────────────┤
│   LLM Gateway   │  Tool Layer  │ Memory │
│ DeepSeek/OpenAI │ Shopify/Ads  │ ChrDB  │
└─────────────────────────────────────────┘
```""")

with tab_b:
    st.markdown("""
| 模块 | 技术 | 功能 |
|------|------|------|
| Agent 引擎 | LangGraph | 任务拆解 + 多子 Agent 协作 |
| LLM 网关 | DeepSeek / OpenAI / Anthropic | 统一模型接口，Mock 开发模式 |
| 工具层 | 爬虫 / Shopify / Meta Ads / Google Shopping | 外部数据采集 |
| 记忆层 | ChromaDB + BGE Embedding | 向量语义检索 + RAG 问答 |
| 前端 | Streamlit + Plotly | 仪表盘 / 对话 / 报告 / 知识库 |
""")

st.divider()
st.caption(f"E-Commerce SmartOps Agent v0.1 · DeepSeek + LangGraph + ChromaDB")
