# agent-core — Agent 引擎

## 描述
LangGraph 多 Agent 引擎。已有基础代码，需要做用户隔离、任务日志写入、缓存改造。

## 依赖
- `db`（已完成）
- `memory`（已完成）
- `tools`（已完成）

## 子任务

- [ ] 1. `src/agent/cache.py` — 缓存 key 加 `user_id` 前缀
  - `_hash(question)` → `_hash(user_id, question)`
  - `get()` / `set()` 签名加 `user_id` 参数
  - 向下兼容（`user_id=""` 走旧逻辑）
- [ ] 2. `src/agent/graph.py` — `write_cache_node` 写入 `task_history`
  - 注入 `db` 实例（通过 state 或模块级单例）
  - 写入 `task_history` 表（user_id, session_id, question, response_sum, subtasks, elapsed_ms, cache_hit）
- [ ] 3. `src/agent/graph.py` — `_conv_store` 支持从 db 恢复
  - 新增 `load_history(db, session_id)` — 从 `task_history` 恢复最近对话
  - 保留内存 dict 作为一级缓存
- [ ] 4. `src/agent/state.py` — AgentState 加 `user_id: str` 字段
- [ ] 5. `src/agent/graph.py` — `planner_node` 传 `user_id` 给 cache 和 memory
- [ ] 6. pytest 单元测试（`tests/test_agent/test_cache_isolation.py`）
  - 两个不同 user_id 的同一问题不串缓存
  - 同一 user_id 的缓存命中
- [ ] 7. pytest 单元测试（`tests/test_agent/test_graph_db.py`）
  - mock db + mock LLM，验证图执行后 `task_history` 有记录
- [ ] 8. mypy + ruff 通过

## 验收标准
- [ ] 不同用户缓存隔离
- [ ] 任务执行后 `task_history` 表有记录
- [ ] 从 db 恢复对话历史可正常注入 Planner
- [ ] 不影响已有 Agent 图拓扑
