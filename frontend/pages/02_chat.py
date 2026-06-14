"""Agent Chat Page."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Agent 对话", page_icon="🤖", layout="wide")

from frontend.components.sidebar import render_sidebar
from frontend.components.chat_ui import render_chat

settings = render_sidebar()
render_chat(settings["api_url"])
