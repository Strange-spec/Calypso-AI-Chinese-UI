# Calypso AI 中文 Web 控制台系统设计文档

**文档编号**：SPEC-20260917-01  
**状态**：已评审 (Approved)  
**创建时间**：2026-09-17  
**技术选型**：Python FastAPI + Vue 3 (Element Plus + ECharts) + Docker (Multi-stage build)

---

## 1. 背景与目标

Calypso AI（现作为 F5 AI Security 核心引擎）提供针对大模型输入与输出的实时安全护栏（AI Guardrails）以及全自动化的对抗性漏洞评估（AI Red Team）。

本项目旨在基于 Calypso AI 官方 REST API 体系开发一套面向国内企业用户的**全中文 Web 交互控制台**，并以单容器镜像（Docker）交付，解决以下核心痛点：
1. **中文本土化与易用性**：提供全中文操作体验与合规语义（阻断、脱敏、放行、越狱分类等）。
2. **多模式开箱即用**：支持动态配置真实 Calypso 集群地址与 API Token，并内置离线演示/模拟（Mock）引擎，在缺乏外网或演示场景下直接展示完整分析体验。
3. **Guardrails & Red Team 双轮驱动**：覆盖实时护栏对话测试、24h/7d/30d 指标聚合、以及红队任务与报告多维分析。
4. **轻量化一键部署**：多阶段构建生成单一容器镜像，避免多组件依赖与 CORS 跨域问题。

---

## 2. 整体架构与技术选型

### 2.1 架构拓扑

```
+-----------------------------------------------------------------------------------+
|                              用户浏览器 (中文 Web SPA)                             |
|          Vue 3 + Vite + Element Plus + Apache ECharts + Pinia (中文交互)          |
+-----------------------------------------------------------------------------------+
                                         │
                   HTTP/REST + SSE (端口 8080: /api/v1/* & /*)
                                         ▼
+-----------------------------------------------------------------------------------+
|                        Docker 容器 (单一镜像交付)                                  |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   |                    FastAPI BFF (Backend-For-Frontend)                     |   |
|   |  - 路由与静态资源托管 (app/static)                                         |   |
|   |  - 凭证与 Endpoint 动态透传 / 代理转发                                    |   |
|   |  - 历史指标聚合引擎 (24h / 7d / 30d Aggregator)                           |   |
|   |  - 内置离线模拟引擎 (Mock Engine, 含 BMW 红队真实案例)                    |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
                                         │
                    HTTPS 代理转发 (携带 Authorization Bearer Token)
                                         ▼
+-----------------------------------------------------------------------------------+
|                     Calypso AI (F5 AI Security) 目标集群                           |
|  - REST 后端: /backend/v1/projects, /scanners, /prompts, /campaigns, /audit      |
|  - 代理网关: /openai/{provider_name}/chat/completions                             |
+-----------------------------------------------------------------------------------+
```

### 2.2 核心技术栈
- **前端框架**：Vue 3 (Composition API) + Vite
- **UI 组件库**：Element Plus (zh-cn 全局中文国际化)
- **图表可视化**：Apache ECharts + vue-echarts
- **后端服务**：Python 3.11 + FastAPI + Uvicorn + HTTPX（异步高性能 HTTP 客户端）
- **数据处理**：Pydantic v2（数据模型校验）
- **容器与交付**：Docker 多阶段构建 (Node.js 编译 -> Python 3.11-slim 运行)

---

## 3. 功能模块与页面设计

### 3.1 页面划分与核心功能

| 页面路由 | 模块名称 | 核心功能点 |
| :--- | :--- | :--- |
| `/dashboard` | **态势概览看板** | 1. 24h / 7d / 30d 聚合统计（提交量、通过量、阻断量、脱敏量、阻断率）；<br>2. 违规 Scanner 分布饼图；<br>3. 拦截趋势折线图；<br>4. 模型安全健康度雷达图。 |
| `/playground`| **实时护栏测试台** | 1. 交互式 Prompt 提交与策略调整；<br>2. 实时判定动作反馈（Allowed / Blocked / Masked）；<br>3. 敏感数据（PII）脱敏前后对比高亮卡片；<br>4. G01~G10 经典攻击预设用例一键载入测试；<br>5. 过滤后发往 LLM 的安全流式回复。 |
| `/redteam`   | **红队任务与报告** | 1. 历史评估任务列表与状态追踪（Completed, In Progress, Cancelling）；<br>2. 漏洞率与拒绝率多维看板；<br>3. 攻击手法穿透率（Static Content, Caesar, Base64 等）；<br>4. CSV 结果文件解析与图表展示；<br>5. 中文评估报告一键导出。 |
| `/audit`     | **安全审计日志** | 1. 安全事件流水检索（状态、扫描器、时间、客户端 IP）；<br>2. 事件详情抽屉（完整 Prompt、Mask 结果、判定耗时）。 |
| `/settings`  | **系统与连接配置** | 1. Calypso API Base URL 与 API Token 动态配置；<br>2. 接口连通性一键测试（Ping）；<br>3. 运行模式切换（真实集群模式 / 离线模拟演示模式）。 |

---

## 4. 后端 API 接口规格与数据流

### 4.1 接口列表定义

1. **`GET /api/v1/system/status`**
   - 返回当前 BFF 状态、运行模式（`online` 或 `demo`）以及 Calypso API 连通性状态。
2. **`POST /api/v1/system/config`**
   - 请求体：`{"base_url": str, "token": str, "project_id": Optional[str], "mode": str}`
   - 保存当前配置至会话，并测试目标集群可用性。
3. **`GET /api/v1/dashboard/metrics?timeframe={24h|7d|30d}&project_id={id}`**
   - 提取指定时间窗口的聚合指标与违规分布。
4. **`POST /api/v1/guardrails/scan`**
   - 请求体：`{"prompt": str, "project_id": Optional[str], "policy": Optional[dict]}`
   - 模式分支：
     - 若 `mode == "demo"`，由本地 Mock 引擎根据规则库计算结果；
     - 若 `mode == "online"`，调用 Calypso `POST /backend/v1/scans` 并规范化输出。
5. **`GET /api/v1/guardrails/presets`**
   - 返回 G01~G10 经典测试样例集合。
6. **`GET /api/v1/redteam/campaigns`**
   - 调用 `GET /backend/v1/campaigns` 与 `/backend/v1/campaign-runs`，返回结构化任务列表。
7. **`POST /api/v1/redteam/reports/analyze`**
   - 接收上传的 CSV 文件，解析攻击手法、漏洞率、错误类型并输出统计分析图表数据。
8. **`GET /api/v1/audit/logs`**
   - 调用 `GET /backend/v1/prompts` 或本地日志库，支持条件筛选与分页返回。

---

## 5. Docker 交付方案

### 5.1 Dockerfile 多阶段构建
- **前端构建阶段**：使用 `node:20-alpine` 安装依赖并执行 `npm run build`，编译输出至 `web/dist`。
- **运行时阶段**：使用 `python:3.11-slim`，安装依赖包，将 `web/dist` 静态资源拷贝至 `app/static`。
- **静态资源路由**：FastAPI 配置 `StaticFiles(directory="app/static", html=True)`，单端口即可同时提供 REST API 与前端单页应用。

### 5.2 启动与环境变量
- 端口：默认暴露 `8080`。
- 支持环境变量：
  - `CALYPSO_BASE_URL`（默认 `https://us1.calypsoai.app`）
  - `CALYPSO_API_TOKEN`（可选预置）
  - `APP_MODE`（默认 `online`，可选 `demo`）

---

## 6. 验证与质量保证计划

1. **接口自动化测试**：使用 `pytest` 覆盖 BFF 代理路由、Mock 模拟器、CSV 解析器。
2. **Mock 演示模式验证**：在无网络依赖下启动应用，验证 Dashboard 图表渲染、Playground 样例测试、Red Team 报告展示无报错。
3. **生产环境代理验证**：填入有效 Calypso API Token，验证 `/backend/v1/projects` 与 `/backend/v1/scans` 真实请求连通。
4. **Docker 镜像构建验收**：构建镜像并执行容器化启动验证：
   ```bash
   docker build -t calypso-chinese-ui:latest .
   docker run -d -p 8080:8080 calypso-chinese-ui:latest
   ```
   检查 `http://localhost:8080` 页面加载及健康检查状态。
