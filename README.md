# E-Commerce SmartOps SaaS

基于 LangGraph 的多 Agent 协作 + RAG 知识库 + React 前端。面向跨境电商的 AI 智能运营平台。

面向跨境电商场景，集成数据分析、竞品监控、AI 内容工厂、自动化 SOP 和智能知识库管理。

## 快速启动

```bash
# 1. 克隆项目
git clone git@github.com:limhomie/ecommerce-smartops-agent.git
cd ecommerce-smartops-agent

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 配置
cp .env.example .env
# 编辑 .env：LLM_PROVIDER=deepseek  LLM_API_KEY=sk-你的key

# 4. 初始化知识库（种子数据）
python scripts/seed_knowledge.py

# 5. 启动后端
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

# 6. 启动前端（新终端）
cd frontend_react && npm install && npm run dev

# 浏览器打开 http://localhost:5173
```

Docker 一键部署：

```bash
bash deploy/start.sh
# 前端 http://localhost  |  API http://localhost/api/health
```

## 项目结构

```
├── frontend_react/             React SPA（Vite + Ant Design + TypeScript）
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx   运营仪表盘（指标卡片 + 7 图表）
│       │   ├── Chat.tsx        Agent 对话（SSE 流式 + 上下文面板）
│       │   ├── ContentFactory.tsx  AI 内容工厂
│       │   ├── KnowledgeBase.tsx   知识库管理
│       │   ├── Reports.tsx     分析报告
│       │   └── Login.tsx       API Key 登录/注册
│       ├── components/
│       │   ├── Layout.tsx      侧边栏导航
│       │   └── ContextPanel.tsx 右侧悬浮上下文面板
│       └── api/client.ts       Axios + 认证拦截器
├── src/
│   ├── db/                     SQLite 数据库层
│   │   ├── schema.py           DDL（users / sessions / task_history）
│   │   └── crud.py             CRUD 操作
│   ├── auth/                   认证与安全
│   │   ├── middleware.py        X-API-Key 认证中间件
│   │   ├── user_service.py     用户注册/查询
│   │   └── rate_limit.py       令牌桶速率限制
│   ├── agent/                  LangGraph 多 Agent 核心
│   │   ├── graph.py            StateGraph 组装（缓存 + 对话记忆 + 任务日志）
│   │   ├── state.py            AgentState
│   │   ├── cache.py            两阶段查询缓存（精确 + BGE 语义）
│   │   ├── supervisor/         Planner + Router
│   │   ├── analysts/           分析 Agent（转化率/竞品/舆情）
│   │   └── operators/          操作 Agent（内容工厂/SOP/报告）
│   ├── tools/                  工具层
│   │   ├── shopify_api.py      Shopify Admin API
│   │   ├── meta_ads.py         Meta Ads（Facebook Graph API）
│   │   ├── google_ads_api.py   Google Ads API
│   │   ├── google_shopping.py  Google Shopping 搜索
│   │   ├── amazon_api.py       亚马逊 Seller API
│   │   ├── logistics.py        物流查询
│   │   ├── runner.py           自动化脚本执行器
│   │   ├── web_crawler.py      Web 爬虫
│   │   └── base.py             工具基类 + 注册表
│   ├── memory/                 记忆层
│   │   ├── vector_store.py     ChromaDB 向量存储（用户隔离）
│   │   ├── long_term.py        长期记忆（RAG）
│   │   ├── short_term.py       短期记忆（InMemory / Redis / SQLite）
│   │   └── manager.py          记忆管理器
│   ├── llm/                    LLM 接口
│   │   ├── factory.py          统一工厂（DeepSeek/OpenAI/Anthropic/Mock）
│   │   └── mock.py             Mock 模式
│   ├── api/                    FastAPI 后端
│   │   ├── app.py              应用工厂
│   │   └── routers/            health / users / sessions / chat / agent / knowledge / analytics
│   └── observability/          structlog 日志
├── deploy/
│   ├── nginx.conf              nginx 反向代理
│   ├── Dockerfile.api          FastAPI 镜像
│   ├── Dockerfile.frontend     React 构建 + nginx 镜像
│   └── start.sh                一键启动
├── tests/                      49 个 pytest 测试
├── doc/                        需求/设计/任务文档
│   ├── proposal.md
│   ├── design.md
│   └── prompt.md
└── data/                       运行时数据（SQLite + ChromaDB + 缓存）
```

## 架构

```
                    nginx (:80)
                   /          \
              /*               /api/*
          React SPA          uvicorn (FastAPI)
          (静态文件)          :8000
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
     Auth (API Key)        Agent Engine              Tool Layer
     Rate Limiter          ┌─────────────┐           (8 tools)
     User Service          │ check_cache │           Mock/Real
          │                │   Planner   │          双模式
          │                │  6 sub-agents│              │
          │                │ write_cache │              │
          │                └──────┬──────┘              │
          │                       │                       │
     ──── SQLite ────    Conversation    ChromaDB + BGE
     users/sessions/      Memory         知识库 (RAG)
     task_history        (语义检索)
```

## 功能模块

| 页面 | 功能 |
|------|------|
| 仪表盘 | 4 指标卡片 + 7 张交互式图表 + 日期联动 |
| Agent 对话 | 多 Agent 协作，SSE 流式，后台异步，上下文面板 |
| AI 内容工厂 | 9 种内容类型，自定义人群/风格 |
| 知识库管理 | ChromaDB 向量库，上传/搜索/删除 |
| 分析报告 | 5 种报告 AI 生成，Markdown 渲染 |

## 核心特性

### 查询缓存
两阶段缓存：Stage 1（文本归一化 + MD5，0ms）→ Stage 2（BGE 语义匹配，~60ms）。相同/相似问题秒回，用户隔离。

### 对话记忆
时间窗口（最近 3 轮）+ 语义检索（BGE embedding 找回远处相关对话）+ 自动摘要（长对话压缩）。Planner 理解 "那竞品呢？" 等追问。

### 多用户
API Key 认证 + SQLite 用户表 + 缓存隔离 + 知识库 namespace 隔离 + 速率限制（30 req/min）。

### Mock 模式
所有外部 API 工具支持 Mock/Real 双模式。`LLM_PROVIDER=mock` 时全链路零 API 调用，可离线演示。

## 外部 API 集成

| 平台 | 接入方式 |
|------|----------|
| Shopify | Admin REST API + Access Token |
| Meta Ads | Facebook Graph API v19.0 |
| Google Ads | Google Ads API v16 + OAuth2 |
| Google Shopping | Search API |

填 `.env` 凭证即切换真实数据，无需改代码。

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 框架 | LangGraph（Supervisor 路由模式） |
| LLM | DeepSeek / OpenAI / Anthropic（统一工厂 + Mock） |
| 向量数据库 | ChromaDB + BGE-large-zh-v1.5 |
| 关系数据库 | SQLite（users / sessions / task_history） |
| 后端 | FastAPI + Uvicorn |
| 前端 | React 19 + Vite + Ant Design 5 + TypeScript |
| 认证 | API Key + 中间件 |
| 日志 | structlog |
| 部署 | Docker Compose + nginx |

## 开发计划

- [x] Phase 1: 项目骨架 + LLM 层
- [x] Phase 2: 记忆层（ChromaDB + 向量检索）
- [x] Phase 3: 工具层（8 个工具 + Mock/Real 双模式）
- [x] Phase 4: Agent 核心（LangGraph Supervisor + 6 子Agent）
- [x] Phase 5: FastAPI + Streamlit 前端
- [x] Phase 6: 种子数据 + 测试 + 爬虫
- [x] Phase 7: 查询缓存 + 对话记忆 + 异常日志
- [x] Phase 8: SQLite 数据库 + API Key 认证 + 用户隔离
- [x] Phase 9: React 前端 + Docker 部署

## License

MIT
