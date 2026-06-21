# E-Commerce SmartOps Agent — 概要设计文档

## 1. 模块划分

```
┌─────────────────────────────────────────────────────┐
│               frontend-react (React + Vite)          │
│   Dashboard │ Chat │ Content │ Knowledge │ Reports   │
├─────────────────────────────────────────────────────┤
│                api (FastAPI + Uvicorn)               │
│  middleware │ routers │ SSE │ exception handlers     │
├─────────────────────────────────────────────────────┤
│   db        │   auth       │   agent-core            │
│  (SQLite)   │  (API Key)   │  (LangGraph + Cache)    │
├─────────────┴──────────────┼────────────────────────┤
│          memory             │        tools           │
│  (ChromaDB + Embedding)    │   (8 外部 API 工具)      │
└────────────────────────────┘
```

共 8 个模块：

| 模块 | 目录 | 职责 | 依赖 |
|------|------|------|:---:|
| **db** | `src/db/` | SQLite 初始化、ORM、CRUD | — |
| **auth** | `src/auth/` | API Key 认证、用户隔离、速率限制 | db |
| **agent-core** | `src/agent/` | LangGraph 图、Planner、6 子Agent、缓存 | memory, tools, db |
| **tools** | `src/tools/` | 8 个外部 API 工具（Mock/Real 双模） | — |
| **memory** | `src/memory/` | ChromaDB 向量存储、短期/长期记忆、语义检索 | db |
| **api** | `src/api/` | FastAPI 路由、中间件、SSE、异常处理 | auth, agent-core, db |
| **frontend-react** | `frontend_react/` | React SPA，5 页面 | api |
| **deploy** | `deploy/` | Docker Compose、nginx 配置、启动脚本 | — |

## 2. 模块详细设计

### 2.1 db — 数据库层

**文件**: `src/db/__init__.py`, `src/db/schema.py`, `src/db/crud.py`

**Schema** (SQLite):

```sql
CREATE TABLE users (
    id         TEXT PRIMARY KEY,       -- UUID
    username   TEXT NOT NULL UNIQUE,
    api_key    TEXT NOT NULL UNIQUE,   -- sha256 hash, 展示时只显前8位
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE sessions (
    id         TEXT PRIMARY KEY,       -- UUID
    user_id    TEXT NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL DEFAULT '',  -- 自动从第一条问题截取
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE task_history (
    id           TEXT PRIMARY KEY,     -- UUID
    user_id      TEXT NOT NULL REFERENCES users(id),
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    question     TEXT NOT NULL,
    response_sum TEXT NOT NULL DEFAULT '',  -- 摘要（前300字）
    subtasks     TEXT NOT NULL DEFAULT '[]', -- JSON array
    elapsed_ms   INTEGER NOT NULL DEFAULT 0,
    cache_hit    INTEGER NOT NULL DEFAULT 0,  -- 0/1
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**API**:

```python
class Database:
    def init(self) -> None                    # 建表
    # users
    def create_user(self, username: str) -> User
    def get_user_by_api_key(self, key: str) -> User | None
    def list_users(self) -> list[User]
    # sessions
    def create_session(self, user_id: str, title: str) -> Session
    def list_sessions(self, user_id: str) -> list[Session]
    # task_history
    def log_task(self, **kwargs) -> TaskRecord
    def list_tasks(self, user_id: str, session_id: str) -> list[TaskRecord]
    def get_user_stats(self, user_id: str) -> dict
```

### 2.2 auth — 认证与安全

**文件**: `src/auth/__init__.py`, `src/auth/middleware.py`, `src/auth/rate_limit.py`

**设计**:
- FastAPI 中间件从 `X-API-Key` header 提取 key，查 `users` 表
- 认证失败返回 401
- 认证成功将 `user` 对象挂到 `request.state.user`
- 速率限制：基于 `user_id` 的内存令牌桶（`src/auth/rate_limit.py`）

### 2.3 agent-core — Agent 引擎

**文件**: 已有 `src/agent/`，需改造点：

| 改造项 | 说明 |
|--------|------|
| 缓存用户隔离 | `cache.py` 的 hash key 加 `user_id` 前缀 |
| 对话历史持久化 | `graph.py` 的 `_conv_store` 改为从 `db.sessions` + `db.task_history` 恢复 |
| 任务日志写入 | `write_cache_node` 写入 `task_history` 表 |
| Planner 内存 | `planner.py` 已有 `extra_context`，不变 |

### 2.4 tools — 工具层

**文件**: 已有 `src/tools/`，**不改**。

8 个工具保持 Mock/Real 双模式，通过 `.env` 切换。

### 2.5 memory — 记忆层

**文件**: 已有 `src/memory/`，改造点：

| 改造项 | 说明 |
|--------|------|
| 知识库用户隔离 | `vector_store.py` 的 Collection 名称加 `user_{id}_` 前缀 |
| 短期记忆改为 db 驱动 | `short_term.py` 新增 SQLite backend（替换 Redis） |

### 2.6 api — 后端 API

**文件**: 已有 `src/api/`，改造点：

| 改造项 | 说明 |
|--------|------|
| Auth 中间件 | 挂载 `auth/middleware.py` |
| 用户路由 | 新增 `POST /api/users/register`, `GET /api/users/me` |
| Session 路由 | 新增 `GET /api/sessions`, `POST /api/sessions` |
| Task 路由 | `GET /api/tasks/{task_id}` 改为读 db |
| Chat SSE | 已有，不变 |
| Agent 路由 | 已有，加 user 参数 |
| Knowledge 路由 | 已有，Collection 前缀加 `user_id` |

**路由表**:

```
GET    /api/health
POST   /api/users/register        {username}
GET    /api/users/me
GET    /api/sessions              用户会话列表
POST   /api/sessions              {title}
GET    /api/sessions/{id}/tasks   会话任务历史
POST   /api/agent/tasks           {task, session_id}  → 异步执行
GET    /api/agent/tasks/{id}      任务状态/结果
POST   /api/chat                   SSE 流式对话
GET    /api/knowledge/search      ?q=&collection=
POST   /api/knowledge/documents   {content, collection}
DELETE  /api/knowledge/documents/{id}
POST   /api/content/generate      {product, type}
GET    /api/analytics/report      ?date=
```

### 2.7 frontend-react — React 前端

**技术栈**: Vite + React 18 + TypeScript + Ant Design 5 + Ant Design Charts + SSE

**页面路由**:

```
/              → Dashboard
/chat          → Agent 对话
/chat/:id      → 历史会话
/content       → AI 内容工厂
/knowledge     → 知识库管理
/reports       → 分析报告
/login         → API Key 登录
```

**组件树**:

```
App
├── AuthGuard (API Key 输入/验证)
├── Layout
│   ├── Sidebar (导航 + 会话列表)
│   └── Content
│       ├── DashboardPage
│       │   ├── MetricCards
│       │   └── ChartGrid (7 charts)
│       ├── ChatPage
│       │   ├── MessageList (SSE 流式)
│       │   ├── InputArea (预设 + 自定义)
│       │   └── ContextPanel (悬浮导航)
│       ├── ContentFactoryPage
│       │   ├── ProductForm
│       │   └── ContentTabs
│       ├── KnowledgePage
│       │   ├── SearchBar
│       │   ├── UploadArea
│       │   └── DocumentTable
│       └── ReportsPage
│           ├── ReportSelector
│           └── ReportView (Markdown + Charts)
```

### 2.8 deploy — 部署

**文件**: `deploy/nginx.conf`, `deploy/Dockerfile.api`, `deploy/Dockerfile.frontend`, `deploy/docker-compose.yml`

**拓扑**:

```
nginx (:80)
  ├─ /api/*  → uvicorn (FastAPI, :8000, 4 workers)
  ├─ /*      → React 静态文件 (Vite build)
  └─ /health → nginx health check
```

## 3. 模块间接口

```
auth ──(request.state.user)──→ api
db   ──(Database instance)──→ auth, api, agent-core, memory
agent-core ──(graph.ainvoke)──→ api
memory ──(VectorStore, LongTermMemory)──→ agent-core, api
tools ──(ToolRegistry)──→ agent-core
frontend-react ──(HTTP/SSE)──→ api
```

- 模块间通过**构造函数注入**传递依赖
- 无循环依赖（dag 关系：db → auth → api → frontend）
- 每个模块可独立加载配置、独立编写 pytest

## 4. 数据流

```
用户输入 (React)
  │ POST /api/agent/tasks
  ▼
FastAPI (auth 中间件 → request.state.user)
  │ 查缓存 (agent-core, user-scoped)
  ├─ [hit] → 直接返回
  └─ [miss]
       │ task_history 写入 (db)
       ▼
     LangGraph → planner (含对话历史)
              → sub-agents (调 LLM + tools)
              → report_generator
              → write_cache + 写入 task_history
       │
       ▼
     SSE 流式返回 → React 渲染 Markdown + 图表
```

## 5. 测试策略

- **单元测试**: 每个模块独立 pytest，mock 外部依赖
- **集成测试**: api 路由 + db 真实 SQLite
- **Agent 测试**: mock LLM 验证图拓扑 + 路由正确性
- **前端测试**: Vitest + React Testing Library
- **覆盖率**: ≥ 80%（行覆盖）
