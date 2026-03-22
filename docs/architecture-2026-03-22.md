# 系统架构文档 — 2026-03-22 (Preview 1.0 Baseline)

> 本文档记录当前系统的完整架构、数据契约、设计决策和已知问题。

---

## 1. 系统概览

两个仓库协同工作：

| 仓库 | 路径 | 职责 |
|------|------|------|
| Windows 客户端 | `H:\demo-win` | PySide6 GUI、浏览器采集、视频下载、任务打包、结果展示 |
| WSL 处理端 | `/home/ahzz1207/codex-demo` | HTML 解析、Whisper 转录、LLM 分析流水线 |

共享收件箱：`H:\demo-win\data\shared_inbox` = `/mnt/h/demo-win/data/shared_inbox`

---

## 2. 任务生命周期

```
URL → PlatformRouter → Collector (browser/http/yt-dlp)
    → JobExporter → shared_inbox/incoming/<job_id>/
    → WSL Watcher (2s) → Parser → LLM Pipeline
    → normalized.json + analysis_result.json
    → Windows 轮询 → InsightBriefV2 → InlineResultView
```

任务触发条件：incoming/<job_id>/ 下同时存在 metadata.json + payload.* + READY。

---

## 3. StructuredResult schema (LLM 输出契约)

```
summary: { headline, short_text }
key_points: [ { id, title, details, evidence_segment_ids } ]
analysis_items: [ { id, kind(implication|alternative), statement, confidence } ]
verification_items: [ { id, claim, status(supported|partial|unsupported|unclear), rationale } ]
synthesis: { final_answer, next_steps[], open_questions[] }
```

---

## 4. InsightBriefV2 字段映射

| InsightBriefV2 字段 | 来源 |
|---|---|
| hero.title | summary.headline |
| hero.one_sentence_take | summary.short_text |
| viewpoints(key_point) | statement=kp.title, why_it_matters=kp.details |
| viewpoints(analysis) | statement=item.statement |
| viewpoints(verification) | statement=item.claim, support_level=item.status |
| gaps | synthesis.open_questions + synthesis.next_steps |
| synthesis_conclusion | synthesis.final_answer |

修复(2026-03-22)：key_point 之前错误地将 kp.details 存为 statement，why_it_matters 永远 None。

---

## 5. LLM Prompt 4目标框架

1. OVERVIEW — 主题 + 作者立场 (summary)
2. VIEWPOINTS — 每个论点 + 3-5句解读 (key_points, 5-10条)
3. CRITICAL CHECK — 值得质疑的声明 (verification_items)
4. DIVERGENT THINKING — 隐含结论/反向视角 (analysis_items, kind=implication|alternative)

参数变更(2026-03-22)：key_points 3-6→5-10条，details 1-2句→3-5句，移除字数限制，
evidence_segments 上限 40→100。

---

## 6. GUI 布局 InlineResultView (从上到下)

Top Bar: [New URL] [Re-analyze] [历史记录]
Hero Card: 标题 + 一句话概括(18px) + byline + 来源链接 + chips
精华卡片: Gemini PNG（可选）
作者观点: 编号标题(加粗) + 详细解读(缩进)
Fact Check: 仅 unsupported/partial/unclear 条目
Bottom Line: synthesis.final_answer
延伸思考: → implication/alternative 条目
Questions & Next Steps: · open_questions + next_steps
警告横幅: 覆盖率不足 / 图片截断
Browser: 仅降级路径显示
Action Row: [Open Folder] [Export JSON] [Copy] [Save]

---

## 7. 历史记录面板导航流

Ready Page
  [History] → History Dialog
               [查看完整分析]/双击 → InlineResultView
                                      [历史记录]
                                        → 先切回 Ready Page
                                        → History Dialog (定位当前条目)
                                            关闭 → Ready Page
                                            查看 → InlineResultView (新条目)

---

## 8. WSL 状态指示

后台线程 + _status_ready Signal (queued connection，线程安全)。
注意：QTimer.singleShot 在非主线程不绑定主线程事件循环，必须用 Signal。
每15秒 tasklist 轻量轮询，状态变化才触发完整刷新。
Pills: WSL 处理中 ● / WSL 已停止 ○ / WSL 未启动 ○

---

## 9. subprocess 规范

所有 Windows subprocess 必须加 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)。
已覆盖：wsl_bridge (_run_command/tasklist/taskkill)、yt_dlp_downloader、cli (launcher)。

---

## 10. 资源上限

llm_max_evidence_segments: 100 | document.blocks: 80 | wechat_max_images: 8 | multimodal_max_frames: 8

---

## 11. Preview 1.0 状态

完成:
- 完整采集链路 (WeChat/Bilibili/YouTube/通用网页)
- LLM 4目标分析框架
- InsightBriefV2 结构化展示
- Gemini 精华卡片
- WSL 状态实时指示
- 历史记录面板双向导航
- 全链路 CREATE_NO_WINDOW

规划中:
- Obsidian 导出
- LLM 日期注入 (修复"当前2024年")
- 历史面板自动刷新
- 批量重分析
