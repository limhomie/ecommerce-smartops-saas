"""Knowledge Base Management — real ChromaDB + embedding + dynamic sync."""

from __future__ import annotations

import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import streamlit as st

st.set_page_config(page_title="知识库管理", page_icon="📚", layout="wide")

st.title("知识库管理")

# ── Init vector store (cached so model downloads once) ──
@st.cache_resource
def get_vector_store():
    from src.memory.vector_store import VectorStore
    from config.settings import Settings
    return VectorStore(Settings())

@st.cache_resource
def get_long_term_memory():
    from src.memory.long_term import LongTermMemory
    return LongTermMemory(get_vector_store())

store = get_vector_store()
ltm = get_long_term_memory()

COLLECTIONS = ["products", "competitors", "ads_history", "policies", "enterprise_wiki"]

# ── Tabs ──
tab1, tab2, tab3, tab4 = st.tabs(["📤 上传文档", "🔍 语义搜索", "🔄 目录同步", "📊 统计概览"])

# ═══════════════════════════════════════
with tab1:
    st.subheader("上传文档到知识库")

    up_col1, up_col2 = st.columns([2, 1])
    with up_col1:
        uploaded_file = st.file_uploader(
            "选择文档（.md / .txt / .html）",
            type=["md", "txt", "html"],
            key="kb_upload",
        )
    with up_col2:
        target_collection = st.selectbox("目标知识库", COLLECTIONS, key="kb_coll")

    if uploaded_file:
        file_content = uploaded_file.read().decode("utf-8")
        st.text_area("预览", file_content, height=200, disabled=True)

        if st.button("📤 上传并向量化", type="primary", use_container_width=True):
            with st.spinner("正在切块并向量化..."):
                try:
                    chunks = ltm.ingest_document(
                        target_collection,
                        file_content,
                        {"filename": uploaded_file.name, "source": "manual_upload",
                         "uploaded_at": time.strftime("%Y-%m-%d %H:%M")},
                    )
                    st.success(f"成功！文件切分为 {chunks} 个块，已存入 `{target_collection}` 知识库")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"上传失败: {e}")

    st.divider()
    st.subheader("或直接粘贴内容")
    paste_text = st.text_area("粘贴文本内容", height=120, key="paste_text",
                              placeholder="直接粘贴需要入库的政策、文档、竞品信息...")
    paste_coll = st.selectbox("知识库", COLLECTIONS, key="paste_coll")
    if st.button("📋 粘贴入库", disabled=not paste_text.strip()):
        with st.spinner("向量化中..."):
            try:
                chunks = ltm.ingest_document(paste_coll, paste_text, {"source": "manual_paste"})
                st.success(f"已入库，{chunks} 个向量块 → `{paste_coll}`")
            except Exception as e:
                st.error(f"入库失败: {e}")

# ═══════════════════════════════════════
with tab2:
    st.subheader("语义搜索知识库")
    search_q = st.text_input("输入自然语言问题", placeholder="例：竞品A的定价策略是什么？退换货政策？")
    search_coll = st.selectbox("搜索范围", ["全部"] + COLLECTIONS, key="search_coll")

    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_btn = st.button("🔍 搜索", disabled=not search_q.strip(), type="primary")
    with search_col2:
        ai_answer = st.checkbox("🤖 AI 回答", value=True, help="用大模型从检索结果中提取精确答案")

    if search_btn:
        with st.spinner("搜索中..."):
            try:
                # Retrieve
                if search_coll == "全部":
                    docs = ltm.search_all(search_q, top_k=5)
                else:
                    docs = ltm.search(search_coll, search_q, top_k=5)

                if not docs:
                    st.info("未找到相关结果。可能原因：1) 知识库中无此信息 2) 需要更换搜索词")
                    st.stop()

                # ── AI Answer (RAG: retrieve → generate) ──
                if ai_answer:
                    st.subheader("AI 回答")
                    with st.spinner("AI 正在从知识库中提取答案..."):
                        try:
                            from src.llm import set_llm
                            from src.llm.factory import create_llm_from_settings
                            from config.settings import Settings
                            s = Settings()
                            llm = create_llm_from_settings(s)
                            set_llm(llm)

                            # Build context from top chunks (dedup + cap at ~3000 chars)
                            context_parts = []
                            seen = set()
                            total_chars = 0
                            for d in docs[:8]:
                                src = d['metadata'].get('category', d['metadata'].get('filename', '?'))
                                chunk = d['content']
                                # Skip duplicates
                                import hashlib
                                h = hashlib.md5(chunk.encode()).hexdigest()[:8]
                                if h in seen:
                                    continue
                                seen.add(h)
                                if total_chars + len(chunk) > 3000:
                                    chunk = chunk[:3000 - total_chars]
                                context_parts.append(f"[来源:{src}] {chunk}")
                                total_chars += len(chunk)
                                if total_chars >= 3000:
                                    break
                            context = "\n\n---\n\n".join(context_parts)

                            rag_prompt = f"""你是一个知识库问答助手。请**仅根据**以下文档内容回答用户问题。

## 用户问题
{search_q}

## 文档内容
{context}

## 回答规则
1. 从文档中找出所有相关信息，即使信息分散在不同段落也要汇总
2. 如果文档明确列出了具体名称/数量，直接统计并回答（如列举了4个店铺就回答4家）
3. 如果文档中有总数和具体例子的信息，两个都要提到
4. 只使用文档中的信息，不要编造
5. 如果确实没有任何相关信息，回复"根据现有资料，无法回答此问题"
6. 简洁输出，先给结论再列细节"""
                            response = llm.invoke(rag_prompt)
                            answer = response.content if hasattr(response, "content") else str(response)
                            st.markdown(answer)
                        except Exception as e:
                            st.warning(f"AI 回答生成失败（将显示原始检索结果）: {e}")

                # ── Source chunks ──
                st.divider()
                st.subheader("检索来源")
                st.caption(f"共 {len(docs)} 条（相关度 <1.0 🟢高质量，1.0-1.1 🟠一般，>1.1 已过滤）")
                for i, doc in enumerate(docs):
                    score = doc.get('distance', 0)
                    color = "green" if score < 1.0 else "orange" if score < 1.1 else "red"
                    coll = doc.get('metadata', {}).get('collection', '?')
                    cat = doc.get('metadata', {}).get('category', doc.get('metadata', {}).get('filename', '?'))
                    brand = doc.get('metadata', {}).get('brand', '')
                    with st.container(border=True):
                        st.caption(f":{color}[#{i+1} 相关度: {score:.3f}] 📁{coll} | {cat} {brand}")
                        st.markdown(doc["content"][:400])
            except Exception as e:
                st.error(f"搜索失败: {e}")
                import traceback
                with st.expander("详情"):
                    st.code(traceback.format_exc())

# ═══════════════════════════════════════
with tab3:
    st.subheader("从目录同步知识库")
    st.caption("重新扫描 `data/documents/` 下所有 .md/.txt 文件，分类入库。适用于批量更新政策文档。")

    sync_dir = "data/documents"
    st.code(f"同步目录: {sync_dir}")

    if st.button("🔄 扫描并同步目录", type="primary"):
        with st.spinner("扫描目录中..."):
            from pathlib import Path
            from config.settings import ROOT_DIR

            results = {}
            for coll in COLLECTIONS:
                coll_dir = ROOT_DIR / "data" / "documents" / coll
                if coll_dir.exists():
                    try:
                        count = ltm.ingest_directory(coll, coll_dir)
                        if count > 0:
                            results[coll] = count
                    except Exception as e:
                        st.warning(f"{coll} 同步失败: {e}")

        if results:
            st.success("同步完成：")
            for coll, count in results.items():
                st.write(f"  ✓ `{coll}` — {count} 个新块")
        else:
            st.info("没有检测到新文档。在 data/documents/ 下放入 .md 文件后重试。")

    st.divider()
    st.subheader("🔗 从 URL 拉取内容")
    st.caption("输入一个网页 URL，自动抓取内容并入库（适合抓取竞品政策、行业公告等）")
    url = st.text_input("URL", placeholder="https://example.com/policy-update")
    url_coll = st.selectbox("入库到", COLLECTIONS, key="url_coll")
    if st.button("🌐 拉取并入库", disabled=not url.strip()):
        with st.spinner("抓取中..."):
            try:
                import httpx
                resp = httpx.get(url.strip(), timeout=15)
                if resp.status_code == 200:
                    # Simple HTML to text (no bs4 dependency needed)
                    text = re.sub(r"<[^>]+>", "", resp.text)
                    text = re.sub(r"\n{3,}", "\n\n", text).strip()
                    if len(text) > 100:
                        chunks = ltm.ingest_document(url_coll, text[:10000],
                                                     {"source": url, "fetched_at": time.strftime("%Y-%m-%d %H:%M")})
                        st.success(f"抓取成功！{chunks} 个块已存入 `{url_coll}`")
                    else:
                        st.warning("页面内容为空或太短")
                else:
                    st.error(f"HTTP {resp.status_code}")
            except Exception as e:
                st.error(f"抓取失败: {e}")

# ═══════════════════════════════════════
with tab4:
    st.subheader("知识库统计")

    try:
        stats = ltm.get_stats()
    except Exception:
        stats = {}

    cols = st.columns(len(COLLECTIONS))
    for i, coll in enumerate(COLLECTIONS):
        count = stats.get(coll, 0)
        cols[i].metric(label=coll, value=count, delta="块")

    total_chunks = sum(stats.values())
    st.metric("总向量块数", total_chunks)

    st.divider()
    st.subheader("各知识库详情")

    for coll in COLLECTIONS:
        count = stats.get(coll, 0)
        if count > 0:
            with st.expander(f"📁 {coll} ({count} 块)"):
                try:
                    # Show a sample from each collection
                    docs = ltm.search(coll, "示例", top_k=3)
                    for i, doc in enumerate(docs):
                        st.caption(f"块 #{i+1} | 来源: {doc.get('metadata', {}).get('filename', doc.get('metadata', {}).get('source', 'N/A'))}")
                        st.text(doc["content"][:300])
                except Exception:
                    st.caption("无法加载预览")
        else:
            st.caption(f"📁 {coll} — 空")

    st.caption(f"ChromaDB 路径: {os.path.abspath('data/chroma')}")

    # Danger zone
    st.divider()
    with st.expander("⚠️ 危险操作", expanded=False):
        del_coll = st.selectbox("选择要清空的知识库", COLLECTIONS, key="del_coll")
        if st.button("🗑️ 清空此知识库", type="secondary"):
            try:
                store.delete_collection(del_coll)
                st.cache_data.clear()
                st.cache_resource.clear()
                st.warning(f"已清空 `{del_coll}`，刷新页面生效")
            except Exception as e:
                st.error(f"清空失败: {e}")
