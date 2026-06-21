# deploy — 部署

## 描述
Docker Compose 一键部署。nginx 反代 + uvicorn + React 静态文件。

## 依赖
- 所有其他模块已完成

## 子任务

- [ ] 1. `deploy/nginx.conf` — nginx 配置
  - `/api/*` → `uvicorn:8000`
  - `/*` → React 静态文件（`/usr/share/nginx/html`）
  - 反向代理 WebSocket/SSE 支持
  - gzip 压缩 + 缓存策略
- [ ] 2. `deploy/Dockerfile.api` — FastAPI 镜像
  - `python:3.12-slim` base
  - `pip install -r requirements.txt`
  - `CMD ["uvicorn", "src.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]`
  - 挂载 `data/` 目录（SQLite + ChromaDB 持久化）
- [ ] 3. `deploy/Dockerfile.frontend` — React 构建镜像
  - `node:20-alpine` base
  - `npm ci && npm run build`
  - 产出复制到 nginx 镜像
- [ ] 4. `deploy/docker-compose.yml`
  - services: nginx, api, chromadb（可选）
  - volumes: `./data:/app/data`
  - environment 从 `.env` 注入
  - health checks
- [ ] 5. `deploy/start.sh` — 一键启动脚本
  - `docker compose up -d`
  - 等待 healthy
  - 打印访问 URL
- [ ] 6. 端到端烟雾测试
  - `curl http://localhost/api/health` → 200
  - `curl http://localhost/` → React HTML
- [ ] 7. mypy + ruff 通过（deploy 脚本不检查）

## 验收标准
- [ ] `docker compose up -d` 一键启动
- [ ] `/api/health` 返回 200
- [ ] 前端页面可访问
- [ ] 重启后 SQLite + ChromaDB 数据不丢
