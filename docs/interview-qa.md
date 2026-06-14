# E-Commerce SmartOps Agent — 开发问题与面试问答

## 一、Agent 架构设计

### Q1: 为什么选择 LangGraph 而不是直接用 LangChain？

**问题**：项目初期直接用 LangChain 的 AgentExecutor 做任务编排，但遇到两个瓶颈：
1. Agent 执行流程是黑盒的，无法控制中间步骤的路由
2. 多个子 Agent 之间的状态传递需要手动管理

**方案**：改用 LangGraph 的 StateGraph，用 Supervisor 路由模式：
- `Planner` 节点拆解模糊指令 → 生成子任务列表
- `Router` 根据子任务类型分发到对应的子 Agent
- `advance` 节点推进任务索引，形成 while 循环
- 最后 `report_generator` 汇总所有结果

这个方案下每个节点的输入输出是显式的 TypedDict，状态通过 reducer 合并，可观测、可中断、可恢复。

### Q2: 6 个子 Agent 是串行还是并行？

串行。每个子 Agent 的输出可能是下一个的输入（例如竞品分析的结果需要传给报告生成器），且 LLM 调用本身是 I/O 密集而非 CPU 密集，Python 多线程对 LLM API 调用无加速效果。

优化方向：如果子任务之间无依赖（如同时分析转化率 + 舆情），可以用 LangGraph 的 `Send` API 做并行 fan-out。当前项目保持串行以保证结果质量。

### Q3: Agent 为什么会"卡住"？怎么解决的？

**现象**：用户提交任务后 UI 无响应 60-90 秒。

**根因**：Streamlit 是单线程同步执行模型，Agent 图在主线程 `graph.stream()` 阻塞了 Tornado 事件循环。6 个 LLM 调用 × 25 秒 = 150 秒阻塞。

**解决方案**：
1. 将 Agent 执行移到 `threading.Thread` 后台线程
2. 用模块级 `threading.Lock` 保护的结果字典在线程间通信
3. Streamlit 主线程每 1.5 秒 `st.rerun()` 轮询结果
4. 用户切换页面不中断后台线程

**教训**：`st.session_state` 不是线程安全的，不能从非请求线程写入。需要独立的线程安全存储。

---

## 二、RAG 知识库

### Q4: RAG 链路的设计是怎样的？

```
文档上传 → 段落切块(500 char, 50 overlap) → BGE Embedding(1024维)
→ ChromaDB 向量存储 → 用户查询 → 向量检索(top_k) → 拼接上下文 → LLM 精读回答
```

关键设计决策：
1. **不用 LangChain 的 RAG 封装**：直接用 ChromaDB + sentence-transformers，减少依赖
2. **内容哈希做文档 ID**：`MD5(content)[:12]` 作为 ChromaDB 文档 ID，同内容重新摄入 = upsert 覆盖，天然去重
3. **切块策略**：按段落（`\n\n`）切分，而不是按字符数硬切，保持语义完整性，超长段落才按字符切

### Q5: 搜索返回大量重复内容怎么解决的？

**现象**：products 知识库 127 个向量块，搜一次返回 10 个完全相同的结果。

**根因**：
1. 每次启动都重新运行 `seed_knowledge.py`，用 `uuid.uuid4()` 生成新 ID，同内容反复插入
2. 切块算法有 bug：长段落按字符滑动窗口切（step = chunk_size - overlap），产生了大量重叠块

**修复**：
1. `add_documents()` 改用 `MD5(content)` 做 ID → `upsert` 替代 `add` → 同内容 = 同 ID = 覆盖
2. 修复切块逻辑：先按段落边界切，只有超长段落才按字符切
3. LLM 上下文构建时加内容哈希去重：相同 chunk 只送一次

### Q6: 语义搜索返回不相关结果（幻觉）怎么解决？

**现象**：搜"今天天气"也返回竞品分析结果。

**根因**：ChromaDB 对任意查询都会返回最近邻，即使语义不相关也会有结果（只是距离远）。

**解决方案**：
1. 加 **相关性阈值**：`MAX_RELEVANCE_DISTANCE = 1.1`（余弦距离），超过阈值的直接丢弃
2. **LLM 零幻觉约束 Prompt**：明确要求"只根据文档回答，没有就说不清楚"
3. **全局排序**：`search_all()` 将所有知识库的结果按距离排序取 top_k，而不是每库各取 top_k
4. **显示相关度分数**：UI 用绿(好)/橙(一般)区分，让用户判断可信度

### Q7: HuggingFace 模型下载失败怎么处理？

**问题**：BGE-large-zh-v1.5 模型从 huggingface.co 下载超时（国内网络）。

**解决**：
1. `os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"` 设置国内镜像
2. 必须在 `import chromadb` **之前**设置，否则 sentence-transformers 会先用默认地址尝试连接
3. 知识库搜索加 15 秒超时 + Mock 数据兜底，避免模型下载阻塞整个系统

---

## 三、Web 爬虫与数据清洗

### Q8: 静态爬虫对 SPA 网站无效怎么解决？

**问题**：蕉内（bananain.com）是 Next.js SPA，所有内容 JS 动态渲染，`requests.get()` 拿到的 HTML 只有框架壳。

**检测方法**：`curl` 拿到 HTML 后用 `grep` 搜目标关键词（凉皮/Aircoolskin），发现关键词在 HTML 源码中存在但在 BeautifulSoup 提取的文本中丢失——说明它们在 `<script>` 标签内的 JS 代码中。

**解决方案**：
1. 增强 HTML 解析：提取 `<meta description>`、JSON-LD 结构化数据、`<noscript>` 内容、`<img alt>` 文本
2. 手动策展（Manual Curation）：对关键竞品信息手动录入 Markdown → 切块 → 入库
3. 未来方案：Playwright 无头浏览器（太重，当前项目不需要）

**设计原则**：爬虫自动提取 + 手动策展双轨并行，不追求 100% 自动化。

### Q9: HTML 清洗后内容太短导致被丢弃？

**问题**：HSIA 实体店铺页爬取后只剩 66 字符（去掉导航栏后），低于 80 字符的摄入阈值，整个页面被跳过。

**修复**：降低阈值到 30 字符，同时优化清洗逻辑：
1. 识别每页通用的导航文本模式（如"品牌理念 新品推荐 实体店铺"）并删除
2. 删除 ICP 备案号/版权声明等固定 footer 文本
3. 保留短的但有信息密度的内容（如门店列表）

---

## 四、前端与用户体验

### Q10: Streamlit 的 `st.rerun(scope="fragment")` 报错？

**问题**：`StreamlitAPIException: scope="fragment" can only be specified from @st.fragment-decorated functions`

**原因**：Streamlit 1.38 版本 `st.rerun(scope="fragment")` 只能在 `@st.fragment` 装饰的函数内使用，而我们用的是普通函数。

**修复**：`st.rerun(scope="fragment")` → `st.rerun()`（不带 scope 参数）

### Q11: `NameError: function not defined` 反复出现？

**问题**：UI 代码中按钮点击时引用 `_generate` 函数，但函数定义在文件末尾。

**原因**：Python 是**解释执行**，代码从上到下逐行执行。当 Streamlit 执行到 `launch(TASK_KEY, _generate, ...)` 时，`_generate` 还没定义。

**修复**：所有后台执行函数必须**定义在 UI 代码之前**。这是 Streamlit 开发中最容易犯的错误，因为习惯了其他框架的"先 UI 后逻辑"模式。

---

## 五、LLM 调用

### Q12: DeepSeek API 调用慢怎么优化？

**问题**：单个 LLM 调用 20-25 秒，6 个串行 = 150 秒。

**优化手段**：
1. **限制子任务数量**：Planner prompt 明确要求"最多 3-4 个子任务"
2. **减少 Prompt 长度**：去掉冗余的格式要求，精简为要点式
3. **快速通道**：对话页提供单次 LLM 调用模式（15-20 秒），不做完整 Agent 图
4. **Prompt Cache**：相同 system prompt 可以复用，减少 token 消耗

### Q13: langchain-openai 版本不兼容？

**问题**：`ModuleNotFoundError: No module named 'langchain_core.pydantic_v1'`

**原因**：`langchain-core 1.4.x` 废弃了 `pydantic_v1` 兼容模块，但旧版 `langchain-openai 0.1.6` 还在引用。

**修复**：升级三个包到兼容版本：
```
langchain-openai: 0.1.6 → 1.3.2
langchain-core: 1.4.1 → 1.4.7
langchain: 1.3.6 → 1.3.9
```

---

## 六、工程实践

### Q14: 为什么所有外部 API 工具都用 Mock/Real 双模式？

好处：
1. 开发时不需要真实 API Key，Mock 数据结构和真实 API 完全一致
2. 演示时数据可控，不会因为 API 限流/欠费导致 demo 失败
3. 接入真实 API 只需改 `.env` 文件，代码零修改

实现方式：
```python
class ShopifyTool:
    def __init__(self, store_url="", access_token=""):
        self._enabled = bool(store_url and access_token)

    async def execute(self, action):
        if self._enabled:
            data = await self._real_api_call()
            if data:
                return ToolResult(data=data, source="shopify_api")
        return ToolResult(data=self._mock_data(), source="mock")
```

### Q15: `.env` 文件怎么确保不泄露到 Git？

1. `.gitignore` 中添加 `.env` 和 `.env.local`
2. 提供 `.env.example` 模板（只有 key 名，没有 value）
3. 提交前用 `git status` 确认 `.env` 不在 staged files 中
4. `config/settings.py` 的所有敏感字段都设了空字符串默认值

---

## 面试话术模板

**"介绍一下这个项目"**

> 我做了一个电商智能体运营系统，面向跨境电商场景。核心是基于 LangGraph 的多 Agent 协作引擎——用户输入一个模糊指令比如"为什么转化率下降了"，Planner 会自动拆解成分析步骤，然后路由到 6 个专门的子 Agent 去执行，最后汇总成报告。
>
> 技术栈上，Agent 框架用 LangGraph 的 Supervisor 模式，LLM 接 DeepSeek，知识库用 ChromaDB+BGE 做向量检索，前端用 Streamlit+Plotly 做数据看板。工具层集成了 Shopify/Meta Ads/Google Ads 三大平台的 API，支持真实接入和 Mock 双模式。
>
> 比较有意思的是 RAG 部分——我写了一个 Web 爬虫自动抓竞品官网内容，然后切块→Embedding→入库，用户可以用自然语言搜索"HSIA 有多少家线下门店"，系统能从向量库检索到相关文档块，再用 LLM 精读生成准确回答。

**"遇到的最大挑战是什么"**

> 最大的挑战是 Streamlit 的线程模型和 Agent 长时间执行之间的矛盾。Agent 跑完 6 个子任务要 60-90 秒，但 Streamlit 是同步的，直接调用会卡死 UI。
> 
> 我的方案是把 Agent 放到后台线程执行，用线程安全的结果字典在线程间通信，前端每 1.5 秒轮询一次。关键教训是 st.session_state 不能从非请求线程写入，需要独立的 Lock 保护。
> 
> 另一个挑战是 RAG 的幻觉问题——向量数据库对任何查询都会返回最近邻，需要设置相关性阈值过滤，配合 LLM prompt 约束"只根据文档回答"。

**"如果再给你两周时间，你会完善什么"**

> 1. 把 FastAPI 后端的 SSE 流式对话接起来，目前 Agent 对话框是直连的
> 2. 支持更多竞品数据源，特别是天猫/京东的商品价格和评论
> 3. 加一个定时调度层，Windows Task Scheduler 或 GitHub Actions 每天自动爬取+更新报告
> 4. Agent 子任务支持并行执行（LangGraph Send API），把 90 秒压到 30 秒
