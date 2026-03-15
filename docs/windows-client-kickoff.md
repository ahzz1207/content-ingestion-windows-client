# `content-ingestion` Windows Client Kickoff v0.8

## 1. 目标

本仓库承载 `content-ingestion` 的 Windows 侧实现。

当前主目标仍然不是直接做完整 GUI，而是先把 Windows 到 WSL 的最小真实链路打稳：

```text
URL input
  -> collect or mock content
  -> export payload + metadata + READY
  -> write shared_inbox/incoming/<job_id>/
  -> hand off to existing WSL processor
```

---

## 2. 与现有 WSL 仓库的边界对齐

当前已有的 WSL Processor 已经具备：

- `validate-job`
- `validate-inbox`
- `watch-inbox --once`
- `process-job`
- `processed/` / `failed/` 标准输出

因此 Windows 侧当前仍然只负责：

- URL 输入
- 内容采集
- job 导出
- 与共享 inbox 的协议对齐

不在本仓库里实现：

- WSL 侧处理逻辑
- `processed/failed` 写入逻辑
- 标准化解析逻辑
- OpenClaw 接入逻辑

---

## 3. 当前默认配置

当前仓库已经支持默认配置：

- 默认 shared inbox：`data/shared_inbox`
- 默认 `content_type`：`html`
- 默认 `platform`：`generic`
- 浏览器默认 `headless=True`
- 浏览器默认 `wait_until=networkidle`
- 浏览器默认 `timeout_ms=30000`
- 浏览器默认 `settle_ms=1000`
- 浏览器 profile 根目录：`data/browser-profiles`

因此下面几个命令都已经接好：

```text
python main.py doctor
python main.py browser-login --start-url https://mp.weixin.qq.com/
python main.py export-mock-job https://example.com/article
python main.py export-url-job https://example.com/article
python main.py export-browser-job https://example.com/article
```

---

## 4. 当前命令面

### 4.1 `doctor`

输出：

- 当前仓库路径
- 当前 Python 可执行路径
- 当前版本
- 当前生效的 shared inbox 配置
- 默认 content type / platform
- 浏览器默认参数
- browser profiles 根目录
- browser collector 是否可用以及原因

### 4.2 `export-mock-job`

用途：

- 输入一个 URL
- 使用固定 mock 内容生成一个合法 job
- 写入默认或指定的 shared inbox

### 4.3 `export-url-job`

当前第一版真实 collector 已支持：

- 通过标准库 HTTP 抓取简单页面
- 自动识别 `html` / `txt` / `md`
- HTML 页面提取 `title_hint`
- 将结果导出为合法 job

当前限制：

- 只适合简单静态页面或可直接返回内容的 URL
- 不处理登录态
- 不处理 JS 渲染页面
- 不做平台特化抽取

### 4.4 `export-browser-job`

当前浏览器 collector 已支持：

- 通过 Playwright Chromium 打开页面
- 等待策略可配置：`load` / `domcontentloaded` / `networkidle` / `commit`
- 超时可配置：`--timeout-ms`
- 页面稳定等待可配置：`--settle-ms`
- 支持等待选择器：`--wait-for-selector`
- 支持选择器状态：`attached` / `visible` / `hidden` / `detached`
- 支持持久化 profile：`--profile-dir`
- 支持浏览器通道参数：`--browser-channel`
- 支持 `--headed`
- 输出 `payload.html`
- 提取 `platform`、`title_hint`、`author_hint`、`published_at_hint`
- 已支持真实微信公众号文章导出
- 对已识别的平台 URL 可自动复用默认 profile
- collector / exporter / CLI 已输出结构化错误码与错误细节

当前限制：

- 还没有更细的平台特化采集逻辑
- 还没有 GUI 侧的交互封装

### 4.5 `browser-login`

当前已支持：

- 打开一个 headed 持久化浏览器会话
- 支持自定义 `--start-url`
- 支持自定义 `--profile-dir`
- 支持 `--browser-channel`
- 支持 `--wait-until` 与 `--timeout-ms`
- 若省略 `--profile-dir`，会按平台或主机名自动选择 `data/browser-profiles/<slug>`

用途：

- 先手工完成登录或 profile 预热
- 后续由 `export-browser-job` 复用同一个 profile 抓取需要登录态的页面

---

## 5. 当前模块状态

### 5.1 `collector/`

当前已实现：

- `MockCollector`
- `HttpCollector`
- `BrowserCollector`
- HTML metadata 提取与平台识别
- 选择器等待能力

下一步候选：

- 平台特化 collector
- 登录态验证辅助输出
- 更细的抓取失败诊断

### 5.2 `job_exporter/`

当前已实现：

- `job_id` 生成
- metadata 组装
- payload / metadata / READY 的稳定写入顺序
- `ExportResult` 返回值
- URL / content type 基本校验

### 5.3 `app/`

当前已实现：

- `doctor`
- `browser-login`
- `export-mock-job`
- `export-url-job`
- `export-browser-job`

---

## 6. 当前测试覆盖

当前单元测试已覆盖：

1. `job_id` 生成格式
2. metadata 字段完整性
3. payload 后缀与 `content_type` 一致
4. 默认 shared inbox 生效
5. `source_url` 与 `content_type` 不一致时稳定报错
6. 非法 URL 输入时报错
7. service 默认配置导出路径
8. `doctor` 输出核心配置
9. HTTP collector 对 `html` / `txt` / `md` 的识别
10. HTTP 404 错误处理
11. browser collector 可用性判断
12. browser collector 缺运行时的显式失败行为
13. browser collector 在可用环境下的页面抓取
14. browser collector 的 `wait_until` / `settle_ms` 参数校验
15. browser collector 的持久化 profile 路径支持
16. `browser-login` 的默认 profile 路径选择
17. 已识别平台 URL 的自动 profile 复用
18. 通用 URL 默认保持无状态抓取
19. 默认 profile slug 对 host 的可读命名
20. 选择器等待参数透传与非法状态报错

---

## 7. 当前验证结论

当前已经完成这些验证：

1. Windows 原生 Python 下单元测试通过
2. `export-mock-job` 已联调到 WSL `processed/`
3. `export-url-job` 已通过本地 HTTP 页面联调到 WSL `processed/`
4. `export-browser-job` 已通过 Playwright 本地页面抓取联调到 WSL `processed/`
5. 带 `--profile-dir`、`--wait-until`、`--timeout-ms`、`--settle-ms` 的 browser 命令已完成本地验证
6. `doctor` 已能正确暴露浏览器默认参数和运行状态
7. 真实微信公众号文章 URL 已通过浏览器链路导出并成功进入 WSL `processed/`
8. 真实微信公众号文章 metadata 已能提取 `platform`、`title_hint`、`author_hint`、`published_at_hint`
9. 公众号 URL 在省略 `--profile-dir` 时，也已通过自动 profile 复用链路成功进入 WSL `processed/`

这意味着 Windows 侧已经从“纯 mock 导出器”进入“具备真实网页抓取、可复用 profile、支持选择器等待、并已验证公众号文章场景”的阶段。

---

## 8. 当前阶段判断

### Milestone 0: 对齐

- 已完成

### Milestone 1: 最小 mock exporter

- 已完成

### Milestone 1 polish

- 默认配置
- `doctor` 输出
- 输入校验
- 测试收尾
- 已完成

### Milestone 2 slice 1: 真实 URL collector

- 简单 HTTP collector
- `export-url-job`
- 与 WSL 联调
- 已完成

### Milestone 2 slice 2: 浏览器 collector

- Playwright collector
- `export-browser-job`
- 与 WSL 联调
- 已完成

### Milestone 2 slice 3: 浏览器运行时与 profile 工作流

- `profile-dir`
- `browser-channel`
- `wait_until`
- `timeout-ms`
- `settle-ms`
- `--headed`
- `browser-login`
- 已识别平台 URL 的默认 profile 复用
- 已完成

### Milestone 2 slice 4: 动态页面稳定性补强

- `wait-for-selector`
- `wait-for-selector-state`
- 已完成

---

## 9. 下一步建议

这部分保留为阶段性历史建议。
其中第 2 项已经落地到当前仓库的 GUI 适配层，当前真实的收口状态以 `docs/pre-gui-checkpoint-2026-03-14.md` 为准。

阶段性下一步曾经是三选一：

1. 给公众号等重点站点补更多真实 URL 手工样本，验证 profile / selector 策略
2. 开始设计 GUI 需要消费的最小状态与错误展示模型
3. 为成功路径补一层结构化事件日志，统一记录 profile 选择、等待策略与导出结果

补充边界文档：

- `docs/windows-wsl-handoff-contract.md`
  - 正式说明 Windows 应交给 WSL 的主 payload 枚举、metadata 分层、以及未来附件扩展策略
- `docs/pre-gui-checkpoint-2026-03-14.md`
  - 记录 GUI 开始前的冻结边界、验证基线、剩余风险与推荐切入点

当前建议跳转：

- `docs/pre-gui-checkpoint-2026-03-14.md`
  - 这是 GUI 开始前的最终收拢状态，应优先于本节的历史建议阅读

当前 GUI 准备状态：

- `src/windows_client/app/workflow.py`
  - 提供 GUI-facing 的操作适配层，统一返回成功/失败状态
- `src/windows_client/app/view_models.py`
  - 提供 doctor、job export、browser login、error 的最小 view model
- 当前推荐让 GUI 只调用 workflow，而不是直接绑定 CLI 输出或底层异常
