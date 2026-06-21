# db — 数据库层

## 描述
SQLite 数据库初始化、Schema 定义、CRUD 封装。三张表：users、sessions、task_history。

## 依赖
无

## 子任务

- [ ] 1. `src/db/__init__.py` — Database 类骨架（`init()` 建表）
- [ ] 2. `src/db/schema.py` — DDL 语句（users / sessions / task_history）
- [ ] 3. `src/db/crud.py` — User CRUD（create_user, get_user_by_api_key, list_users）
- [ ] 4. `src/db/crud.py` — Session CRUD（create_session, list_sessions, get_session）
- [ ] 5. `src/db/crud.py` — TaskHistory CRUD（log_task, list_tasks, get_user_stats）
- [ ] 6. `src/db/config.py` — SQLite 路径配置（复用 .env，默认 `data/ecommerce.db`）
- [ ] 7. pytest 单元测试（`tests/test_db.py`）：建表 + CRUD + 并发写入
- [ ] 8. mypy + ruff 通过

## 接口

```python
from src.db import Database
db = Database("data/ecommerce.db")
db.init()

user = db.create_user(username="test")
user = db.get_user_by_api_key(key)
tasks = db.list_tasks(user_id, session_id)
```

## 验收标准
- [ ] 三张表自动建表
- [ ] CRUD 全部有测试
- [ ] 多线程并发写不报错
- [ ] mypy strict + ruff lint 通过
