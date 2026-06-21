# AI 智能助手实习生 — 面试问答准备

> 公司: 深圳十沣科技有限公司
> 简历: E-Commerce SmartOps Agent / News Briefing Agent / Paper Analysis Assistant
> JD 匹配度分析: Python ✓ | LangGraph ✓ | RAG ✓ | 向量库(ChromaDB) △ | Claude Code ✓ | Agent 开发 ✓ | MCP ✗

---

## 一、项目深挖（必问）

### Q1: 介绍一下你最熟悉的一个项目

**建议**: 重点讲 SmartOps Agent，因为和 JD 最匹配（知识库 + Agent + Python）。

> 我做过一个电商智能体运营系统。核心是用 LangGraph 搭了一个多 Agent 协作引擎——用户输入模糊指令，比如"分析转化率为什么下降"，Supervisor 会自动拆成分析步骤，然后路由到 6 个专门的子 Agent 执行，最后汇总成带图表的分析报告。
>
> 技术栈上，Agent 编排用 LangGraph 的 StateGraph + Supervisor 模式，LLM 接 DeepSeek，知识库用 ChromaDB + BGE Embedding 做向量检索 + RAG 问答。前端用 Streamlit 搭了 5 个页面，包括仪表盘、对话、内容工厂、知识库管理和报告生成。
>
> 比较特别的是我做了一个动态爬虫 → 自动切块 → Embedding → 入库的完整 RAG 链路，竞品网站的内容可以每天自动更新到知识库里，然后用户用自然语言搜索，LLM 从检索到的文档中提取精确答案。
>
> 整个项目独立完成，从架构设计到代码实现大概用了一周多。

**面试官可能的追问**:
- "6 个子 Agent 为什么要这样分？" → 按电商运营的实际工作流划分：先分析数据（转化/竞品/舆情），再做操作（内容/SOP），最后出报告
- "Sub-agent 之间怎么通信？" → 共享 AgentState TypedDict，每个节点读 state、返回更新后的 dict，LangGraph 自动合并
- "为什么用 ChromaDB 不用 Milvus？" → 见下文

### Q2: 为什么选 ChromaDB 而不是 Milvus？

**这个问题一定会问，因为 JD 明确写了 Milvus。**

> ChromaDB 和 Milvus 都是向量数据库，选择 ChromaDB 是因为：
> 1. **零配置**: `chromadb.PersistentClient(path="./data")` 一行代码启动，不需要 Docker 或服务端部署，对个人项目更友好
> 2. **Embedded 模式**: ChromaDB 可以直接嵌入 Python 进程，自带 embedding function 管理（内置 SentenceTransformer），不需要额外部署 embedding 服务
> 3. **开发效率**: 从 pip install 到能跑起来不到 5 分钟
> 
> 但 Milvus 在生产场景下更强：
> - **分布式架构**: 支持十亿级向量，ChromaDB 单机适合百万级
> - **多种索引**: IVF_FLAT、HNSW、DiskANN 等，ChromaDB 只支持 HNSW
> - **标量过滤 + 向量搜索**: Milvus 的混合查询能力更强
> 
> **如果公司用 Milvus，我可以快速迁移**: 核心的 Embedding 和切块逻辑完全通用，只是把 `collection.add()` 改成 Milvus 的 `insert()`，`collection.query()` 改成 `search()`，API 语义几乎一样。这两个我都用过——Paper Analysis Assistant 项目里我甚至是自己用 numpy 手动实现向量检索的，所以对底层原理很熟。”

**关键点**: 不要说"我不会 Milvus"，要说"我用过 ChromaDB，理解向量检索底层原理，迁移到 Milvus 很快"。

### Q3: RAG 链路怎么做的？遇到过什么问题？

> 完整链路：**文档上传 → 段落切块（500字符/50重叠）→ BGE-large-zh-v1.5 Embedding（1024维）→ ChromaDB 存储 → 用户查询 → 向量检索（top_k）→ 拼接上下文 → LLM 精读回答**。
>
> 遇到的典型问题：
> 1. **搜索幻觉**: 用户问"今天天气"，向量库也会返回"最相似"的结果（只是距离远）。解决方法是设置相关性阈值 + LLM prompt 约束"只根据文档回答，没有就说不知道"
> 2. **重复入库**: 每次启动重新导入导致重复向量。改用 MD5 哈希做文档 ID，同内容自动 upsert 覆盖
> 3. **中文搜索不准**: 默认 embedding 模型对中文支持差，换成了 BGE-large-zh-v1.5
> 4. **HuggingFace 下载超时**: 国内网络问题，设置 `HF_ENDPOINT=https://hf-mirror.com` 镜像 + 15 秒超时兜底

### Q4: Agent 任务拆解是怎么实现的？

> 用一个 Supervisor Planner 节点，把用户的模糊指令扔给 LLM：

> ```
> System Prompt: "你是任务规划器，把用户指令拆成 3-4 个子任务"
> User: "分析转化率下降原因"
> → LLM 返回 JSON: [
>     {step:1, agent:"conversion_analyst", description:"拉取转化率趋势数据"},
>     {step:2, agent:"competitor_analyst", description:"搜索竞品价格变化"},
>     {step:3, agent:"sentiment_analyst", description:"分析用户差评"},
>     {step:4, agent:"report_generator", description:"汇总报告"}
>   ]
> ```

> 然后 Router 根据 agent 字段把每个子任务分发到对应的节点。关键设计是约束 LLM 输出 JSON 格式 + 有限枚举值（agent 字段只能是预定义的 6 种），避免 LLM 自由发挥导致路由失败。如果 JSON 解析失败，还有关键词匹配的兜底逻辑。

**追问**: "如果 LLM 拆解得不对怎么办？"
> Planner prompt 里限制了子任务数量和 agent 类型枚举。测试下来 DeepSeek 的 JSON 输出稳定性不错，偶尔格式不对也能用正则 fallback 修复。最差情况就是 Planner 输出四个通用步骤（数据→分析→建议→报告），至少不会中断流程。

---

## 二、技术基础

### Q5: LangGraph 和 LangChain 的区别？

> - LangChain 是**组件库**，提供 LLM、Chain、Tool、Memory 等积木
> - LangGraph 是**状态图引擎**，用于编排多步骤的 Agent 工作流
> - 我的项目里两者都用：用 LangChain 的 ChatOpenAI 封装 LLM 调用，用 LangGraph 的 StateGraph 编排 Agent 节点
> - LangGraph 的核心优势：**显式状态管理**（TypedDict + Reducer）、**条件路由**（conditional edges）、**可中断/可恢复**（checkpointer）、**可观测**（每个节点的输入输出都能看到）

### Q6: 你了解 MCP（Model Context Protocol）吗？

**JD 明确要求，简历没提。需要提前准备。**

> MCP 是 Anthropic 提出的一个开放协议，让 LLM 应用能标准化地连接到外部工具和数据源。可以理解为"AI 应用的 USB 协议"。
>
> **核心概念**：
> - MCP Server: 暴露工具/资源的服务端
> - MCP Client: 调用工具的客户端（如 Claude Desktop、Claude Code）
> - 通信方式: JSON-RPC over stdio/SSE
>
> **我虽然没有在项目里直接实现 MCP Server，但我的 Agent 工具层设计思路和 MCP 类似**：每个工具（Shopify、Meta Ads）都有统一的 `execute(action, params)` 接口 → 工具注册表 → Agent 调用。这和 MCP 的 `tools/list` → `tools/call` 模式是一样的。
>
> **如果公司需要，我可以**：
> 1. 把现有的 Agent 工具封装成 MCP Server
> 2. 让 Claude Code 通过 MCP 调用我们内部的 API

### Q7: 向量数据库的选型和对比？

| 维度 | ChromaDB | Milvus | Pinecone |
|------|----------|--------|----------|
| 部署 | 嵌入式 | Docker/K8s | SaaS |
| 规模 | 百万级 | 十亿级 | 十亿级 |
| 索引 | HNSW | IVF/HNSW/DiskANN | 专有 |
| 过滤 | 元数据过滤 | 标量+向量混合 | 元数据过滤 |
| 适用 | 原型/小项目 | 生产/大规模 | 企业/SaaS |
| 学习成本 | 极低 | 中等 | 低 |

> 我的项目用 ChromaDB 因为单机开发够用。如果团队用 Milvus，迁移成本很低——Embedding 和切块逻辑不变，只是 API 名称不同（`add`→`insert`, `query`→`search`）。

---

## 三、数据清洗与处理

### Q8: 爬虫数据是怎么做清洗的？

> 1. **HTML 解析**: BeautifulSoup 提取文本 → 删除 `<script>/<style>/<nav>/<footer>` → 删除 class/id 含 nav/menu/sidebar/footer 的 div
> 2. **去导航噪音**: 识别多页面重复的导航文本模式并删除（如 "品牌理念 新品推荐 实体店铺" 是每个页面都有）
> 3. **去短行**: 删除长度 ≤2 的无效行、常见 UI 文本（"Chinese"、"English"、"返回"、"首页"等）
> 4. **去 ICP/版权**: 正则删除备案号和版权声明
> 5. **格式规范化**: 合并多余空行 → 段落结构保留
>
> 清洗后还会做一层**质量检查**: 如果文本长度 < 30 字符，说明这个页面主要是图片/JS，跳过不入库。

### Q9: News Briefing Agent 的数据处理流程？

> 这是完全自动化的数据处理 pipeline：
> 1. **RSS 抓取**: feedparser 解析 5 个 RSS 源（36氪/虎嗅/少数派/InfoQ/机器之心）
> 2. **去重**: 用 `(title_hash, pub_date)` 做联合主键，SQLite 存储，新文章才处理
> 3. **清洗**: Pandas 去 HTML 标签、截断过长文章、统一日期格式
> 4. **AI 处理**: 把清洗后的文章列表 + One-shot Prompt 喂给 DeepSeek，输出结构化日报（标题/TLDR/详情/来源）
> 5. **分发**: 生成 Markdown 文件 → Feishu Webhook 推送
> 6. **调度**: GitHub Actions cron `0 0 * * *` 每天早上 8 点自动跑

---

## 四、AI 开发工作流

### Q10: 你用 Claude Code 的开发流程是怎样的？

> 1. **规划阶段**: 让 Claude Code 先读代码库 → 讨论架构方案 → 生成 Plan
> 2. **编码阶段**: 描述需求 → Claude 生成代码 → 我 review 关键逻辑 → 测试
> 3. **调试阶段**: 遇到 bug 贴错误日志 → Claude 分析根因 → 一起修
> 4. **提交阶段**: Claude 自动生成 commit message → 我 review 后 push
>
> 三个项目（SmartOps Agent、News Briefing、Paper Analysis）都是这个流程从零搭的。关键经验是：**不能盲目信任生成的代码**，Agent 的边界条件（空输入、异常路径、线程安全）需要自己把关。

### Q11: 说说你对 Vibe Coding 的理解

> Vibe Coding 的核心是**用自然语言驱动 AI 编程**，人负责意图和决策，AI 负责实现细节。
>
> 我的实践：
> - 思路和高层设计我来定（比如选择 Supervisor 路由模式）→ 让 AI 生成骨架 → 我 review 架构合理性
> - 重复性代码（CRUD、配置、HTML 模板）完全交给 AI
> - 关键逻辑（Agent 状态管理、RAG 去重）自己写，因为需要精确控制
> - 测试和文档让 AI 生成初稿，自己补充细节
>
> 最终效果是开发速度提升了 3-5 倍，同时保持对核心代码的掌控。

---

## 五、场景设计题（高频）

### Q12: 如果让你为内部团队搭建一个知识库问答助手，你会怎么做？

> 1. **需求分析**: 问清楚知识来源（文档/数据库/API）、用户群体（开发/运营/管理）、预期 QPS
> 2. **技术选型**: 
>    - 知识库规模 < 10 万条 + 单机 → ChromaDB
>    - 知识库规模 > 百万 + 多人并发 → Milvus + Redis 缓存
> 3. **数据准备**: 
>    - 收集所有文档 → 统一格式（Markdown/JSON）→ 清洗（去重/去 HTML/去无效内容）
>    - 切块策略按文档类型：FAQ 按 Q&A 对切，长文档按段落切（500 chars），API 文档按函数切
> 4. **入库**: 批量 Embedding（bge-large-zh-v1.5）→ 向量库 + 元数据（来源/部门/更新时间）
> 5. **检索 + 生成**:
>    - 用户问 → Embedding → 向量检索 top_k → 拼接上下文 → LLM 回答
>    - 关键：Prompt 约束"只根据文档回答" → 带引用来源
> 6. **迭代**: 记录用户反馈（👍/👎）→ 调整切块策略 → 补充缺失知识
> 7. **部署**: FastAPI 后端 + Streamlit/Web 前端 + Docker 部署

### Q13: 如果知识库数据源每天更新，你怎么保证数据新鲜度？

> 1. **增量更新**: 爬虫/API 记录上次抓取时间 → 只拉取新数据 → MD5 去重后增量 upsert
> 2. **过期清理**: 文档元数据带 `expires_at` 字段 → 定时任务删除过期文档
> 3. **全量刷新**: 对于重要但量小的数据源（如政策文件），直接清空重新入库
> 4. **调度**: GitHub Actions cron 或 APScheduler，每天凌晨跑
> 5. **监控**: 记录入库文档数 → 如果新文档数为 0，发告警（可能数据源挂了）
>
> News Briefing Agent 项目就是按这个思路做的：每天 RSS 拉取 → SQLite 去重 → Pandas 清洗 → AI 处理 → 推送，全自动。

---

## 六、非技术问题

### Q14: 为什么投 AI 智能助手实习生这个岗位？

> 我的技术栈和岗位匹配度很高——LangGraph/Agent/RAG/向量数据库/Claude Code，这些在我的三个项目里都深度实践过。十沣科技的 AI 智能助手方向是我感兴趣的方向，我希望从一个 side project 开发者成长为能在工业级场景下交付 AI 产品的工程师。

### Q15: 你觉得自己最大的优势是什么？

> 独立交付能力。三个项目都是个人从 0 到 1 完成的（Paper Analysis → News Briefing → SmartOps Agent），每个都跑通、可演示、有 GitHub。而且我不只是调 API——我理解 Agent 编排的底层逻辑（状态图、路由、工具注册表），也理解 RAG 的完整链路（切块→Embedding→检索→生成），不是黑盒使用框架。

### Q16: 有什么想问我们的？

1. "团队的 AI 智能助手目前处于什么阶段？主要在解决哪些场景？"
2. "技术栈预期是什么？会用到 Milvus + LangGraph 吗？"
3. "实习生的工作是参与现有系统还是独立负责某个模块？"

---

## 七、JD 关键词对照速查

| JD 要求 | 你的经历 | 准备方向 |
|---------|----------|----------|
| Python | 3 个项目均 Python | 如问"写过多复杂的 Python"，举 Agent State 管理 + 异步任务调度 |
| Agent 开发（LangGraph） | SmartOps 核心用 LangGraph | 准备说清楚 StateGraph/节点/条件边/reducer 的概念 |
| RAG | 两个项目实现 RAG | 准备完整链路 + 幻觉/去重/切块的问题和解决 |
| Milvus | 用过 ChromaDB | **准备 Milvus vs ChromaDB 对比 + 迁移思路** |
| MCP | 无经验 | **准备 MCP 基本概念 + 类比你的工具注册表** |
| 数据清洗 | Web Crawler + Pandas | 准备 HTML→文本的 pipeline 细节 |
| Claude Code | 三个项目都用 | 准备开发流程 + Vibe Coding 理解 |
| 知识库搭建 | SmartOps 知识库管理页 | 准备从上传到检索的完整流程 |

---

## 八、必会的基础概念（防突袭）

- **Embedding**: 文本→向量的映射，BGE 是中文领域最好的开源模型之一
- **余弦相似度**: `cos(θ) = A·B / (|A|×|B|)`，值越大越相似，ChromaDB 返回的是距离（1 - 相似度）
- **Chunk 切块策略**: chunk_size 决定上下文窗口（500 适合 FAQ，1000 适合长文档），chunk_overlap 防止语义断裂（一般 10-20%）
- **Prompt Engineering**: System Prompt 定角色 + 约束格式，User Prompt 给具体任务，Few-shot 给示例
- **Function Calling / Tool Use**: LLM 输出结构化 JSON → 代码解析 → 执行工具 → 结果返回 LLM
- **Agent 路由模式**: Supervisor（中心调度）、Swarm（多 Agent 自由协作）、Sequential（流水线）
- **SSE (Server-Sent Events)**: HTTP 长连接，服务端推送流式数据，ChatGPT 的打字效果就是用 SSE 实现的
