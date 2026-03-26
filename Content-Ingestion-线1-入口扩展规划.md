---
title: "Content Ingestion 入口扩展规划"
type: research
created: 2026-03-26
status: active
area: "[[Content-Ingestion-架构分析]]"
tags: [research, content-ingestion, chrome-extension, ios-shortcuts, obsidian-plugin]
---
# Content Ingestion — 线1: 入口扩展规划

## 概述

当前 Content Ingestion 系统仅支持 Windows 客户端（PySide6 GUI）的手动 URL 输入。本规划将入口扩展到三个新渠道：**Chrome 扩展**、**iOS 快捷指令**、**Obsidian 插件**，使用户在任意场景下都能一键将内容送入处理管线。

核心设计原则：所有新入口通过统一的 **本地 HTTP API Server** 与 WSL Processor 通信，避免每个入口都实现独立的 IPC 协议。

---

## 架构总览

```
┌─────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Chrome 扩展  │  │ iOS 快捷指令  │  │ Obsidian 插件    │
│ (Manifest V3)│  │ (Shortcuts)  │  │ (TypeScript)    │
└──────┬───────┘  └──────┬───────┘  └────────┬────────┘
       │ HTTP POST       │ HTTP POST          │ HTTP POST
       ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────┐
│              Local HTTP API Server                   │
│         (FastAPI, localhost:19527)                   │
│  POST /api/v1/ingest   — 提交 URL                   │
│  GET  /api/v1/jobs/:id — 查询状态                    │
│  GET  /api/v1/jobs     — 列出任务                    │
│  GET  /api/v1/health   — 健康检查                    │
└──────────────────────┬──────────────────────────────┘
                       │ File-based IPC
                       ▼
┌─────────────────────────────────────────────────────┐
│              WSL Processor Pipeline                  │
│   shared_inbox → incoming → processing → processed  │
└─────────────────────────────────────────────────────┘
```

---

## 模块一：本地 HTTP API Server

### 为什么不用 Native Messaging

| 维度 | Native Messaging | 本地 HTTP Server |
|------|-----------------|-----------------|
| 适用范围 | 仅 Chrome 扩展 | Chrome + iOS + Obsidian + CLI + 任意 HTTP 客户端 |
| 实现复杂度 | 每个浏览器需独立适配 | 一次实现，多端复用 |
| 调试难度 | stdio 管道，难以手动测试 | curl 即可测试 |
| 跨平台 | 需要 host manifest 注册 | 标准 HTTP，无注册 |
| 安全性 | 浏览器沙箱内 | 需要 localhost 绑定 + token |

**结论**: 本地 HTTP Server 是更优方案，一次建设、多端受益。

### 技术选型

- **框架**: FastAPI (已在 processor 依赖链中)
- **绑定**: `127.0.0.1:19527` (仅本机可访问)
- **认证**: Bearer Token (首次启动生成，存储在 `~/.content-ingestion/api_token`)
- **进程模型**: 作为 Windows 客户端的子进程启动，或独立 systemd/launchd 服务

### API 设计

#### `POST /api/v1/ingest`

提交一个 URL 进行处理。

```json
// Request
{
  "url": "https://example.com/article",
  "options": {
    "priority": "normal",       // normal | high
    "extract_mode": "auto",     // auto | article | video | audio
    "tags": ["AI", "research"], // 可选标签
    "callback_url": null        // 可选回调 URL
  }
}

// Response 201 Created
{
  "job_id": "job_20260326_143052_a1b2c3d4",
  "status": "queued",
  "created_at": "2026-03-26T14:30:52Z",
  "estimated_wait": 30
}
```

#### `GET /api/v1/jobs/{job_id}`

查询单个任务状态。

```json
// Response 200
{
  "job_id": "job_20260326_143052_a1b2c3d4",
  "url": "https://example.com/article",
  "status": "processing",      // queued | processing | completed | failed
  "stage": "llm_analysis",     // fetch | extract | llm_analysis | display_plan
  "progress": 0.65,
  "created_at": "2026-03-26T14:30:52Z",
  "updated_at": "2026-03-26T14:31:22Z",
  "result": null,              // 完成后包含摘要
  "error": null
}
```

#### `GET /api/v1/jobs`

列出所有任务，支持分页和过滤。

```
GET /api/v1/jobs?status=completed&limit=20&offset=0
```

#### `GET /api/v1/health`

```json
// Response 200
{
  "status": "ok",
  "version": "0.2.0",
  "wsl_connected": true,
  "active_jobs": 2,
  "uptime_seconds": 3600
}
```

### Server 实现要点

```python
# api_server.py — 核心结构

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
import uvicorn
import asyncio
from pathlib import Path

app = FastAPI(title="Content Ingestion API", version="0.2.0")
security = HTTPBearer()

# Token 验证
def verify_token(credentials = Depends(security)):
    token_path = Path.home() / ".content-ingestion" / "api_token"
    expected = token_path.read_text().strip()
    if credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid token")

# 任务队列：内存 + 文件双写
class JobManager:
    def __init__(self, shared_inbox: Path):
        self.shared_inbox = shared_inbox
        self.jobs: dict[str, Job] = {}

    async def submit(self, url: str, options: dict) -> Job:
        job_id = self._generate_id()
        job = Job(id=job_id, url=url, status="queued")
        self.jobs[job_id] = job

        # 写入 shared_inbox，触发 WSL processor
        request_file = self.shared_inbox / f"{job_id}.json"
        ready_file = self.shared_inbox / f"{job_id}.json.READY"
        request_file.write_text(json.dumps({...}))
        ready_file.touch()  # sentinel file

        return job

    async def poll_status(self, job_id: str) -> Job:
        # 检查 processed/ 和 failed/ 目录
        ...

# 启动
def start_server(host="127.0.0.1", port=19527):
    uvicorn.run(app, host=host, port=port)
```

### 文件结构

```
content-ingestion-api-server/
├── api_server.py          # FastAPI 主入口
├── job_manager.py         # 任务管理（提交、状态轮询）
├── auth.py                # Token 生成与验证
├── models.py              # Pydantic 数据模型
├── config.py              # 配置管理（端口、路径等）
├── requirements.txt       # fastapi, uvicorn, pydantic
└── tests/
    ├── test_api.py
    └── test_job_manager.py
```

---

## 模块二：Chrome 扩展

### 功能设计

1. **一键发送**: 在任意网页点击扩展图标 → 当前页面 URL 发送到本地 API
2. **右键菜单**: 选中链接 → 右键 "Send to Content Ingestion"
3. **状态徽章**: 扩展图标显示队列中的任务数量
4. **弹出面板**: 显示最近提交的任务列表和状态

### Manifest V3 结构

```json
{
  "manifest_version": 3,
  "name": "Content Ingestion",
  "version": "0.1.0",
  "description": "一键将网页内容送入知识处理管线",
  "permissions": [
    "activeTab",
    "contextMenus",
    "storage"
  ],
  "host_permissions": [
    "http://127.0.0.1:19527/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "background": {
    "service_worker": "background.js"
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

### 核心逻辑

```javascript
// background.js — Service Worker

const API_BASE = "http://127.0.0.1:19527/api/v1";

// 从 storage 读取 token
async function getToken() {
  const { apiToken } = await chrome.storage.local.get("apiToken");
  return apiToken;
}

// 提交 URL
async function submitUrl(url, options = {}) {
  const token = await getToken();
  try {
    const response = await fetch(`${API_BASE}/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ url, options })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const job = await response.json();

    // 更新徽章
    await updateBadge();

    // 显示通知
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "已提交处理",
      message: `${url.substring(0, 60)}...`
    });

    return job;
  } catch (error) {
    // 服务器未运行时的友好提示
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "连接失败",
      message: "请确认 Content Ingestion 服务正在运行"
    });
  }
}

// 点击扩展图标
chrome.action.onClicked.addListener(async (tab) => {
  if (tab.url && !tab.url.startsWith("chrome://")) {
    await submitUrl(tab.url);
  }
});

// 右键菜单
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "send-to-ingestion",
    title: "发送到 Content Ingestion",
    contexts: ["page", "link"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const url = info.linkUrl || info.pageUrl;
  if (url) await submitUrl(url);
});

// 定期更新徽章（显示队列数量）
async function updateBadge() {
  try {
    const token = await getToken();
    const resp = await fetch(`${API_BASE}/jobs?status=queued,processing`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await resp.json();
    const count = data.total || 0;
    chrome.action.setBadgeText({ text: count > 0 ? String(count) : "" });
    chrome.action.setBadgeBackgroundColor({ color: "#4A90D9" });
  } catch { /* 静默失败 */ }
}

// 每 10 秒更新一次
setInterval(updateBadge, 10000);
```

### 弹出面板

```html
<!-- popup.html -->
<!DOCTYPE html>
<html>
<head>
  <style>
    body { width: 360px; font-family: system-ui; padding: 12px; }
    .job { padding: 8px; border-bottom: 1px solid #eee; }
    .job-url { font-size: 13px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .job-status { font-size: 11px; margin-top: 4px; }
    .status-queued { color: #999; }
    .status-processing { color: #4A90D9; }
    .status-completed { color: #27AE60; }
    .status-failed { color: #E74C3C; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .send-btn { background: #4A90D9; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
    #settings-link { font-size: 12px; color: #999; cursor: pointer; }
    .empty { text-align: center; color: #999; padding: 20px; }
  </style>
</head>
<body>
  <div class="header">
    <button class="send-btn" id="send-current">📥 发送当前页面</button>
    <span id="settings-link">⚙️ 设置</span>
  </div>
  <div id="jobs-list">
    <div class="empty">暂无任务</div>
  </div>
  <script src="popup.js"></script>
</body>
</html>
```

### 文件结构

```
chrome-extension/
├── manifest.json
├── background.js         # Service Worker
├── popup.html            # 弹出面板
├── popup.js              # 面板逻辑
├── options.html          # 设置页（Token 配置）
├── options.js
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── styles/
    └── popup.css
```

---

## 模块三：iOS 快捷指令

### 设计思路

iOS 快捷指令（Shortcuts）可以通过 Share Sheet 拦截任意 App 的分享动作，将 URL 发送到指定 HTTP 端点。

**关键限制**: iOS 快捷指令只能访问公网 URL，无法直接调用 `localhost`。

### 方案：Tailscale / Cloudflare Tunnel

```
iPhone → Share Sheet → Shortcut
  → HTTP POST https://your-tunnel.trycloudflare.com/api/v1/ingest
  → Cloudflare Tunnel → localhost:19527
  → Local API Server → WSL Processor
```

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| Tailscale | 端对端加密，零配置隧道 | 需要两端都安装 Tailscale |
| Cloudflare Tunnel | 免费，无需客户端 | 需要 cloudflared 守护进程 |
| ngrok | 简单快速 | 免费版 URL 不固定 |
| 自建 VPN | 完全控制 | 维护成本高 |

**推荐**: Tailscale（最简单安全）或 Cloudflare Tunnel（零客户端依赖）

### 快捷指令构建步骤

```
快捷指令名称: Send to Ingestion

触发方式: Share Sheet (接受 URL、文本)

步骤:
1. [接收] 从 Share Sheet 获取输入
2. [条件] 如果输入是 URL → 直接使用
         如果输入是文本 → 检查是否包含 URL → 提取
3. [网络请求]
   - URL: https://<tunnel-domain>/api/v1/ingest
   - 方法: POST
   - Headers:
     - Content-Type: application/json
     - Authorization: Bearer <token>
   - Body (JSON):
     {
       "url": [输入的URL],
       "options": {
         "tags": ["mobile"],
         "priority": "normal"
       }
     }
4. [解析] 获取 JSON 响应中的 job_id
5. [通知] 显示 "已提交: [job_id]"
6. [可选] 添加到提醒事项 "稍后查看处理结果"
```

### 安全设计

- API Token 存储在快捷指令的 "文本" 动作中（不外泄）
- Tunnel 层面可额外配置 IP 白名单
- 建议在 API Server 增加 rate limiting (每分钟 10 次)

---

## 模块四：Obsidian 插件

### 功能设计

1. **命令面板**: `Ctrl+P` → "Ingest URL" → 粘贴 URL → 提交
2. **内联链接**: 在笔记中选中 URL → 右键 "Ingest this URL"
3. **侧边栏面板**: 显示任务队列和处理状态
4. **自动嵌入**: 处理完成后在当前笔记插入结果摘要（Callout 格式）

### 插件结构

```
obsidian-content-ingestion/
├── main.ts               # 插件主入口
├── settings.ts           # 设置面板（API 地址、Token）
├── api-client.ts         # HTTP 客户端封装
├── ingest-modal.ts       # URL 输入弹窗
├── status-view.ts        # 侧边栏状态面板
├── result-formatter.ts   # 将结果格式化为 Obsidian Markdown
├── manifest.json
├── package.json
├── tsconfig.json
├── esbuild.config.mjs
└── styles.css
```

### 核心代码

```typescript
// main.ts
import { Plugin, Notice, MarkdownView } from "obsidian";
import { IngestModal } from "./ingest-modal";
import { StatusView, VIEW_TYPE_STATUS } from "./status-view";
import { ApiClient } from "./api-client";
import { IngestionSettings, DEFAULT_SETTINGS, SettingTab } from "./settings";

export default class ContentIngestionPlugin extends Plugin {
  settings: IngestionSettings;
  apiClient: ApiClient;

  async onload() {
    await this.loadSettings();
    this.apiClient = new ApiClient(this.settings);

    // 注册命令：提交 URL
    this.addCommand({
      id: "ingest-url",
      name: "提交 URL 到 Content Ingestion",
      callback: () => new IngestModal(this.app, this).open()
    });

    // 注册命令：提交选中文本中的 URL
    this.addCommand({
      id: "ingest-selected-url",
      name: "提交选中的 URL",
      editorCallback: async (editor) => {
        const selection = editor.getSelection();
        const urlMatch = selection.match(/https?:\/\/[^\s)]+/);
        if (urlMatch) {
          await this.submitUrl(urlMatch[0]);
        } else {
          new Notice("未在选中文本中找到 URL");
        }
      }
    });

    // 注册侧边栏视图
    this.registerView(
      VIEW_TYPE_STATUS,
      (leaf) => new StatusView(leaf, this)
    );

    // 添加设置面板
    this.addSettingTab(new SettingTab(this.app, this));

    // Ribbon 图标
    this.addRibbonIcon("inbox", "Content Ingestion", () => {
      this.activateView();
    });
  }

  async submitUrl(url: string, tags?: string[]) {
    try {
      const job = await this.apiClient.ingest(url, { tags });
      new Notice(`已提交: ${job.job_id}`);

      // 如果设置了自动嵌入，启动轮询
      if (this.settings.autoEmbed) {
        this.pollAndEmbed(job.job_id);
      }
    } catch (error) {
      new Notice(`提交失败: ${error.message}`);
    }
  }

  async pollAndEmbed(jobId: string) {
    const maxAttempts = 60;  // 最多等 5 分钟
    for (let i = 0; i < maxAttempts; i++) {
      await sleep(5000);
      const job = await this.apiClient.getJob(jobId);
      if (job.status === "completed") {
        await this.embedResult(job);
        return;
      }
      if (job.status === "failed") {
        new Notice(`处理失败: ${job.error}`);
        return;
      }
    }
    new Notice("处理超时，请稍后在侧边栏查看");
  }

  async embedResult(job: any) {
    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
    if (!view) return;

    const editor = view.editor;
    const cursor = editor.getCursor();

    // 格式化为 Obsidian Callout
    const callout = [
      "",
      `> [!abstract] ${job.result.title}`,
      `> **来源**: [${job.url}](${job.url})`,
      `> **处理时间**: ${job.updated_at}`,
      `> `,
      ...job.result.summary.split("\n").map((l: string) => `> ${l}`),
      "",
    ].join("\n");

    editor.replaceRange(callout, cursor);
    new Notice("已嵌入处理结果");
  }
}
```

```typescript
// api-client.ts
export class ApiClient {
  private baseUrl: string;
  private token: string;

  constructor(settings: IngestionSettings) {
    this.baseUrl = settings.apiUrl || "http://127.0.0.1:19527/api/v1";
    this.token = settings.apiToken;
  }

  private async request(path: string, options: RequestInit = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.token}`,
        ...options.headers,
      },
    });
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  async ingest(url: string, options?: { tags?: string[]; priority?: string }) {
    return this.request("/ingest", {
      method: "POST",
      body: JSON.stringify({ url, options }),
    });
  }

  async getJob(jobId: string) {
    return this.request(`/jobs/${jobId}`);
  }

  async listJobs(params?: { status?: string; limit?: number }) {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/jobs?${query}`);
  }

  async health() {
    return this.request("/health");
  }
}
```

```typescript
// settings.ts
export interface IngestionSettings {
  apiUrl: string;
  apiToken: string;
  autoEmbed: boolean;
  defaultTags: string[];
}

export const DEFAULT_SETTINGS: IngestionSettings = {
  apiUrl: "http://127.0.0.1:19527/api/v1",
  apiToken: "",
  autoEmbed: true,
  defaultTags: [],
};
```

---

## 实施路线图

### 第一阶段：本地 HTTP API Server（1-2 天）

- [ ] 实现 FastAPI 服务框架
- [ ] 实现 `/ingest` 和 `/jobs` 端点
- [ ] 对接 shared_inbox 文件 IPC
- [ ] Token 生成与验证
- [ ] 编写 API 测试
- [ ] 集成到 Windows 客户端作为子进程启动

### 第二阶段：Chrome 扩展（1-2 天）

- [ ] Manifest V3 项目搭建
- [ ] 实现 background service worker
- [ ] 实现 popup 面板（任务列表 + 状态）
- [ ] 右键菜单集成
- [ ] 连接测试 + 错误处理
- [ ] 打包并加载到 Chrome 测试

### 第三阶段：Obsidian 插件（2-3 天）

- [ ] 插件项目搭建（esbuild + TypeScript）
- [ ] 命令面板 + URL 输入模态框
- [ ] 侧边栏状态面板
- [ ] 自动嵌入结果到笔记
- [ ] 设置面板
- [ ] 本地测试

### 第四阶段：iOS 快捷指令（0.5 天）

- [ ] 配置 Cloudflare Tunnel 或 Tailscale
- [ ] 构建 Shortcut 流程
- [ ] Share Sheet 测试
- [ ] 文档化设置步骤

---

## 依赖关系

```
HTTP API Server ──► Chrome 扩展
       │
       ├──────► Obsidian 插件
       │
       └──────► iOS 快捷指令 (需额外配置 Tunnel)
```

API Server 是所有入口的基础，必须首先完成。

---

## 相关

- [[Content-Ingestion-架构分析]] — 系统架构研究
- [[Content-Ingestion-线2-功能深度规划]] — 功能深度增强
- [[Content-Ingestion-线3-用户体验规划]] — 用户体验改进
