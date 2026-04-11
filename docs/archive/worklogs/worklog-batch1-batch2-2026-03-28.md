# Worklog — Batch 1 WSL Repair + Batch 2 Obsidian O1
**日期：** 2026-03-28
**仓库：** Windows (`H:/demo-win`) + WSL (`/home/ahzz1207/codex-demo`)
**状态：** 全部完成，验收通过，48 tests passed

---

## Batch 1 — WSL Repair

### W1 — processed/ 状态机修复

**问题：** job 先移入 `processed/`，再慢慢写 normalized/status/pipeline/analysis 文件，导致 Windows 侧读到半写状态。

**方案：** 引入 `finalizing/` 中间阶段：
```
incoming → processing → finalizing → processed
incoming → processing → failed
```
`processed/` 只在所有必要文件写完、通过 `_verify_required_outputs()` 检验后才移入。

**改动文件：**
- `src/content_ingestion/inbox/protocol.py`：新增 `FINALIZING_DIRNAME`、`SharedInboxPaths.finalizing`、`JobPaths.finalizing_dir`；`ensure_shared_inbox()` 创建 finalizing/ 目录
- `src/content_ingestion/inbox/processor.py`：重构 `process()` 为三阶段流程；新增 `_verify_required_outputs()`；`_handle_failure()` P1#2 修复（先定位 source_dir 再读 metadata）

**注意：** Windows 侧 `_load_result_entry` 的 `incomplete_result` 兜底分支**保留**，不在此批删除。

---

### W2 — Runtime data 迁出 repo worktree

**问题：** `data_dir` 默认在 `project_root/data/`，repo reset/clean 会带走运行数据。

**方案：** 默认路径改为 `~/.content-ingestion-wsl/`，支持 `CONTENT_INGESTION_DATA_DIR` env var override。

**改动文件：** `src/content_ingestion/core/config.py`

---

### W3a — visual_findings 独立字段

**问题：** multimodal 分支把 `visual_finding` 塞进 `analysis_items`，违反数据契约。

**方案：** `StructuredResult` 新增 `visual_findings: list[VisualFinding]` 字段；multimodal 结果写入该字段；`_serialize_structured_result()` 同步输出。

**改动文件：**
- `src/content_ingestion/core/models.py`：新增 `VisualFinding` dataclass（`id`, `finding`, `evidence_frame_paths`）；`StructuredResult.visual_findings`
- `src/content_ingestion/pipeline/llm_pipeline.py`：W3a 分离逻辑；`_serialize_structured_result()` 增加 `content_kind`、`author_stance`、`visual_findings` 输出
- `src/content_ingestion/inbox/processor.py`：processor 侧同步序列化 `visual_findings_payload`

---

### W3b — Bilibili Whisper language 参数化

**问题：** Bilibili 硬编码 `language=zh`，非中文视频识别结果质量差。

**方案：** `bilibili_whisper_language: str | None`；`None` = 不传 `--language`（Whisper 自动识别）；env var `CONTENT_INGESTION_BILIBILI_WHISPER_LANGUAGE` 显式设置时才强制指定。

**改动文件：**
- `src/content_ingestion/core/config.py`
- `src/content_ingestion/pipeline/media_pipeline.py`

---

### W3c — watcher interval 单一来源

**问题：** `--interval-seconds` CLI 默认值 `2.0` 与 service 层逻辑双写。

**方案：** CLI default 改为 `None`，由 service 层统一管理默认值。

**改动文件：**
- `src/content_ingestion/app/cli.py`
- `src/content_ingestion/app/service.py`

---

### 测试覆盖

新增两个测试用例（`tests/unit/test_processor.py`）：
- `test_handle_failure_rescue_from_finalizing_preserves_metadata` — 验证从 finalizing/ 救援时 error.json 保留 content_type / source_url / payload_filename
- `test_visual_findings_in_result_not_in_analysis_items` — 验证 visual_findings 独立于 analysis_items

**最终结果：** 48 tests passed

---

## Batch 2 — Obsidian O1 深化

### O1a — Source note frontmatter 完整

新增字段：`ingestion_date`（导入当天日期 `YYYY-MM-DD`）、`tags`（从插件设置 `defaultTags` 解析的字符串数组）

**改动文件：**
- `obsidian-plugin/importer.ts`：计算 `ingestionDate`、`tags` 并传入 `buildSourceNote`
- `obsidian-plugin/note-builders.ts`：接收并写入 frontmatter；`frontmatter()` 支持 `string | string[]` 值（YAML 数组格式）

### O1b — Digest note frontmatter 完整

新增字段：`verification_status`（`verified` / `partial` / `unverified`）、`key_point_count`（整数）、`analysis_model`

**改动文件：** `obsidian-plugin/note-builders.ts`：`deriveVerificationStatus()` helper；从 `structuredResult` 读取 `key_points`、`verification_items`、`analysis_model`

### O1c — StatusView "已导入" 标记（防误标）

只对 `status === "completed"` 且 vault 中存在匹配 `job_id` frontmatter 的文件时显示紫色 "已导入" chip；archived/failed job 不误标。

**改动文件：**
- `obsidian-plugin/main.ts`：`isJobImported(jobId)` 方法；`renderJobRow` 中条件渲染 chip
- `obsidian-plugin/styles.css`：`.content-ingestion-chip--imported { color: var(--color-purple); }`

### O1d — 重建 main.js + 端到端验证

```bash
npm run build  # obsidian-plugin/
# Copy to vault: .obsidian/plugins/content-ingestion/
```

端到端验证：Source + Digest 双注生成，frontmatter 完整，重复导入 upsert，"已导入" chip 正确显示。**验收通过。**

---

## 后续方向

- **Batch 3 A2**：WebSocket 替代 GUI polling（依赖 W1 processed/ 语义稳定）
- **WSL 全面功能升级**：挖掘处理结果质量上限，保证细节完美和稳定性（范围待对齐）
- **Q4 问题**：`completed` 但无有效 LLM 分析的质量场景，留作下阶段处理
