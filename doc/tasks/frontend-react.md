# frontend-react — React 前端

## 描述
Vite + React 18 + TypeScript + Ant Design 5 SPA，5 个业务页面 + 登录页。

## 依赖
- `api`（已完成）

## 子任务

- [ ] 1. 脚手架
  - `npm create vite@latest frontend_react -- --template react-ts`
  - `npm install antd @ant-design/charts axios react-router-dom`
  - Vite proxy 配置（`/api` → `localhost:8000`）
- [ ] 2. `src/api/client.ts` — Axios 封装
  - baseURL 配置
  - 请求拦截器注入 `X-API-Key`（从 localStorage 读取）
  - 响应拦截器处理 401
- [ ] 3. `src/App.tsx` — 路由 + AuthGuard
  - `react-router-dom` 路由表
  - `AuthGuard` 组件：无 key 时显示登录页
- [ ] 4. `src/pages/Login.tsx` — API Key 登录
  - 输入框（`type="password"`）
  - 保存到 localStorage
  - 调用 `GET /api/users/me` 验证
- [ ] 5. `src/pages/Dashboard.tsx` — 仪表盘
  - `StatisticCard` 指标卡片（4 个）
  - `@ant-design/charts` 7 张图表
  - 日期范围选择器
  - 数据从 `GET /api/analytics/report` 获取
- [ ] 6. `src/pages/Chat.tsx` — Agent 对话
  - `ChatMessageList` — 消息气泡列表（Markdown 渲染）
  - `ChatInput` — 预设按钮 + 自定义输入
  - `ContextPanel` — 右侧悬浮上下文导航（hover 展开，锚点跳转）
  - SSE 流式接收（`EventSource` / `fetch` + ReadableStream）
  - 后台任务状态轮询
- [ ] 7. `src/pages/ContentFactory.tsx` — AI 内容工厂
  - 产品信息表单（名称、人群、风格）
  - 内容类型多选
  - 异步生成 + Tabs 展示
- [ ] 8. `src/pages/KnowledgeBase.tsx` — 知识库管理
  - 搜索栏 + 结果列表
  - 文档上传（Upload 组件）
  - 文档表格（CRUD）
- [ ] 9. `src/pages/Reports.tsx` — 分析报告
  - 报告类型选择器 + 时间范围
  - 报告 Markdown 渲染 + 图表
  - SSE 流式生成
- [ ] 10. Vitest 组件测试
  - Login 页渲染
  - Dashboard 页渲染
  - Chat 页消息列表
  - AuthGuard 路由保护
- [ ] 11. ESLint + TypeScript strict 通过
- [ ] 12. `npm run build` 成功，产出到 `frontend_react/dist/`

## 验收标准
- [ ] 5 个页面可正常渲染
- [ ] API Key 登录流程完整
- [ ] SSE 聊天功能正常
- [ ] 右侧上下文面板 hover/点击跳转
- [ ] `npm run build` 无错误
