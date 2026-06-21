# api — FastAPI 后端

## 描述
REST API + SSE。已有基础（health/chat/agent/knowledge/analytics 路由），需要添加用户路由、auth 中间件集成、session 路由、并发修复。

## 依赖
- `db`（已完成）
- `auth`（已完成）
- `agent-core`（已完成）

## 子任务

- [ ] 1. `src/api/app.py` — lifespan 注入 `Database` 实例
  - 从 `Settings` 读 db 路径
  - `app.state.db = Database(...); app.state.db.init()`
- [ ] 2. `src/api/middleware.py` — 替换 `SecurityMiddleware` 为 `AuthMiddleware`
  - 挂载 `auth/middleware.py` 的认证中间件
  - 白名单：`/api/health`, `/api/users/register`
- [ ] 3. `src/api/routers/users.py` — 新增用户路由
  - `POST /api/users/register` → `{user, api_key}`
  - `GET /api/users/me` → 用户信息 + 使用统计
- [ ] 4. `src/api/routers/sessions.py` — 新增会话路由
  - `GET /api/sessions` → 当前用户会话列表
  - `POST /api/sessions` → 创建新会话 `{title}`
  - `GET /api/sessions/{id}/tasks` → 会话任务历史
- [ ] 5. `src/api/routers/agent.py` — 改造
  - `create_task` 从 `request.state.user` 取 `user_id`
  - 传入 AgentState：`user_id`, `session_id`
  - 任务完成后写入 `task_history`
  - 并发：`ThreadPoolExecutor(max_workers=4)`
- [ ] 6. `src/api/routers/chat.py` — SSE 改造
  - 加 `user_id` 到初始 AgentState
- [ ] 7. `src/api/routers/knowledge.py` — 知识库路由
  - 所有 Collection 操作加 `user_id` 前缀
- [ ] 8. `src/api/exceptions.py` — 补充异常处理器
  - 401 / 429 / 500 统一 JSON 格式
- [ ] 9. pytest 集成测试（`tests/test_api/`）
  - 注册 → 获取 key → 调用受保护路由
  - 无 key → 401
  - 错误 key → 401
  - SSE 流式返回
  - Session CRUD
- [ ] 10. mypy + ruff 通过

## 验收标准
- [ ] 所有路由有集成测试
- [ ] Auth 正确拦截
- [ ] SSE 流式工作正常
- [ ] 并发请求不报错
