# 开发计划 — Post Phase 0 基线

**整理日期：** 2026-03-28
**基线 commit：** 2462d18（Phase 0 boundary repair 完成）
**参考文件：** `docs/preview1-boundary-repair-plan-2026-03-27.md`

---

## 当前状态

### Phase 0 已完成（Windows 仓库）

| 项目 | 内容 | 测试 |
|------|------|------|
| Archive 语义 | `DELETE /jobs/{id}` 移动到 `archived/`，不再物理删除 | ✓ |
| Archived 结果读取 | GUI 历史、API result_card、`/jobs/{id}/result` 全部支持 archived job | ✓ |
| Archived 错误保留 | archived failed job 的 error.json 消息完整透传 | ✓ |
| Shared root 可见性 | `/health` 返回 `shared_inbox_root` + `watcher` 块；Obsidian StatusView、Chrome/Edge popup 均展示 | ✓ |
| Watcher 状态诊断 | 异常时暴露真实 `str(exc)` 而非固定字符串 | ✓ |
| Obsidian thumbnail 兜底撤除 | `importer.ts` 只接受真正的 `insight_card` | ✓ |
| 客户端文案统一 | 所有客户端 Delete → Archive，确认文案同步 | ✓ |

**测试基线：** 187 passed（Windows），41 passed（WSL）

---

## Batch 1 — WSL Repair

**仓库：** `/home/ahzz1207/codex-demo`
**原则：** 单仓库完成、验收后再开下一批；Windows 侧兜底逻辑在此批保留不动

### W1 — processed/ 状态机修复（P0）

**文件：** `src/content_ingestion/inbox/processor.py`（参见当前 line 53-61）

**问题：** job 先移入 `processed/`，再异步写 normalized/status/pipeline/analysis 文件，导致 Windows 侧读到半写状态。

**方案：** 引入 `finalizing/` 中间阶段

```
incoming → processing → finalizing → processed
incoming → processing → failed
```

- job 进入 `processing/` 后开始所有处理
- 处理完成写完所有文件后，先移入 `finalizing/`
- 确认以下文件全部存在后，再原子性移入 `processed/`：
  - `normalized.json`
  - `normalized.md`
  - `pipeline.json`
  - `status.json`
- 任何阶段异常 → 移入 `failed/`

**Windows 侧说明：** `job_manager.py` 的 `_load_result_entry` 中 `incomplete_result` 兜底分支**此批保留**，等 WSL finalizing 机制跑稳后再删。

**验收：**
- [ ] `processed/<job_id>/` 内 `normalized.json` + `status.json` 必然存在
- [ ] `finalizing/` 作为过渡目录正确出现和消失
- [ ] WSL tests 通过，补充 finalizing 阶段覆盖测试

---

### W2 — Runtime data 迁出 repo worktree（P1）

**文件：** `src/content_ingestion/core/config.py`（参见当前 line 56, 58）

**问题：** `data_dir` 默认落在 `project_root/data/`，repo reset / reclone / clean 会带走运行数据。

**方案：** 修改默认路径为 `~/.content-ingestion-wsl/`

```
~/.content-ingestion-wsl/
  shared_inbox_local/
  cache/
  profiles/
  sessions/
```

- 保留 env var override（`CONTENT_INGESTION_DATA_DIR` 或等效）
- 写迁移说明：旧数据手动 mv，新启动自动使用新路径

**验收：**
- [ ] 默认启动时 `data_dir` 指向 `~/.content-ingestion-wsl/`
- [ ] Windows bridge 配置的 `shared_inbox_root`（`H:\demo-win\data\shared_inbox`）路径不受此变更影响——Windows 侧显式传路径，不依赖 WSL 默认值
- [ ] env var override 仍有效
- [ ] 迁移文档写入 WSL repo README 或 MIGRATION.md

---

### W3 — Processing blockers（P1）

#### W3a — visual_finding 字段分离

**文件：** `src/content_ingestion/pipeline/llm_pipeline.py`（参见 line 323）
**测试参考：** `tests/unit/test_llm_pipeline.py`

**问题：** multimodal 分支把 `visual_finding` 塞进 `analysis_items[]`，与结构化 contract 冲突（`analysis_items` 只应含 `implication` / `alternative` 类型）。

**方案：** `visual_finding` 写入独立的顶层字段 `visual_findings[]`，不混入 `analysis_items[]`

**验收：**
- [ ] `analysis_items[]` 中不再出现 `kind=visual_finding` 的条目
- [ ] `visual_findings[]` 字段独立存在于 structured result 中
- [ ] Windows 侧 `inline_result_view.py` 的 visual findings 展示区已有独立读取路径，此项不需改 Windows 代码

#### W3b — Bilibili Whisper language 参数化

**文件：** `src/content_ingestion/pipeline/media_pipeline.py`（参见 line 70）

**问题：** Bilibili 平台硬编码 `language=zh`，平台不等于语种，非中文视频会误识别。

**方案（三级优先）：**
1. 优先读 metadata / handoff 里的 `language` 字段（如有）
2. 没有 → **不传 `--language`**，让 Whisper 自动识别
3. 只有用户显式配置 `whisper_language` 时才强制指定

> 不设 zh 作为无条件兜底，避免平台即语种的错误假设。

**验收：**
- [ ] 无 `language` 配置时，Whisper 调用不含 `--language` 参数
- [ ] metadata 提供 `language` 时，正确透传
- [ ] 显式配置覆盖时生效

#### W3c — Watcher interval 双写消除

**文件：** `src/content_ingestion/app/cli.py`（line 48）+ `src/content_ingestion/app/service.py`（line 186）

**问题：** watcher interval 在两处分别赋值，来源不一致时行为不可预测。

**方案：** 统一为单一来源（config 或 cli arg），另一处引用而不重新赋值。

**验收：**
- [ ] interval 只有一处赋值，另一处为引用
- [ ] 行为与修改前一致（已有测试覆盖）

---

### Batch 1 总验收

```
WSL tests: ≥ 41 passed（+新增 finalizing / language / interval 测试）
processed/ 只含完整 job
Windows incomplete_result 兜底保留
runtime data 默认在 ~/.content-ingestion-wsl/
visual_findings[] 独立字段
Bilibili 无配置时不传 --language
```

---

## Batch 2 — Obsidian O1 深化

**仓库：** `H:\demo-win`（Windows 仓库）
**依赖：** 不依赖 Batch 1（纯 Windows 侧），可在 Batch 1 并行启动，但建议 Batch 1 验收后再开，保持边界清晰

**目标：** Obsidian 插件从"提交入口"演进为"消费结果的知识 artifact"

### 当前基础

| 文件 | 现状 |
|------|------|
| `obsidian-plugin/importer.ts` | `importCompletedResult()` 已实现，Source + Digest 双注生成，upsert 逻辑存在 |
| `obsidian-plugin/note-builders.ts` | `buildSourceNote()` + `buildDigestNote()` 已实现，frontmatter 不完整 |
| `obsidian-plugin/main.ts` | StatusView 有任务列表（line 115 区域），无"已导入"状态追踪 |

### O1 任务

#### O1a — Source note frontmatter 补全

**文件：** `obsidian-plugin/note-builders.ts` → `buildSourceNote()`

补充字段：
- `ingestion_date`（导入日期，ISO 格式）
- `content_shape`（article / video / podcast 等）
- `tags`（来自 settings.defaultTags，逗号分隔转数组）

#### O1b — Digest note frontmatter 补全

**文件：** `obsidian-plugin/note-builders.ts` → `buildDigestNote()`

补充字段：
- `verification_status`（从 `verification_items` 整体信号派生：supported / mixed / warning / unavailable）
- `key_point_count`（`key_points[]` 数量）
- `analysis_model`（来自 `source_metadata.analysis_model`，如有）

#### O1c — StatusView 已导入状态标记

**文件：** `obsidian-plugin/main.ts` → `StatusView.renderJobRow()`

规则：
- 遍历 vault 中 `sourceNotesDir` 和 `digestNotesDir` 下的 markdown 文件
- 读 frontmatter `job_id` 字段
- 若当前 job 的 `job_id` 有匹配文件 **且** job `status === "completed"` → 显示"已导入"标记
- `archived` / `failed` / `processing` / `queued` 状态的 job **不显示**已导入标记（防误标）

#### O1d — 重建 main.js + 端到端验证

```bash
cd obsidian-plugin && npm run build
```

验证：导入一个 completed job → vault 中生成 Source + Digest 双注，frontmatter 字段完整，重复导入做 upsert 不新建。

### O1 验收

- [ ] Source note frontmatter 含 `ingestion_date`, `content_shape`, `tags`
- [ ] Digest note frontmatter 含 `verification_status`, `key_point_count`, `analysis_model`
- [ ] 重复导入同 job_id 做 upsert（importer.ts 已有逻辑，验证有效）
- [ ] "已导入"标记只出现在 `status=completed` 且 vault 有匹配 job_id 的 job 上
- [ ] `archived` / `failed` job 不误标已导入
- [ ] Obsidian build 通过，183+ tests 通过

---

## Batch 3 — Architecture A2（占位）

**目标：** WebSocket 替代 GUI polling，提升实时处理进度体验
**依赖：** Batch 1 WSL processed/ 语义稳定后设计才有意义
**时间：** Batch 1 + 2 完成后细化，当前不排期

---

## 优先级全景

```
Batch 1（WSL 仓库）
  W1  processed/ 状态机 + finalizing 阶段   [P0]
  W2  runtime data 迁出 repo worktree       [P1]
  W3a visual_finding 独立字段              [P1]
  W3b Bilibili Whisper 参数化（不传默认zh）  [P1]
  W3c watcher interval 单一来源            [P1]

Batch 2（Windows 仓库）
  O1a Source note frontmatter 补全         [P1]
  O1b Digest note frontmatter 补全         [P1]
  O1c StatusView 已导入标记（防误标）       [P1]
  O1d 端到端验证 + build                   [P1]

Batch 3（两仓库，中期）
  A2  WebSocket 实时进度                   [P2]
  O2  GUI deep-link "Save to Obsidian"    [P2]
```

---

## 不在计划内（明确排除）

- 引入数据库
- 把 analysis 逻辑移入 Windows
- WSL 暴露新的对外 HTTP API
- browser extension 变成重客户端
- Obsidian 成为后台同步引擎
- 广义知识图谱（claim/topic/entity 提取）

---

## 文件路径速查

### Windows 仓库（H:\demo-win）

| 路径 | 用途 |
|------|------|
| `src/windows_client/api/job_manager.py` | archive_job、result_card 构建、incomplete_result 兜底（Batch 1 后可简化） |
| `src/windows_client/app/result_workspace.py` | load_job_result、list_recent_results，已支持 archived |
| `obsidian-plugin/importer.ts` | importCompletedResult，O1 扩展点 |
| `obsidian-plugin/note-builders.ts` | Source/Digest note 构建，O1a/O1b 修改处 |
| `obsidian-plugin/main.ts` | StatusView line 115，O1c 修改处 |
| `docs/preview1-boundary-repair-plan-2026-03-27.md` | 修复计划全文（Phase 1-5） |
| `docs/worklog-phase0-boundary-repair-2026-03-28.md` | Phase 0 工作日志 |

### WSL 仓库（/home/ahzz1207/codex-demo）

| 路径 | 用途 |
|------|------|
| `src/content_ingestion/inbox/processor.py` | W1：processed/ 状态机 |
| `src/content_ingestion/core/config.py` | W2：data_dir 默认路径 |
| `src/content_ingestion/pipeline/llm_pipeline.py` | W3a：visual_finding 字段 |
| `src/content_ingestion/pipeline/media_pipeline.py` | W3b：Whisper language |
| `src/content_ingestion/app/cli.py` | W3c：watcher interval |
| `src/content_ingestion/app/service.py` | W3c：watcher interval |
| `tests/unit/test_processor.py` | W1 测试 |
| `tests/unit/test_llm_pipeline.py` | W3a 测试 |
