# E-Commerce SmartOps Agent

电商智能体运营系统 — 基于 LangGraph 的多 Agent 协作 + RAG 知识库 + 工具调用。

面向跨境电商场景，集成数据分析、竞品监控、AI 内容工厂、自动化 SOP 和智能知识库管理。

## 快速启动

```bash
# 1. 克隆项目
git clone git@github.com:limhomie/ecommerce-smartops-agent.git
cd ecommerce-smartops-agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，修改：
#   LLM_PROVIDER=deepseek          # openai / anthropic / mock
#   LLM_API_KEY=sk-你的key

# 4. 初始化知识库（种子数据）
python scripts/seed_knowledge.py

# 5. 爬取竞品数据
python scripts/crawl_competitors.py

# 6. 启动前端
python -m streamlit run frontend/app.py --server.port 8501

# 浏览器打开 http://localhost:8501
```

## 项目结构

```
├── frontend/                  Streamlit 前端
│   ├── app.py                 主页（指标看板 + 快速操作）
│   ├── pages/
│   │   ├── 01_dashboard.py    运营仪表盘（日期联动 + Plotly 图表）
│   │   ├── 02_chat.py         Agent 对话（多 Agent 协作）
│   │   ├── 03_content.py      AI 内容工厂（文案/SEO/广告生成）
│   │   ├── 04_knowledge.py    知识库管理（上传/搜索/同步/爬取）
│   │   └── 05_reports.py      分析报告（5种报告 AI 生成）
│   └── components/            共享组件（任务执行器/聊天UI）
├── src/
│   ├── agent/                 LangGraph 多 Agent 核心
│   │   ├── graph.py           StateGraph 组装（Supervisor 路由模式）
│   │   ├── state.py           AgentState 定义
│   │   ├── supervisor/        Planner（任务拆解）+ Router（子Agent路由）
│   │   ├── analysts/          分析 Agent（转化率/竞品/舆情）
│   │   └── operators/         操作 Agent（内容工厂/SOP/报告生成）
│   ├── tools/                 工具层
│   │   ├── shopify_api.py     Shopify Admin API（Mock/Real 自动切换）
│   │   ├── meta_ads.py        Meta Ads API（Facebook Graph API）
│   │   ├── google_ads_api.py  Google Ads API（OAuth2）
│   │   ├── google_shopping.py Google Shopping 搜索
│   │   ├── amazon_api.py      亚马逊 Seller API
│   │   ├── logistics.py       物流查询 + 自动回复
│   │   ├── runner.py          自动化脚本执行器
│   │   ├── web_crawler.py     Web 爬虫（HTML → 清洗文本）
│   │   └── base.py            工具基类 + 注册表
│   ├── memory/                记忆层
│   │   ├── vector_store.py    ChromaDB 向量存储（BGE Embedding）
│   │   ├── long_term.py       长期记忆（文档切块/语义检索/RAG）
│   │   └── short_term.py      短期记忆（Redis 对话上下文）
│   ├── llm/                   LLM 接口层
│   │   ├── factory.py         统一工厂（DeepSeek/OpenAI/Anthropic/Mock）
│   │   └── mock.py            Mock 模式（开发/演示用）
│   ├── api/                   FastAPI 后端
│   │   ├── app.py             应用工厂
│   │   └── routers/           chat / agent / knowledge / analytics
│   ├── utils/                 工具
│   │   └── chart_utils.py     Plotly 图表生成（7种图表类型）
│   └── observability/         日志/中间件
├── scripts/
│   ├── seed_knowledge.py      种子数据（产品/FAQ/政策/会员）
│   ├── crawl_competitors.py   Phase 1 竞品爬虫
│   └── run_dev.py             一键启动脚本
├── data/documents/            知识库源文档（.md 文件）
├── config/settings.py         Pydantic Settings 统一配置
├── docker-compose.yml         Redis + ChromaDB 开发环境
└── tests/                     测试
```

## 架构

```
┌──────────────────────────────────────────┐
│           Streamlit 前端（5 页面）         │
│  仪表盘 │ Agent对话 │ 内容工厂 │ 报告      │
├──────────────────────────────────────────┤
│       LangGraph Agent 引擎（Supervisor）   │
│  Planner → 转化分析/竞品分析/舆情分析      │
│         → 内容工厂/SOP执行/报告生成        │
├──────────────────┬───────────────────────┤
│    LLM Gateway   │     Memory Layer      │
│  DeepSeek/OpenAI │  ChromaDB + BGE       │
├──────────────────┴───────────────────────┤
│              Tool Layer（8 工具）          │
│  Shopify │ Meta Ads │ Google Ads │ 爬虫   │
└──────────────────────────────────────────┘
```

## 功能模块

| 页面 | 功能 | 状态 |
|------|------|------|
| 仪表盘 | 日期联动指标卡片 + 7张交互式图表 + 自定义数据 | ✅ |
| Agent 对话 | 多 Agent 协作（Planner + 6 子Agent），后台异步执行 | ✅ |
| AI 内容工厂 | DeepSeek 生成文案/SEO/广告脚本，后台执行，支持自定义 | ✅ |
| 知识库管理 | ChromaDB 向量库，上传/粘贴/URL拉取/目录同步/语义搜索 | ✅ |
| 分析报告 | 5种报告 AI 生成（转化/竞品/广告/舆情/周报），图表 + 下载 | ✅ |

## 外部 API 集成

所有工具均支持 **Mock/Real 双模式**，填了 API Key 自动切换真实数据：

| 平台 | 配置文件 | 接入方式 |
|------|----------|----------|
| Shopify | `shopify_api.py` | Admin REST API + Access Token |
| Meta Ads | `meta_ads.py` | Facebook Graph API v19.0 |
| Google Ads | `google_ads_api.py` | Google Ads API v16 + OAuth2 |
| Google Shopping | `google_shopping.py` | Search API |

在 `.env` 中填入对应的凭证即可切换，无需改任何代码。

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 框架 | LangGraph（Supervisor 路由模式） |
| LLM | DeepSeek / OpenAI / Anthropic（统一工厂 + Mock 降级） |
| 向量数据库 | ChromaDB（Embedded）+ BGE-large-zh-v1.5 |
| 前端 | Streamlit + Plotly |
| 后端 | FastAPI + Uvicorn |
| 配置 | Pydantic Settings（.env） |
| 日志 | structlog |

## 开发计划

- [x] Phase 1: 项目骨架 + LLM 层
- [x] Phase 2: 记忆层（ChromaDB + 向量检索）
- [x] Phase 3: 工具层（8 个工具 + Mock/Real 双模式）
- [x] Phase 4: Agent 核心（LangGraph Supervisor + 6 子Agent）
- [x] Phase 5: FastAPI + Streamlit 前端
- [x] Phase 6: 种子数据 + 测试 + 爬虫
- [ ] Phase 7: FastAPI 后端完善 + SSE 流式
- [ ] Phase 8: 更多竞品爬虫源 + 定时调度

## License

MIT
