---
type: research
created: 2026-03-25
status: active
tags:
  - 架构分析
  - 知识管线
  - LLM
source:
  - "https://github.com/ahzz1207/content-ingestion-wsl-processor"
  - "https://github.com/ahzz1207/content-ingestion-windows-client"
---
# Content Ingestion 架构分析

## 系统定位

个人知识摄取管线。从多种内容源（微信公众号、B站/YouTube、网页）采集原始内容，经 LLM 结构化分析后输出**可溯源、可验证**的知识资产。

## 架构总览

双仓库 Windows + WSL 架构，通过共享文件系统通信。

```
Windows Client                    WSL Processor
─────────────                    ─────────────
URL → PlatformRouter             InboxWatcher (轮询)
  → Collector (HTTP/Playwright)    → JobProcessor 管线:
  → 微信图片/yt-dlp视频下载           ① HTML/MD/TXT 解析
  → JobExporter                      ② ffmpeg + Whisper 转写
  → shared_inbox/incoming/           ③ LLM 结构化分析
     ├── metadata.json               ④ 证据验证 + 自动修复
     ├── payload.html                ⑤ 多模态验证（视频帧）
     ├── attachments/                ⑥ 输出 normalized.json/md
     └── READY ← 哨兵         → shared_inbox/processed/
                    ↑                         │
WSLBridge ──────────┘         ResultWorkspace ←┘
(wsl.exe 子进程)              → InsightBriefV2 → GUI 展示
```

**四阶段目录协议：** `incoming → processing → processed / failed`
- `READY` 哨兵文件标志任务就绪
- `shutil.move()` 实现原子认领（同文件系统内）

## 技术栈

| 维度 | Windows Client | WSL Processor |
|------|---------------|---------------|
| 语言 | Python 3.10+ | Python 3.10+ |
| 核心依赖 | **零依赖**（仅 stdlib） | beautifulsoup4, lxml |
| 可选依赖 | PySide6, Playwright, yt-dlp | openai, playwright |
| HTML 解析 | 正则表达式 | BeautifulSoup |
| 外部服务 | 无 | OpenAI API, ffmpeg, Whisper |

## 核心设计理念

### 1. 证据驱动分析（最突出亮点）

- 每段原始内容生成确定性证据段 ID：`kind-source-seq-SHA1[:8]`
- LLM 每个结论必须引用证据段，系统自动校验引用有效性
- 少量无效引用 → 重新调用 LLM 修复；大量无效 → 降级为警告
- 证据反向链接索引支持结论到原文的双向溯源

### 2. 渐进式能力降级

- 无 Playwright → HTTP 采集
- 无 yt-dlp → 跳过视频
- 无 PySide6 → CLI only
- 每个能力均有 `is_available()` + `availability_reason()` 检查

### 3. 内容形状感知的 LLM 策略

根据内容类型自动选择分析策略：
- `article_text_first_v1` — 文章，支持 text/image/text_image
- `audio_text_only_v1` — 音频，仅 text
- `video_text_first_v1` — 视频，支持 text/text_image

使用 OpenAI Responses API 的 `json_schema` 模式约束输出结构。

### 4. 展示规划系统

后端生成 `display_plan`（分区/色调/优先级/展示模式），前端通过 `InsightBriefV2` 渲染。后端与前端清晰解耦。

## 模块拆解

### Windows Client 核心模块

| 模块 | 职责 |
|------|------|
| `config/settings.py` | 集中配置，环境变量读取 |
| `app/service.py` | 业务编排，三种导出模式（mock/url/browser） |
| `app/workflow.py` | GUI 适配层，异常安全的视图状态转换 |
| `app/wsl_bridge.py` | WSL 子进程调用、watcher 管理、路径转换、环境变量透传 |
| `collector/` | HTTP/Playwright/Mock 三种采集器 + 元数据提取 + 微信图片下载 |
| `job_exporter/` | job_id 生成、payload/metadata/manifest/READY 打包 |
| `video_downloader/` | yt-dlp 封装，支持 audio/video 模式 |
| `gui/` | PySide6 桌面应用：URL 输入 → 进度追踪 → 结果展示 |
| `app/result_workspace.py` | 从 processed/ 读取结果，构建 InsightBriefV2 |

### WSL Processor 核心模块

| 模块 | 职责 |
|------|------|
| `core/` | 配置、数据模型（ContentAsset 25+ 字段）、证据 ID 生成、异常 |
| `inbox/protocol.py` | 收件箱协议、路径遍历防护、job 校验 |
| `inbox/watcher.py` | 轮询扫描、原子认领 |
| `inbox/processor.py` | **核心管线**（~900 行）：解析→媒体→LLM→输出 |
| `raw/` | HTML 解析（微信去噪/容器提取/块结构化）、MD/TXT 解析、字幕解析（VTT/SRT/LRC/B站XML） |
| `pipeline/llm_contract.py` | LLM 交互契约：内容策略 → 任务规格 → 请求信封 |
| `pipeline/llm_pipeline.py` | LLM 调用 + 结构化结果解析 + 证据校验修复 + 多模态验证 |
| `pipeline/media_pipeline.py` | ffmpeg 音频/帧提取 + Whisper 转写 |
| `normalize/` | 文本清洗、Markdown 渲染、元数据附加 |

## 现有问题

### 架构层

| 问题 | 影响 |
|------|------|
| 单线程轮询 + 同步处理 | 大文件阻塞后续任务 |
| 无持久化状态（全靠 glob） | 大量任务时查询慢 |
| `shutil.move()` 跨文件系统非原子 | NTFS↔ext4 间可能数据丢失 |
| processor.py ~900 行 | 职责过重，难维护 |

### 工程层

| 问题 | 影响 |
|------|------|
| Client HTML 解析全靠正则 | 格式不规范时出错 |
| WSL Bridge 拼接 shell 命令 | 特殊字符路径有隐患 |
| LLM 无重试/无错误分类 | rate limit 等场景直接失败 |
| 微信去噪规则硬编码 | 无法适应前端更新 |
| 图片 base64 内嵌请求 | 高分辨率帧有内存风险 |
| GUI 样式硬编码在 Python 中 | ~100 行 CSS 嵌在字符串里 |

## 改进路线

### P0 — 立即可做

**MCP Server 化**
- 将 Content Ingestion 封装为 MCP Server
- 暴露 `ingest_url`、`query_knowledge`、`get_evidence` 等工具
- 任何 AI Agent（Claude Code、Cursor 等）直接调用，融入 AI 工作流

**Docker 化部署**
- 消除 Windows + WSL 强依赖，macOS/Linux 也能用
- 通信协议可从文件系统升级为 HTTP API

### P1 — 质变升级

**知识图谱 + 向量检索**
- 引入向量数据库（ChromaDB）对证据段做 embedding
- 跨文章主题聚合、观点对比、知识演化追踪
- 分析新文章时自动关联历史阅读

**SQLite 持久化**
- 任务状态、历史记录、搜索过滤、统计分析
- 替代目录遍历式查询

### P2 — 深度进化

**Agentic 多步分析**
- 从单轮 LLM 调用升级为多步 Agent 工作流：
  - 内容理解 Agent → 事实核查 Agent → 深度分析 Agent → 归档 Agent
- 利用 Tool Use 让 Agent 自主决定搜索、对比、深挖

**多模态原生**
- 直接用多模态大模型分析视频帧 + 音频
- 图片理解从"提取 alt"升级为"视觉内容理解"

**实时进度推送**
- WebSocket/SSE 替代客户端轮询
- 每个管线步骤实时上报

### P3 — 长期愿景

**前端现代化**
- PySide6 → Web 应用（Next.js / Tauri）
- 移动端支持：分享链接即触发采集
- 流式展示 LLM 分析过程

**知识 OS**
- Obsidian 深度集成：结果自动创建笔记、更新链接图谱
- 订阅机制：关注公众号/频道，定时采集分析
- 推荐系统：基于阅读历史推荐相关内容
