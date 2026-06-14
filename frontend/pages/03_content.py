"""AI Content Factory — real LLM generation, background execution."""

from __future__ import annotations

import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import streamlit as st
from frontend.components.task_runner import status, update, launch, pending

st.set_page_config(page_title="AI 内容工厂", page_icon="✍️", layout="wide")

TASK_KEY = "content_factory"


# ── Background task function (must be defined before UI calls it) ──
def _do_generate(prompt: str, log=None):
    t0 = time.time()
    if log:
        log("正在初始化模型...")
    from src.llm import set_llm
    from src.llm.factory import create_llm_from_settings
    from config.settings import Settings
    s = Settings()
    llm = create_llm_from_settings(s)
    set_llm(llm)
    if log:
        log(f"模型: {s.llm_provider}/{s.llm_model}, 正在生成...")
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    if log:
        log(f"生成完成，共 {len(content)} 字符")
    return {"content": content, "elapsed": f"{time.time()-t0:.0f}秒"}


def _tab_title(section: str) -> str:
    m = re.match(r"##\s*(.+)", section.strip())
    if m:
        t = m.group(1).strip()
        return t[:25] + "…" if len(t) > 25 else t
    return section.strip()[:20]


# ── UI ──
st.title("AI 内容工厂")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("产品信息")
    product_name = st.text_input("产品名称", value="有机棉T恤")

    st.caption("目标人群")
    audience_presets = st.multiselect(
        "选择预设人群",
        ["年轻女性", "商务人士", "学生", "户外爱好者", "宝妈", "Z世代", "银发族"],
        default=["年轻女性"],
    )
    audience_custom = st.text_input("自定义人群描述", placeholder="例：25-35岁注重环保的都市白领")
    target_audience = "、".join(audience_presets)
    if audience_custom:
        target_audience = audience_custom if not audience_presets else f"{target_audience}；{audience_custom}"

    st.caption("文案风格")
    tone_preset = st.selectbox("选择预设风格", ["专业正式", "活泼轻松", "情感共鸣", "科技感", "极简风", "可爱风", "自定义"])
    tone = st.text_input("自定义风格描述", placeholder="例：小红书种草风格，多用emoji") if tone_preset == "自定义" else tone_preset
    if tone_preset != "自定义":
        st.caption(f"当前风格: {tone}")

    st.divider()
    st.caption("生成内容类型")
    content_presets = st.multiselect(
        "选择预设类型",
        ["A+ 详情页文案", "SEO 关键词", "Facebook 广告脚本",
         "Instagram 广告脚本", "邮件营销文案", "产品标题优化",
         "品牌故事", "卖点提炼", "小红书笔记"],
        default=["A+ 详情页文案", "SEO 关键词", "Facebook 广告脚本"],
    )
    content_custom = st.text_input("自定义内容类型", placeholder="例：抖音直播话术")
    all_types = list(content_presets)
    if content_custom:
        all_types.append(content_custom)

    st.divider()
    running = pending(TASK_KEY)
    can_gen = product_name and target_audience and all_types and not running
    if st.button("🚀 AI 生成内容", use_container_width=True, type="primary", disabled=not can_gen):
        types_str = "\n".join(f"- {t}" for t in all_types)
        prompt = f"""你是一位顶级电商文案和广告创意专家。

## 产品信息
- 产品名称：{product_name}
- 目标人群：{target_audience}
- 文案风格：{tone}

## 需要生成的内容类型
{types_str}

## 要求
1. 每种内容类型都要单独输出，用「## 类型名称」作为标题
2. 文案必须符合指定风格，精准针对目标人群
3. SEO关键词要区分主关键词和长尾关键词
4. 广告脚本要包含标题、正文、CTA，至少两个版本
5. 直接输出可发布内容，用中文"""
        launch(TASK_KEY, _do_generate, prompt)
        st.rerun()
    if not can_gen and not running:
        st.caption("请填写产品名称、目标人群和内容类型")

with col2:
    st.subheader("生成结果")
    task = status(TASK_KEY)

    if task.get("status") == "running":
        prog = task.get("progress", [])
        st.info("AI 正在后台生成内容... 可以切换到其他页面，不会中断。")
        if prog:
            with st.expander("进度", expanded=True):
                for line in prog[-5:]:
                    st.caption(line)
        time.sleep(1.5)
        st.rerun()

    if task.get("status") == "done":
        result = task.get("result", {})
        update(TASK_KEY, status="delivered")
        content = result.get("content", "")
        elapsed = result.get("elapsed", "?")

        if content:
            sections = re.split(r"\n(?=## )", content)
            if len(sections) > 1:
                tabs = st.tabs([_tab_title(s) for s in sections])
                for tab, sec in zip(tabs, sections):
                    with tab:
                        st.markdown(sec)
            else:
                st.markdown(content)
            st.success(f"已生成 {len(sections)} 个内容板块 · 耗时 {elapsed}")
        else:
            st.warning("生成结果为空")

    if task.get("status") == "error":
        err = task.get("error", "")
        update(TASK_KEY, status="delivered")
        st.error(f"生成失败: {err[:500]}")

    if task.get("status") == "delivered" or not task:
        st.caption("输入产品信息后点击「AI 生成内容」开始")
