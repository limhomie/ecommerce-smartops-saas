# memory — 记忆层

## 描述
ChromaDB 向量存储 + 短期/长期记忆。已有基础，需要用户隔离和 SQLite short-term backend。

## 依赖
- `db`（已完成）

## 子任务

- [ ] 1. `src/memory/vector_store.py` — Collection 名称加 `user_{id}_` 前缀
  - 向后兼容：`user_id=""` 不走前缀
  - `get_or_create_collection(name, user_id="")` → `f"user_{user_id}_{name}"`
- [ ] 2. `src/memory/short_term.py` — 新增 `SQLiteBackend`
  - 实现 `Backend` 协议（`get`, `append`, `clear`）
  - 表结构：`conversations (session_id TEXT, role TEXT, content TEXT, ts REAL)`
  - 替代 Redis 作为默认 backend
- [ ] 3. `src/memory/manager.py` — 构造函数加 `user_id` 参数
  - 透传给 `VectorStore` collection 操作
- [ ] 4. pytest 单元测试（`tests/test_memory/test_user_isolation.py`）
  - 两个用户的知识库检索结果不重复
- [ ] 5. pytest 单元测试（`tests/test_memory/test_sqlite_backend.py`）
  - SQLiteBackend 的 append/get/clear
- [ ] 6. mypy + ruff 通过

## 验收标准
- [ ] 不同用户的知识库操作互不影响
- [ ] SQLite 短期记忆可替代 Redis
- [ ] ChromaDB 持久化正常
