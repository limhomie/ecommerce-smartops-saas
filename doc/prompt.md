# E-Commerce SmartOps Agent — Vibe Coding Prompt

## 项目概述

电商智能运营 Agent SaaS 系统。基于 LangGraph 多 Agent 协作 + RAG 知识库 + React 前端。
面向跨境电商卖家，提供数据分析、竞品监控、AI 内容生成、知识库管理和自动报告功能。

## 当前状态

项目已有完整的 Agent 引擎（LangGraph + 6 子Agent + 查询缓存 + 对话记忆）、
工具层（8 个外部 API，Mock/Real 双模）、FastAPI 后端骨架、Streamlit 前端原型。

现需将其升级为多用户 SaaS 服务：SQLite 数据库 + API Key 认证 + React 前端 + Docker 部署。

## 核心原则

1. 每个模块独立可测，模块间通过构造函数注入依赖
2. 不改动已有工具层代码（`src/tools/`）
3. Agent 核心逻辑不变，仅加 user_id 隔离和任务日志
4. 所有代码必须有 pytest 单元测试，mypy strict + ruff lint 通过
5. 测试覆盖率 ≥ 80%

## 文档索引

- 需求文档：`doc/proposal.md`
- 概要设计：`doc/design.md`
- 任务划分：`doc/tasks/<module>.md`（8 个模块）
- 总体进度：`doc/tasks/progress.md`

## 执行流程

1. 读取 `doc/tasks/progress.md`，找到下一个未开始的模块
2. 读取该模块的 `doc/tasks/<module>.md`
3. 按子任务顺序实现
4. 每完成一个子任务，更新 `<module>.md` 中的 checkbox
5. 模块全部完成后，更新 `progress.md` 中该模块状态
6. 继续下一个模块

## 模块实施顺序

```
Phase 1:  db → auth
Phase 2:  tools → memory → agent-core
Phase 3:  api → frontend-react
Phase 4:  deploy
```

## 质量标准

- [ ] pytest 全部通过
- [ ] pytest --cov 覆盖率 ≥ 80%
- [ ] mypy --strict 通过
- [ ] ruff check 通过
- [ ] 无循环导入
- [ ] 异常都有 structlog 记录

## 注意事项

- 每完成一个模块，运行 `python -m pytest tests/ -q` 确保无回归
- 修改已有文件前先 Read
- 新建文件使用绝对路径
- 不确定的需求先提问，不要猜测
