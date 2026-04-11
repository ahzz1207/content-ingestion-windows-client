# Windows Client Handoff - 2026-03-13

## 1. 当前阶段

今天的目标是把 Windows 侧从“可跑的最小浏览器导出器”继续推进到“更适合真实公众号场景的稳定抓取链路”。

到今天结束时，项目已经处于这个状态：

- Windows 侧可用命令已经包括 `doctor`、`export-mock-job`、`export-url-job`、`browser-login`、`export-browser-job`
- `export-browser-job` 已可处理真实微信公众号文章 URL
- 浏览器 profile 预热、默认 profile 复用、选择器等待都已经接好
- Windows 导出的 job 已多次成功进入现有 WSL Processor 的 `processed/`

一句话总结：

Windows 侧现在已经不是“纯原型”，而是一个能对真实 URL 做稳定联调的 CLI 基线。

---

## 2. 今天完成的工作

### 2.1 环境与基线确认

- 确认了 Windows 原生 Python 可用路径：
  `C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe`
- 确认了 Playwright Python 包与 Chromium 浏览器运行时可用
- 之后的 Windows 原生验证都已经基于这套环境完成

### 2.2 浏览器登录预热流程

新增了 `browser-login` 命令，用于手工打开持久化浏览器会话，完成登录或 profile 预热。

行为：

- 默认打开 `https://mp.weixin.qq.com/`
- 默认使用 headed 持久化浏览器会话
- 若省略 `--profile-dir`，会自动落到 `data/browser-profiles/<slug>`

这一层的意义是：

- 后续抓需要登录态的页面时，可以复用同一个浏览器 profile
- 对公众号等页面，后面不需要每次都从“纯净浏览器”重新开始

### 2.3 默认 profile 命名与复用

今天把 profile 的默认策略从“手动指定为主”推进成了“默认尽量帮用户选对”。

规则如下：

- 若 URL 已识别为已知平台，例如微信公众平台，则优先使用平台名
- 若是通用网站，则按 host 生成可读 slug
- 若 `export-browser-job` 遇到已识别平台 URL，且未显式传 `--profile-dir`，会自动复用对应默认 profile

当前效果：

- `browser-login --start-url https://mp.weixin.qq.com/`
  默认会落到 `data/browser-profiles/wechat`
- `export-browser-job https://mp.weixin.qq.com/s/...`
  在未传 `--profile-dir` 时，也会自动走 `data/browser-profiles/wechat`

这一步是今天最关键的体验优化之一。

### 2.4 公众号场景 metadata 提取增强

浏览器导出链路已经稳定补出这些 metadata：

- `platform`
- `title_hint`
- `author_hint`
- `published_at_hint`

真实公众号文章联调时，已经成功提取到：

- 平台：`wechat`
- 标题：`直击霍尔木兹&油运`
- 作者：`热点投研`
- 发布时间：`2026年3月12日 23:56`

### 2.5 动态页面稳定性补强

今天又新增了选择器等待能力，用于动态页面或结构加载稍慢的页面。

`export-browser-job` 现在新增支持：

- `--wait-for-selector`
- `--wait-for-selector-state`

当前支持的 selector state：

- `attached`
- `visible`
- `hidden`
- `detached`

这意味着后续我们可以对不同平台逐步沉淀更稳的抓取策略，而不是只依赖 `wait_until` + `settle_ms`。

---

## 3. 今天涉及的主要代码点

核心实现主要落在这些文件：

- `src/windows_client/collector/browser.py`
- `src/windows_client/app/service.py`
- `src/windows_client/app/cli.py`
- `tests/unit/test_browser_collector.py`
- `tests/unit/test_service.py`
- `README.md`
- `docs/windows-client-kickoff.md`

其中可以特别关注：

- `browser.py`
  负责浏览器抓取、profile 打开、默认 profile slug 规则、selector wait
- `service.py`
  负责把“平台识别 -> 默认 profile 选择 -> collector 调用 -> exporter 输出”串起来
- `cli.py`
  负责把这些能力暴露成命令面

---

## 4. 今天完成的验证

### 4.1 单元测试

Windows 原生 Python 下已通过：

- `30` 个测试全部通过

这说明今天新加的几层能力都已经有测试兜底：

- `browser-login`
- 默认 profile slug
- WeChat 默认 profile 复用
- selector wait 参数透传
- selector state 非法值报错

### 4.2 CLI 自检

已验证：

- `python main.py doctor`
- `python main.py browser-login --help`
- `python main.py export-browser-job --help`

其中 `doctor` 当前能输出：

- 项目根目录
- Python 可执行路径
- shared inbox 路径
- browser profiles 根目录
- 浏览器默认参数
- browser collector 是否可用

### 4.3 Windows -> WSL 真实联调

今天至少完成了这些真实链路验证：

1. 真实微信公众号文章 URL，带显式 `--profile-dir`，成功进入 WSL `processed/`
2. 真实微信公众号文章 URL，不传 `--profile-dir`，走自动 profile 复用，成功进入 WSL `processed/`
3. 真实微信公众号文章 URL，带 `--wait-for-selector '#js_content'`，成功进入 WSL `processed/`

今天确认成功的 job id 包括：

- `20260313_010721_0f251d`
- `20260313_011519_3143eb`

这说明当前主链路已经覆盖：

- 浏览器抓取
- metadata 生成
- Windows inbox job 输出
- WSL validate-job
- WSL watch-inbox --once
- WSL processed 落盘

---

## 5. 当前可直接使用的关键命令

### 5.1 环境检查

```powershell
& "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe" main.py doctor
```

### 5.2 预热微信 profile

```powershell
& "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe" main.py browser-login --start-url https://mp.weixin.qq.com/
```

### 5.3 导出真实公众号文章

```powershell
& "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe" main.py export-browser-job "https://mp.weixin.qq.com/s/0PWXUXZ1uObGrnK_ES8qMQ"
```

### 5.4 导出真实公众号文章并等待正文节点

```powershell
& "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe" main.py export-browser-job "https://mp.weixin.qq.com/s/0PWXUXZ1uObGrnK_ES8qMQ" --wait-for-selector "#js_content" --wait-until domcontentloaded --timeout-ms 45000 --settle-ms 1500
```

---

## 6. 当前已知观察

### 6.1 控制台中文显示可能乱码

在 PowerShell 或 WSL 控制台里直接查看某些 JSON / Markdown 文件时，中文有时会显示成乱码。

当前判断：

- 更像是终端编码显示问题
- 不是 job 文件本身坏掉
- 不是 WSL Processor 处理失败

因为：

- 真实联调是成功的
- metadata / processed 产物都能正常生成

这个问题后面值得继续收一下查看体验，但不阻塞主链路开发。

### 6.2 `watch-inbox --once` 会处理队列里的全部待处理 job

这不是 bug，但要记得：

- 如果 `incoming/` 里已经积压了多个 job
- 一次 `watch-inbox --once` 可能会连续输出多个 `job_output=...`

排查时不要误以为是“当前命令多跑了一个别的 job”。

---

## 7. 当前阶段判断

今天结束后，Windows 侧更准确的阶段描述是：

- Milestone 0：完成
- Milestone 1：完成
- Milestone 1 polish：完成
- Milestone 2 slice 1：完成
- Milestone 2 slice 2：完成
- Milestone 2 slice 3：完成
- Milestone 2 slice 4：完成

其中 Milestone 2 slice 4 指的是：

- 选择器等待
- 默认 profile 复用体验补强
- 对真实公众号场景的进一步稳态验证

---

## 8. 明天最顺的继续方向

明天建议优先做下面三件事之一，按优先级我更推荐前两项：

1. 结构化错误码和日志
   目标是让抓取失败时更容易看出是 URL 问题、浏览器问题、等待超时、selector 不存在，还是 exporter 协议问题。

2. 公众号等目标站点的真实样本补充
   继续积累几条真实 URL，逐步沉淀 profile / wait 策略，避免只在单条样本上“碰巧可用”。

3. GUI 需要消费的最小状态模型
   如果后面要做 GUI，可以先定义命令执行结果、错误展示字段、任务状态的最小结构。

如果明天直接继续开发，我建议从第 1 项开做。

---

## 9. 明天如何快速恢复上下文

明天只要先让我读这几份文件，我就能快速续上：

- `docs/windows-handoff-2026-03-13.md`
- `docs/windows-client-kickoff.md`
- `README.md`

如果还想让我直接接着改代码，再补一句：

“按 handoff 文档继续推进结构化错误日志”

我就能直接开始。
