# 产品演进路线图 2026

**版本：** 1.0
**日期：** 2026-03-22
**状态：** Preview 1.0 已发布，开始规划下一阶段

---

## 0. 当前基线（Preview 1.0）

当前系统是一个本地单机工具：Windows PySide6 GUI + WSL 处理引擎，通过共享文件系统 inbox 通信。

核心能力已验证：
- 多平台内容采集（微信、Bilibili、YouTube、通用 URL）
- LLM 4-goal 结构化分析（概述 / 观点 / 事实核查 / 发散思考）
- InsightBriefV2 结构化结果展示
- 历史记录面板 + 双向导航

**架构图：**

```
Windows GUI (PySide6)
    │
    ├── Browser Collector (Playwright)
    ├── HTTP Collector
    ├── yt-dlp Downloader
    │
    └── shared_inbox/ ──► WSL Processor
                              │
                              ├── HTML Parser
                              ├── Whisper Transcription
                              ├── LLM Pipeline (OpenAI / Gemini)
                              └── processed/ ──► GUI 读取展示
```

**已知限制：**
- 仅限本地 Windows + WSL，无法远程访问
- 手动提交 URL，无自动采集
- 结果停留在 GUI，无知识沉淀
- 无 24h 无人值守处理能力

---

## 1. 三大演进方向

本路线图围绕三个互相关联的方向展开：

```
Direction A: 架构重构 ── 前端升级 + 后端服务化 + 云端部署
Direction B: Obsidian 集成 ── 将分析结果接入知识管理体系
Direction C: Agent 自动采集 ── 24h 实时抓取 + 自动入队处理
```

**依赖关系：**

```
Direction A（API 服务化）
    └── 是 Direction C（Agent 接入）的前提
         └── Agent 产出的内容通过 Direction B 落入 Obsidian

Direction B（Obsidian）
    └── 可与 Direction A 并行推进（基于文件系统，不依赖云端）
```

**最终形态：**

```
多端 Client (Web / Desktop / Mobile)
    │
    ▼
Cloud API (FastAPI, 24h 运行)
    │
    ├── 手动提交任务
    ├── Agent 自动推送任务 (OpenClaw / RSS / 监控)
    │
    ▼
处理引擎 (内容采集 + LLM 分析)
    │
    ├── 结果推送给 Client（WebSocket 实时进度）
    └── 自动写入 Obsidian Vault（知识沉淀）
            │
            └── 每日摘要推送 (Bark / Telegram)
```

---

## 2. Direction A：架构重构

### 2.1 前端框架迁移

**现状问题：**
- PySide6 桌面应用，仅限 Windows，无法多端访问
- 分发和更新成本高
- 前端开发上限低（动画、响应式、协作等难以实现）

**目标框架：Next.js + TypeScript + Tailwind CSS**

选型理由：
- 同一套前端代码可跑 Web + Electron 包装为桌面应用
- TypeScript 全栈类型安全，与 FastAPI 的 Pydantic schema 天然对应
- Vercel 部署零配置
- SSR 支持 SEO（未来知识产品方向）
- React 生态完整（富文本、图表、动画库丰富）

**迁移策略（渐进，不停机）：**
1. 保留 PySide6 GUI 不变，继续作为本地使用入口
2. 新建 `web/` 目录，独立 Next.js 项目
3. Web 前端对接 FastAPI 后端（Direction A2）
4. 功能对齐后，PySide6 逐步退出，最终仅保留 CLI 入口

**页面映射（PySide6 → Next.js）：**

| PySide6 页面 | Next.js 页面 | 新增能力 |
|---|---|---|
| Task Page（URL 输入 + 进度）| `/analyze` | WebSocket 实时进度条 |
| InlineResultView（结果展示）| `/results/[job_id]` | 分享链接、打印友好 |
| ResultWorkspacePanel（历史）| `/history` | 搜索、筛选、批量操作 |
| WSL 状态 pills | 顶栏 status badge | 处理速率、队列长度 |
| — | `/settings` | API key、Obsidian vault 路径、通知配置 |

### 2.2 后端服务化

**现状问题：**
- 处理依赖本地 WSL，必须保持 Windows 机器开机
- 文件系统 inbox 不支持远程客户端
- 无认证，仅限本地访问

**目标：FastAPI 服务（本地可运行 + 可云部署）**

**API 设计：**

```
POST   /api/v1/jobs              # 提交 URL 任务
GET    /api/v1/jobs/{id}         # 查询任务状态 + 结果
WS     /api/v1/jobs/{id}/live    # 实时进度推送
GET    /api/v1/jobs              # 历史列表（带分页、筛选）
DELETE /api/v1/jobs/{id}         # 删除任务

POST   /api/v1/ingest            # Agent webhook（Direction C 专用）

GET    /api/v1/health            # 健康检查（含 LLM 连通性）
GET    /api/v1/status            # 处理引擎状态（队列长度、处理中数量）
```

**认证：**
- Phase 1：单 API Key（`X-API-Key` header），环境变量注入
- Phase 2：多用户 JWT（如需团队协作）

**数据持久化演进：**

| 阶段 | 任务数据 | 结果文件 |
|---|---|---|
| 本地开发 | SQLite | 本地磁盘（现有 processed/ 结构）|
| 云端 v1 | SQLite（持久卷）| 挂载持久卷 |
| 云端 v2 | PostgreSQL | Cloudflare R2（S3 兼容）|

**迁移策略：**
1. WSL Processor 新增 `main.py serve` 命令（启动 FastAPI + Uvicorn）
2. 现有 `watch-inbox` 模式保留为 fallback transport
3. Windows Client 的 `WslBridge` → `ApiClient`（HTTP 调用替代 wsl.exe 子进程）
4. Docker 化：`Dockerfile` + `docker-compose.yml`

### 2.3 云端部署

**云平台选型：Railway 或 Fly.io**

选型理由：
- 便宜（$5-20/月起）
- 支持持久化磁盘（结果文件存储）
- 原生支持 Docker 部署
- 无 GPU 限制（Whisper 用 CPU 运行或调用 AssemblyAI）

**部署架构：**

```
Railway / Fly.io
    ├── app service (FastAPI + Processor)
    ├── persistent volume (/data/shared_inbox)
    └── environment variables (API keys, config)

Cloudflare R2（可选，后期扩容用）
    └── 结果文件对象存储
```

### 2.4 实施阶段

| 阶段 | 目标 | 关键交付 | 依赖 |
|---|---|---|---|
| A1 | FastAPI 封装现有 pipeline | POST /jobs + GET /jobs/{id} 可用 | — |
| A2 | WebSocket 实时进度 | 替换 GUI 轮询逻辑 | A1 |
| A3 | Windows Client 适配 HTTP | WslBridge → ApiClient | A1 |
| A4 | Docker 化 + 本地云测试 | docker-compose up 全链路可用 | A1-A3 |
| A5 | 云端部署 | Railway/Fly.io 上线，24h 处理 | A4 |
| A6 | Next.js Web 前端初版 | 核心用户流程（提交 + 查看结果）| A1-A2 |
| A7 | Next.js 完整版 | 历史 / 设置 / Obsidian 操作 | A6, O1 |

---

## 3. Direction B：Obsidian 知识管理

> 详细设计见 [`docs/obsidian-integration-roadmap-2026-03-16.md`](obsidian-integration-roadmap-2026-03-16.md)

### 3.1 产品定位

```
Windows Client / Web   = 操作入口 + 内容采集 shell
处理引擎 (WSL / Cloud) = 规范化 + LLM 分析引擎
Obsidian Vault         = 知识操作系统（长期归档 + 比较 + 发布）
```

Obsidian 不替代处理管道，而是作为**下游知识工作区**，接收处理结果并支持：
- 跨内容比较与关联
- 话题追踪与演化
- 用户标注与精炼
- 知识产品输出（报告、公开分享）

### 3.2 知识对象模型

每次处理产出三类 Obsidian 对象：

```
Source Note  → 01 Sources/YYYY-MM-DD-标题.md
               含原文 markdown、采集元数据

Digest Note  → 02 Digests/YYYY-MM-DD-标题.md
               含 LLM 分析（key_points、verification、synthesis）
               链接到 Source Note

Assets       → Assets/YYYY-MM-DD-标题/
               insight card PNG、视频截帧、字幕文件
```

### 3.3 Digest Note 模板（核心交付物）

```markdown
---
type: digest
job_id: 20260322_123456_abc123
source_url: https://...
platform: wechat
author: 作者名
published_at: 2026-03-22
captured_at: 2026-03-22T12:34:56Z
title: 文章标题
headline: LLM 生成的一句话标题
tags: [AI, 大模型]
status: inbox
topics: []
related: []
---

## 一句话

{{hero.one_sentence_take}}

## 作者观点

{{#each key_points}}
**{{index}}. {{title}}**
{{details}}
{{/each}}

## 事实核查

{{#each verification_items where status != supported}}
- ⚠️ {{claim}} — {{rationale}}
{{/each}}

## 底线

{{synthesis.final_answer}}

## 延伸思考

{{#each analysis_items}}
→ {{statement}}
{{/each}}

## 问题 & 下一步

{{#each gaps}}
· {{.}}
{{/each}}

---
原文：[[01 Sources/{{date}}-{{slug}}]]
```

### 3.4 GUI 集成

在 InlineResultView action row 新增：

- **保存到 Obsidian**：调用 `ObsidianWriter.write_digest()`，写入 vault
- **在 Obsidian 中打开**：写入后执行 `obsidian://open?vault=...&file=...` deep-link

### 3.5 技术实现（O1 阶段核心模块）

新建于 WSL 仓库：`src/content_ingestion/obsidian/writer.py`

```python
class ObsidianWriter:
    def __init__(self, vault_root: Path): ...
    def write_digest(self, entry: ResultWorkspaceEntry, brief: InsightBriefV2) -> Path: ...
    def write_source(self, entry: ResultWorkspaceEntry) -> Path: ...
    def copy_assets(self, entry: ResultWorkspaceEntry, target_dir: Path) -> list[Path]: ...
    def obsidian_uri(self, note_path: Path) -> str: ...
```

### 3.6 实施阶段

| 阶段 | 目标 | 关键交付 |
|---|---|---|
| O1 | Vault Export | `ObsidianWriter` 模块，Source + Digest 笔记生成，资产复制 |
| O2 | GUI 深度链接 | "保存到 Obsidian" 按钮 + URI 跳转，vault 路径配置 |
| O3 | Metadata-First | Properties schema 稳定，Bases 视图配置（按 platform / status / tags 筛选）|
| O4 | 主题图谱 | Topic / Entity / Claim 笔记自动生成，`.canvas` 关系可视化 |
| O5 | 伴随插件 | Obsidian plugin（promote → synthesis，mark for publish，cross-source canvas）|

---

## 4. Direction C：Agent 自动采集

### 4.1 目标

让内容采集从「手动提交 URL」演进为「24h 自动发现 + 智能入队处理」。

**集成对象：** OpenClaw 或同类 agent 平台（网页监控 / RSS 订阅 / 语义搜索爬取）

### 4.2 Ingest API 端点

基于 Direction A 的 HTTP API，新增：

```
POST /api/v1/ingest
Content-Type: application/json
X-API-Key: {agent-key}

{
  "url": "https://...",
  "source": "openclaw",
  "priority": "normal",          // normal | high
  "topics": ["AI", "大模型"],    // agent 给出的分类提示
  "triggered_by": "rss",         // rss | search | monitor | schedule
  "agent_note": "..."            // agent 附加的上下文（可选）
}
```

Response：
```json
{
  "job_id": "20260322_...",
  "status": "queued",
  "deduplicated": false,          // true 表示此 URL 近期已处理
  "existing_job_id": null         // 如果 deduplicated=true，返回已有 job_id
}
```

### 4.3 去重机制

- **URL 规范化**：去 UTM 参数、解析 canonical URL、统一协议 (http→https)
- **处理记录索引**：`processed_urls` 表（canonical_url, processed_at, job_id）
- **去重窗口**：同一 canonical URL 在配置天数内不重复处理（默认 7 天，可 per-source 配置）
- **内容变更检测**（可选）：对比 content hash，有变化则忽略去重窗口强制重新分析

### 4.4 优先级队列

```
HIGH       ← 用户手动提交（立即处理）
MEDIUM     ← Agent 标记 priority=high
LOW        ← Agent 标记 priority=normal（默认）
BACKGROUND ← 批量回填 / 历史补录
```

队列实现：
- **本地**：asyncio 优先级队列（无额外依赖）
- **云端扩展**：ARQ（Redis-backed）支持多 worker 并发

### 4.5 通知机制

Agent 提交的任务完成后自动触发：

| 通知渠道 | 场景 | 内容 |
|---|---|---|
| **Bark（iOS Push）** | 单条高优先级完成 | 标题 + 一句话摘要 |
| **Telegram Bot** | 批量完成 / 摘要推送 | 格式化摘要（支持 Markdown）|
| **Webhook 回调** | OpenClaw 请求回调 | POST 到 agent 配置的 callback_url |
| **每日摘要** | 定时推送（每天 22:00）| 当日处理内容汇总（含标题、来源、关键观点）|

### 4.6 订阅管理（Web UI）

在 Next.js 前端 `/settings/subscriptions` 页面：

- 添加 RSS 源（URL + 过滤关键词）
- 配置关键词监控（新闻 / 微信公众号 / 学术）
- 查看 Agent 提交历史 + 成功率
- 配置去重窗口 / 优先级规则

### 4.7 每日摘要格式

```
📊 今日内容摘要 · 2026-03-22

共处理 12 条内容 · 来自 OpenClaw(8) 手动(4)

🔥 高优先级
· [微信] 大模型 2026 年行业报告 — 作者认为...
· [YouTube] OpenAI CTO 访谈 — 核心观点：...

📌 今日主题
· AI 基础设施 (5 条) · 量化投资 (3 条) · 医疗 AI (2 条)

⚠️ 待关注
· 2 条内容包含未验证声明
· 1 条处理失败（网络超时）
```

### 4.8 实施阶段

| 阶段 | 目标 | 关键交付 | 依赖 |
|---|---|---|---|
| I1 | HTTP Ingest 端点 | POST /api/v1/ingest，去重逻辑，优先级队列 | A1 |
| I2 | OpenClaw 适配器 | 官方 webhook 对接，优先级映射，callback | I1 |
| I3 | 通知系统 | 完成推送（Bark + Telegram），webhook 回调 | I1 |
| I4 | 订阅管理 UI | Web 前端配置 RSS / 关键词监控 / 去重规则 | I1, A6 |
| I5 | 每日摘要 | 定时任务生成 + 推送 daily digest | I1, I3 |

---

## 5. 整体里程碑

```
2026 Q1 末 ✅
    Preview 1.0 发布
    PySide6 GUI + LLM 4-goal 分析 + 历史面板 + WSL 状态指示器

2026 Q2
    O1  Obsidian Vault Export（Source + Digest 笔记生成）
    O2  GUI 深度链接（保存到 Obsidian 按钮 + URI 跳转）
    A1  FastAPI 封装现有 pipeline（POST /jobs + GET /jobs/{id}）
    A2  WebSocket 实时进度（替换 GUI 轮询）
    A3  Windows Client 适配 HTTP API

2026 Q3
    A4  Docker 化 + 本地验证
    A5  云端部署（Railway/Fly.io，24h 无人值守处理）
    O3  Obsidian Properties + Bases 视图
    I1  HTTP Ingest 端点 + 去重机制
    I2  OpenClaw 适配器
    A6  Next.js Web 前端初版（核心流程）

2026 Q4
    I3  通知系统（Bark + Telegram）
    I4  订阅管理 UI
    O4  主题图谱（Topic / Entity / Claim 笔记）
    A7  Next.js 完整版（取代 PySide6 成为主入口）

2027 Q1+
    O5  Obsidian 伴随插件
    I5  每日摘要自动化
    多用户 / 团队协作（按需）
```

---

## 6. 技术选型

| 组件 | 选型 | 理由 |
|---|---|---|
| Web 前端 | Next.js 15 + TypeScript + Tailwind CSS | 全栈 React，Vercel 零配置部署，长期上限最高 |
| 桌面包装（可选）| Electron | 用 Web 代码打包桌面应用，复用同一套前端 |
| 后端 API | FastAPI + Uvicorn | 异步，自带 OpenAPI 文档，WebSocket 原生支持 |
| 实时推送 | WebSocket（FastAPI 原生）| 替换现有 GUI 轮询，延迟从秒级降到毫秒级 |
| 任务队列 | asyncio 优先级队列 → ARQ（Redis）| 本地轻量，云端可扩展 |
| 数据库 | SQLite → PostgreSQL | 本地开发无需配置，云端迁移 Postgres |
| 对象存储 | 本地磁盘 → Cloudflare R2 | 便宜（$0.015/GB），S3 兼容，CDN 加速 |
| 云部署 | Railway 或 Fly.io | 便宜，持久磁盘，Docker 原生，无 GPU 限制 |
| 推送通知 | Bark（iOS）+ Telegram Bot | 成熟，API 简单，中文友好 |
| 转录引擎 | WhisperX（本地 GPU）/ AssemblyAI（云）| 说话人分离，速度快 4-8x，幻觉少 |
| Obsidian 集成 | 文件系统 + URI scheme | 最简单，无插件依赖，用户完全掌控文件 |

---

## 7. 可复用的现有资产

架构重构无需从零开始，以下核心资产直接复用：

| 资产 | 位置 | 复用方式 |
|---|---|---|
| 内容收集器（browser / http / yt-dlp）| `src/windows_client/collector/` | 封装为 FastAPI handler，逻辑不变 |
| LLM pipeline（OpenAI + Gemini）| WSL `pipeline/llm_pipeline.py` | 直接调用，无需修改 |
| InsightBriefV2 数据模型 | `src/windows_client/app/insight_brief.py` | Web 前端 API response schema 直接对应 |
| normalized.json + analysis_result.json | 处理产出物 | 作为 API 响应的 data payload |
| 单元测试（129 passing）| `tests/unit/` | 继续覆盖新 API handler，防止回归 |
| Obsidian 集成详细设计 | `docs/obsidian-integration-roadmap-2026-03-16.md` | O1-O5 阶段详细执行计划 |
| 架构参考 | `docs/architecture-2026-03-22.md` | JSON schema、数据契约、已知 caps |

---

## 8. 参考文档

| 文档 | 内容 |
|---|---|
| [`architecture-2026-03-22.md`](architecture-2026-03-22.md) | 当前系统完整架构（JSON schema、数据契约、caps）|
| [`obsidian-integration-roadmap-2026-03-16.md`](obsidian-integration-roadmap-2026-03-16.md) | Obsidian 集成五阶段详细规划 |
| [`changelog-2026-03-22.md`](changelog-2026-03-22.md) | Preview 1.0 改动详情 |
| [`PROJECT_PLAN.md`](../PROJECT_PLAN.md) | 早期架构草图（v1 服务化 + v2 云端化）|
