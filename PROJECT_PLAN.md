# Content Ingestion System — 项目规划

**Version:** 1.0
**Date:** 2026-03-16
**Author:** Claude Opus 4.6

---

## Context

这是一个**个人知识管道系统**，将碎片化的多源内容（公众号、视频、笔记等）转化为结构化、经过验证的知识资产，最终归档到 Obsidian。项目已有 Windows Client + WSL Processor 的双仓库原型，需要在此基础上演进。

用户核心诉求：**简洁、前卫、稳定的知识归档系统**。

### 设计决策

- **笔记结构**：主文件 + 原文存档（notes/ + sources/ 分离）
- **分析维度**：全维度（观点、背景、关联、验证、反驳、延伸阅读）
- **部署形态**：未来云端化（当前架构需向解耦方向演进）
- **知识整合**：自动打标 + 关联推荐（不修改已有笔记）

---

## 1. 整体架构演进

### v0 — 当前原型

```
Windows GUI → shared_inbox/ → WSL Processor → processed/
```

问题：紧耦合于 Win+WSL 文件系统，无法远程化。

### v1 — 服务化 + Obsidian

```
┌─────────────┐      HTTP API       ┌──────────────────┐
│  Client      │ ◄─────────────────► │  Processor       │
│  (GUI/CLI)   │   POST /jobs       │  (FastAPI)       │
│              │   GET  /jobs/{id}   │                  │
│              │   WS   /jobs/stream │  ┌────────────┐  │
└─────────────┘                     │  │ Collector   │  │
                                    │  │ Parser      │  │
                                    │  │ LLM Engine  │  │
                                    │  │ Obsidian    │  │
                                    │  │  Writer     │  │
                                    │  └────────────┘  │
                                    └──────────────────┘
                                            │
                                    ┌───────▼────────┐
                                    │ Obsidian Vault  │
                                    │  Inbox/         │
                                    │  Sources/       │
                                    │  Assets/        │
                                    │  Templates/     │
                                    └────────────────┘
```

### v2 — 云端化

```
多端 Client ──► Cloud API (同一套 FastAPI) ──► 远程/本地 Obsidian Vault
  (Desktop)         │                              (通过 Git 同步)
  (Web)             │
  (Mobile)          └──► OpenClaw (未来)
```

关键点：v1 的 FastAPI 服务化是 v2 云端化的前提。做好 v1 就自然可以迁移到云端。

---

## 2. 模块设计

### Module 1: Obsidian Writer

将 LLM 分析结果写入 Obsidian Vault，遵循「主文件 + 原文存档」结构。

**Vault 目录结构：**

```
vault/
├── Inbox/                    # 新采集的笔记落地区
│   └── 2026-03-16-文章标题.md
├── Sources/                  # 原文存档
│   └── 2026-03-16-文章标题.md
├── Assets/                   # 附件（图片、视频截帧、字幕）
│   └── 2026-03-16-文章标题/
├── Templates/                # 笔记模板
│   └── ingestion-note.md
└── Maps/                     # 自动生成的主题汇总（MOC，后期）
```

**主笔记结构（Inbox/）：**

```markdown
---
title: "文章标题"
source_url: "https://..."
platform: "wechat"
author: "作者名"
collected_at: 2026-03-16T10:30:00Z
content_type: article
tags:
  - AI
  - 大模型
  - 具身智能
related: []
status: inbox
---

## 摘要
LLM 生成的一段话摘要

## 核心观点
- 观点 1 ^ev-001
- 观点 2 ^ev-002

## 背景知识
LLM 补充的相关背景

## 事实验证
| 声明 | 验证结果 | 置信度 | 证据 |
|------|---------|--------|------|
| xxx  | 已验证   | 高     | ^ev-001 |

## 反驳与对立观点
- 反面论点 1
- 反面论点 2

## 延伸阅读
- [[相关笔记1]]
- 外部链接推荐

## 元数据
- 原文：[[Sources/2026-03-16-文章标题]]
- 采集时间：2026-03-16
- 处理耗时：12.3s
```

**原文存档（Sources/）：**

```markdown
---
title: "文章标题（原文）"
source_url: "https://..."
type: source
---

原始内容的 Markdown 转换...
```

### Module 2: LLM 分析引擎增强

当前的 LLM pipeline 已有摘要、验证能力。需要扩展至全维度：

| 维度 | 说明 | 实现方式 |
|------|------|---------|
| 核心观点 | 提取 3-7 个关键观点 | 已有，增强 |
| 背景知识 | 补充读者可能不知道的上下文 | 新增 prompt |
| 事实验证 | 对可验证声明做真实性判断 | 已有 |
| 反驳分析 | 呈现对立观点和潜在弱点 | 新增 prompt |
| 延伸推荐 | 推荐相关主题/概念 | 新增 prompt |
| 自动打标 | 生成 tags（领域、主题、实体） | 新增 prompt |
| 关联推荐 | 与 Vault 已有笔记的关联建议 | 新增模块（需读取 Vault 索引） |

**实现策略：** 单次 LLM 调用 + 结构化输出（JSON Schema），将所有维度合并到一个 prompt 中，避免多次调用带来的延迟和成本。

### Module 3: 自动打标 + 关联引擎

**打标：**
- LLM 在分析时直接输出 `tags` 字段
- 维护一个 `tag_taxonomy.json` 作为标签词表，引导 LLM 尽量复用已有标签
- 新标签自动加入词表

**关联推荐：**
- 构建 Vault 索引：扫描所有笔记的 frontmatter（title, tags, summary）
- 分析时将索引作为上下文传入 LLM，让其推荐 `related` 笔记
- 输出为 `[[wikilink]]` 格式，写入 frontmatter 的 `related` 字段
- **不修改已有笔记**——仅在新笔记中单向引用

### Module 4: 服务化改造（为云端化铺路）

**WSL Processor → FastAPI 服务：**

```
POST   /api/v1/jobs          # 提交采集任务
GET    /api/v1/jobs/{id}     # 查询任务状态和结果
WS     /api/v1/jobs/stream   # 实时进度推送
GET    /api/v1/health        # 健康检查
POST   /api/v1/vault/index   # 触发 Vault 索引更新
```

**保留 Inbox 模式作为备选：** 文件系统 Inbox 作为 fallback transport，当 HTTP 不可用时自动降级。

**Windows Client 改造：**
- `wsl_bridge.py` → `api_client.py`（HTTP 调用替代 `wsl.exe` 子进程）
- GUI 的 WebSocket 连接替代轮询，实现实时进度

---

## 3. 实施路线

### Phase 1: 修复 + 基础

> 目标：让现有代码能跑起来，修复 critical bugs

- [ ] 修复 WSL 端所有参数语法错误（8+ 文件）
- [ ] 修复 `_image_data_url` data URL 前缀
- [ ] 修复 `content_shape` 双赋值 bug
- [ ] 替换硬编码路径为环境变量
- [ ] 添加 `mypy` + CI 基础配置
- [ ] 引入 `logging` 替代 `print`

**验证：** `mypy --strict` 通过 + 全部单元测试通过

### Phase 2: Obsidian Writer

> 目标：完成核心的「采集 → Obsidian 笔记」闭环

- [ ] 实现 `ObsidianWriter` 模块（Vault 路径配置、模板引擎、frontmatter 生成）
- [ ] 实现 Markdown 笔记生成（主笔记 + 原文存档 + 附件目录）
- [ ] 实现 Obsidian wikilink 格式输出
- [ ] 端到端测试：URL → LLM 分析 → Obsidian 笔记文件

**验证：** 输入一个公众号 URL，Obsidian Vault 中生成符合模板的笔记文件

### Phase 3: LLM 增强 + 打标

> 目标：全维度分析 + 自动标签

- [ ] 扩展 LLM prompt schema（背景、反驳、延伸阅读维度）
- [ ] 实现自动打标（`tag_taxonomy.json` 词表管理）
- [ ] 实现 Vault 索引构建（扫描 frontmatter）
- [ ] 实现关联推荐（基于索引的 LLM 推荐）
- [ ] LLM 调用添加 timeout + 重试

**验证：** 笔记自动带 tags，且 `related` 字段正确关联已有笔记

### Phase 4: 服务化

> 目标：WSL Processor 改为 FastAPI 服务，Client 通过 HTTP 调用

- [ ] WSL Processor 添加 FastAPI 入口
- [ ] 实现 Job API（提交/查询/WebSocket 推送）
- [ ] Windows Client 添加 `api_client.py` 替代 `wsl_bridge.py`
- [ ] 保留 Inbox 模式作为 fallback
- [ ] GUI 适配 HTTP + WebSocket

**验证：** `curl POST /api/v1/jobs` 提交任务 → WebSocket 收到进度 → 笔记生成

### Phase 5: 稳定化 + 云端准备

> 目标：为云端部署做准备

- [ ] Docker 化 Processor 服务
- [ ] 添加认证（API key / JWT）
- [ ] Vault 通过 Git 同步到远程
- [ ] OpenClaw 适配器对接（预留接口）
- [ ] Web 客户端（可选）

**验证：** `docker-compose up` 启动服务，远程 Client 可连接

---

## 4. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| API 框架 | FastAPI | 异步、自带 OpenAPI 文档、WebSocket 支持 |
| Markdown 生成 | 纯字符串模板 | Obsidian 的 Markdown 简单，不需要重型库 |
| Vault 索引 | 轻量 JSON 索引文件 | 扫描 frontmatter 生成，避免引入数据库 |
| 标签词表 | `tag_taxonomy.json` | 简单、可版本控制、LLM 可直接消费 |
| HTML 解析 | BeautifulSoup4 | 替代当前的 regex 方案，更健壮 |
| 类型检查 | mypy (strict) | 防止再次出现参数命名类 bug |

---

## 5. 相关文档

- [CODE_REVIEW.md](./CODE_REVIEW.md) — 两个仓库的详细代码审查报告

 转录方案对比

  你当前用的 openai-whisper 的问题

  1. 不支持说话人分离（diarization） —
  所有发言者的内容混在一起，无法区分"谁说了什么"
  2. 推理速度慢 — 比 faster-whisper 慢 4-8 倍
  3. 容易产生幻觉 — 遇到静音段会编造文本
  4. 无 VAD（语音活动检测） — 会处理大量静音/背景噪音

  推荐方案：WhisperX

  WhisperX 是目前最佳的一体化方案，三阶段管道：

  音频 → faster-whisper（转录）→ wav2vec2（词级对齐）→ pyannote（说话人分离）

  ┌────────────┬────────────────────────────┬───────────────────────────┐
  │   对比项   │       openai-whisper       │         WhisperX          │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ 转录引擎   │ 原版 whisper               │ faster-whisper（快 4-8x） │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ 说话人分离 │ 不支持                     │ 支持（via pyannote）      │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ 词级时间戳 │ 基础                       │ 精确（wav2vec2 对齐）     │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ 幻觉控制   │ 差                         │ VAD 预处理，大幅减少      │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ GPU 内存   │ ~10GB (large-v3)           │ <8GB (large-v2, beam=5)   │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ 输出格式   │ SRT/VTT/JSON               │ 带 speaker ID 的分段 JSON │
  ├────────────┼────────────────────────────┼───────────────────────────┤
  │ 安装       │ pip install openai-whisper │ pip install whisperx      │
  └────────────┴────────────────────────────┴───────────────────────────┘

  实际输出效果对比：

  openai-whisper:
  [00:00 - 00:30] 今天我们聊的话题是大模型在医疗领域的落地最近有几个比较重要的进
  展我们团队做了两年实验

  WhisperX:
  [00:00 - 00:15] [Speaker A]
  今天我们聊的话题是大模型在医疗领域的落地。最近有几个比较重要的进展。
  [00:15 - 00:30] [Speaker B] 我们团队做了两年实验...

  云端备选：AssemblyAI

  如果不想自建 GPU 环境，AssemblyAI 是最优云端选择：
  - $0.21/小时，内置 diarization
  - 185 小时免费额度
  - 自带 LLM 后处理网关（摘要、实体提取）
  - 适合轻量使用或作为 fallback

  我的建议：Hybrid 路径

  本地优先: WhisperX（faster-whisper + pyannote）
      ↓ 如果无 GPU 或需要更高质量
  云端降级: AssemblyAI API
      ↓ 统一输出
  标准化转录格式（带 speaker ID + 时间戳）
      ↓
  Content-Shape-Aware 预处理
      ↓
  LLM 分析