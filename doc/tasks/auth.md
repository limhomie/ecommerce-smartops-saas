# auth — 认证与安全

## 描述
API Key 认证中间件、用户注册、速率限制。依赖 db 模块。

## 依赖
- `db`（已完成）

## 子任务

- [ ] 1. `src/auth/__init__.py` — 模块入口，导出 AuthMiddleware
- [ ] 2. `src/auth/middleware.py` — `AuthMiddleware`（FastAPI middleware）
  - 从 `X-API-Key` header 提取 key
  - 查 `db.get_user_by_api_key()` 验证
  - 成功 → `request.state.user = user`
  - 失败 → 401 JSON
  - 白名单路径：`/api/health`, `/api/users/register`
- [ ] 3. `src/auth/user_service.py` — 用户注册/查询
  - `register_user(username)` → 生成 UUID + API Key（`sk-` + 随机32位 hex）
  - `get_me(user)` → 返回用户信息 + 使用统计
- [ ] 4. `src/auth/rate_limit.py` — 令牌桶速率限制
  - 基于 `user_id` 的内存令牌桶
  - 默认 30 req/min（可配）
  - 超限 → 429 JSON
- [ ] 5. pytest 单元测试（`tests/test_auth.py`）
  - 无 key → 401
  - 错误 key → 401
  - 正确 key → 200
  - 注册 → 返回含 api_key 的 user
  - 速率超限 → 429
- [ ] 6. mypy + ruff 通过

## 接口

```python
from src.auth import AuthMiddleware, UserService
from src.db import Database

db = Database()
user_service = UserService(db)
app.add_middleware(AuthMiddleware, db=db, user_service=user_service)
```

## 验收标准
- [ ] 认证中间件正确拦截无认证请求
- [ ] 注册 API 返回可用 API Key
- [ ] 速率限制超限返回 429
- [ ] 覆盖测试全部通过
