"""Streamlit sidebar component."""

from __future__ import annotations

import streamlit as st


def render_sidebar() -> dict:
    """Render the sidebar and return user settings."""
    with st.sidebar:
        st.title("SmartOps Agent")
        st.caption("电商智能体运营系统")

        st.divider()

        # API configuration
        st.subheader("API 配置")
        api_url = st.text_input(
            "后端地址",
            value="http://localhost:8000",
            help="FastAPI 服务地址",
        )

        st.divider()

        # Session management
        st.subheader("会话")
        if st.button("新建会话", use_container_width=True):
            import uuid
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # Info
        st.caption(f"会话 ID: {st.session_state.get('session_id', '未初始化')[:8]}...")

        # Navigation hint
        st.divider()
        st.caption("使用左侧页面导航切换功能模块")

    return {"api_url": api_url}
