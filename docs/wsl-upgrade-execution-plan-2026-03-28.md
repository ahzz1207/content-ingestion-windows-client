# WSL 处理链全面升级 — 可执行规划书

**日期：** 2026-03-28
**基于代码审查：** `llm_pipeline.py` / `llm_contract.py` / `html_parser.py` / `normalize/cleaning.py` / `processor.py`
**目标：** 从当前"能用但结果浅"升级到"有真实阅读价值的 research assistant 输出"

---

## 现状诊断（基于代码审查）

| 问题 | 位置 | 严重程度 |
|------|------|----------|
| 四个分析目标挤在一次 LLM 调用里，每个都做得浅 | `_analysis_instructions()` | 高 |
| 小红书无任何平台 denoise | `html_parser.py`（仅有 wechat/generic） | 高 |
| `blocks[:80]` 硬截断，长文后半部分静默丢失 | `llm_contract.py:138` | 高 |
| verification_items 与 key_points 在同一 prompt 生成，自我验证 | `llm_pipeline.py` | 中 |
| `synthesis.final_answer` 定位模糊，未与 Reader 输出分离 | `_analysis_instructions()` GOAL 4 | 中 |
| `cleaning.py` 仅做空行清理，无语义 denoise | `normalize/cleaning.py` | 中 |

---

## 升级总体架构

```
现在：
  parse_payload → analyze_asset(单次 LLM，4 目标合一) → write_outputs

升级后：
  parse_payload
    → denoise_asset          [U1：平台感知语义去噪]
    → reader_pass            [U2a：结构识别 + 章节地图]
    → synthesizer_pass       [U2b：基于结构的深度分析 + 综合]
    → critique_pass          [U4：独立批判，可选，耗时较长]
    → visual_map_render      [U3：同一次 synthesizer 调用输出 visual_map → Python 渲染 PNG]
    → write_outputs
```

---

## U1 — 输入质量修复

### U1a：小红书 denoise

**目标文件：** `src/content_ingestion/raw/html_parser.py`

**要做的事：**
1. 在 `parse_html` 里识别 `platform == "xiaohongshu"` 分支
2. 新增 `_trim_xiaohongshu_block_records(block_records)` 函数，清除：
   - 话题标签行：以 `#` 开头的纯标签行（`#好物分享 #生活方式`）
   - 互动填充词：独立行的 "姐妹们"、"宝子们"、"点个赞"、"关注一下"、"收藏备用" 等
   - 尾部互动区：检测到连续出现互动词（点赞/收藏/关注/粉丝）后截断
   - 过度 emoji：保留行首单个 emoji（有分隔语义），删除行内连续 4 个以上 emoji
3. 小红书正文容器 CSS 信号：`note-text`、`desc`、`content`（在 `_GENERIC_CONTAINER_SIGNALS` 里补充）

**验收：** 一篇小红书笔记经过处理后，blocks 里不再包含纯话题标签行和互动填充段落

---

### U1b：blocks 长文截断修复

**目标文件：** `src/content_ingestion/pipeline/llm_contract.py`

**当前问题：** `asset.blocks[:80]` 和 `evidence_segments[:100]` 硬截断，10000 字文章可能丢失后 40% 内容

**方案：** 引入 token 预算驱动的智能截取

```python
# 当前（问题）
blocks[:80]

# 升级后
_select_blocks_within_budget(asset.blocks, max_chars=settings.llm_max_content_chars)
```

`_select_blocks_within_budget` 逻辑：
- 计算每个 block 的字符数
- 优先保留：heading 块（全部保留，用于结构识别）、开头和结尾各 30% 字符预算
- 中间内容：按字符预算均匀采样（不是直接截断，是每隔 N 个取一个）
- 如果内容被截取：在 document 里加 `"content_truncated": true` 和 `"coverage_note"` 说明

**新配置项：**
```python
# config.py 新增
llm_max_content_chars: int  # 默认 40000（约 10000 中文字）
```

**验收：** 10000 字文章的结构性内容（开头结论、中间论点、末尾总结）都能进入 LLM 输入

---

### U1c：`evidence_segments` 覆盖率修复

**目标文件：** `llm_contract.py` + `config.py`

当前 `llm_max_evidence_segments` 默认 100，对长视频 transcript 可能严重不足。

**方案：**
- 将默认值从 100 提升到 200
- evidence_segments 的截取也改为按字符预算，优先保留每个 segment 的前 200 字符（截长不截数量）

---

## U2 — Prompt 重构：Reader + Synthesizer 两阶段

这是升级中最核心的改动，拆分当前单次 4 目标 prompt 为两次独立调用。

### U2a：Reader Pass（第一次 LLM 调用）

**目标：** 只做结构理解，不做观点提取。

**新函数：** `_reader_instructions()` in `llm_pipeline.py`

**新 Schema：** `READER_SCHEMA`

```json
{
  "document_type": "article|opinion|report|tutorial|interview|thread",
  "thesis": "作者的核心论点（1-2 句，基于文本的客观描述）",
  "chapter_map": [
    {
      "id": "ch-1",
      "title": "章节标题或主题（自然语言）",
      "block_ids": ["heading-2", "paragraph-3", ...],
      "role": "setup|argument|evidence|counterpoint|conclusion|background",
      "weight": "high|medium|low"
    }
  ],
  "argument_skeleton": [
    {
      "id": "arg-1",
      "claim": "这一章的核心主张",
      "chapter_id": "ch-1",
      "claim_type": "fact|opinion|implication|rhetoric"
    }
  ],
  "content_signals": {
    "evidence_density": "high|medium|low",
    "rhetoric_density": "high|medium|low",
    "has_novel_claim": true,
    "has_data": true,
    "estimated_depth": "shallow|medium|deep"
  }
}
```

**system prompt 原则：**
- 只做结构识别，不做价值判断
- 必须引用 block_ids（确保可溯源）
- 章节数 3-8 个（太少说明识别粗糙，太多说明过度碎片化）

**调用时机：** 在当前 `analyze_asset` 开始处，先于 Synthesizer

---

### U2b：Synthesizer Pass（第二次 LLM 调用）

**目标：** 基于 Reader 的结构输出，做深度分析和综合。当前 4 个 GOAL 的责任重新分配：

| 原 GOAL | 升级后定位 |
|---------|-----------|
| GOAL 1 Overview | 由 Reader 承担（thesis + document_type） |
| GOAL 2 Viewpoints (key_points) | Synthesizer：按章节逐一分析，每章提取 1-2 个核心观点，有 Reader 的 argument_skeleton 作为脚手架 |
| GOAL 3 Critical Check (verification_items) | 保留在 Synthesizer，但要求 Synthesizer 区分"文本明确支持"和"合理推断"——不做独立 Critic（U4 来做） |
| GOAL 4 Divergent Thinking (analysis_items) | Synthesizer 末尾：在全局综合完成后，专门做 3-5 个超越文本的推演 |

**新的 Synthesizer input 结构（`llm_contract.py` 修改）：**

`build_synthesizer_envelope(asset, reader_result, ...)` — 在原有 document 字段基础上新增：
```json
{
  "reader_output": {
    "thesis": "...",
    "chapter_map": [...],
    "argument_skeleton": [...],
    "content_signals": {...}
  }
}
```

**system prompt 改进重点：**
- key_points 按 chapter_map 的 high-weight 章节展开，不是全文盲扫
- 每个 key_point 的 details 要求：是什么论点 + 作者的支撑逻辑 + 与其他论点的关系（3 维度，而非现在的"3-5 句概述"）
- synthesis.final_answer 要求明确回答：读完这篇的人应该带走什么判断，而不是再次复述论点
- synthesis 新增 `what_is_new`（这篇内容相比常见观点有哪些不同），`tensions`（作者立场内部的张力或矛盾）

**新增 `synthesis` schema 字段：**
```json
"synthesis": {
  "final_answer": "...",
  "what_is_new": "...",
  "tensions": ["..."],
  "next_steps": [...],
  "open_questions": [...]
}
```

---

### U2c：`llm_pipeline.py` 调用流程重构

当前：
```python
text_payload = _call_structured_response(instructions=_analysis_instructions(), ...)
```

升级后：
```python
# Pass 1: Reader
reader_payload = _call_structured_response(
    instructions=_reader_instructions(),
    input_payload=reader_envelope.to_model_input(),
    schema=READER_SCHEMA,
)
result.steps.append({"name": "llm_reader_pass", ...})

# Pass 2: Synthesizer（输入包含 Reader 结果）
synthesizer_envelope = build_synthesizer_envelope(asset, reader_payload, ...)
text_payload = _call_structured_response(
    instructions=_synthesizer_instructions(),
    input_payload=synthesizer_envelope.to_model_input(),
    schema=TEXT_ANALYSIS_SCHEMA,  # 扩展 synthesis 字段
)
result.steps.append({"name": "llm_synthesizer_pass", ...})
```

**对 `StructuredResult` 的改动（`models.py`）：**
```python
# 新增字段
chapter_map: list[ChapterEntry] = field(default_factory=list)
what_is_new: str | None = None
tensions: list[str] = field(default_factory=list)
```

---

## U3 — visual_map 生成与 PNG 渲染

### U3a：在 TEXT_ANALYSIS_SCHEMA 里加 visual_map 字段

**目标文件：** `llm_pipeline.py`（schema）+ `llm_pipeline.py`（synthesizer instructions）

**Schema 新增：**
```json
"visual_map": {
  "type": "tree|timeline|grid",
  "title": "图标题（来自 thesis 的 10 字以内压缩）",
  "nodes": [
    {
      "id": "root",
      "label": "核心论点（≤20字）",
      "kind": "thesis|argument|evidence|tension|implication",
      "parent_id": null,
      "weight": "high|medium|low"
    }
  ]
}
```

**类型选择逻辑（Synthesizer 自主决定）：**
- `tree`：适合论证结构清晰的文章（观点→支撑→反驳树）
- `timeline`：适合过程叙述、历史回顾、步骤型内容
- `grid`：适合对比型内容（多维度评测、多方案比较）

**Synthesizer system prompt 补充：**
```
VISUAL MAP RULES
- Choose type based on content structure, not content topic.
- tree: when the content has a central claim with branching support.
- timeline: when the content follows a chronological or sequential progression.
- grid: when the content compares multiple entities across dimensions.
- Node labels must be ≤ 20 Chinese characters or ≤ 15 English words.
- Total nodes: 6-16. Root node: always one.
- Parent_id null = root or top-level node.
```

---

### U3b：Python 渲染模块

**新文件：** `src/content_ingestion/pipeline/visual_render.py`

**依赖：** `graphviz`（tree/timeline）+ `Pillow`（最终合成）— 均为轻量级依赖

**函数签名：**
```python
def render_visual_map(
    visual_map: dict,
    output_path: Path,
    *,
    theme: str = "default",  # "default" | "dark"
    width_px: int = 1200,
) -> Path:
    """Render a visual_map dict to PNG. Returns the output path."""
```

**渲染规格：**
- **tree**：graphviz DOT 格式，左→右布局，节点颜色按 kind：
  - thesis = 深蓝 `#1a56db`
  - argument = 蓝绿 `#0891b2`
  - evidence = 绿 `#059669`
  - tension = 橙 `#d97706`
  - implication = 紫 `#7c3aed`
- **timeline**：横向时间轴，节点按 weight 决定大小（high = 圆形大节点，medium = 正常，low = 小菱形）
- **grid**：矩阵表格，行列来自 nodes 的 label 分组
- 输出分辨率：1200×800px（标准）/ 1200×600px（timeline）

**存储位置：** `job_dir/analysis/visual_map.png`（与 llm/ 并列）

**调用位置（`llm_pipeline.py`）：**
在 synthesizer_pass 之后：
```python
if text_payload.get("visual_map"):
    from content_ingestion.pipeline.visual_render import render_visual_map
    png_path = render_visual_map(
        text_payload["visual_map"],
        output_path=analysis_dir.parent / "visual_map.png",
    )
    result.visual_map_path = png_path.relative_to(job_dir).as_posix()
```

**`LlmAnalysisResult` 新增字段：**
```python
visual_map: dict | None = None
visual_map_path: str | None = None
```

**`normalized.json` 新增：**
```json
"asset": {
  ...
  "visual_map_path": "analysis/visual_map.png"
}
```

---

### U3c：Windows GUI + Obsidian 展示

**Windows GUI（`src/windows_client/`）：**
- `job_manager.py`：读取 `asset.visual_map_path`
- result_renderer：在 Digest 结果页顶部展示图片（图在摘要文字之上）

**Obsidian（`obsidian-plugin/note-builders.ts`）：**
- `buildDigestNote` 里：如果 `result.visual_map_path` 存在，在 note body 顶部插入：
  ```markdown
  ![[visual_map.png]]
  ```
  图片通过 Obsidian vault attachment 链接（需要 importer 把 PNG 复制到 vault attachments）

---

## U4 — Critique 独立 Pass（第三次 LLM 调用）

> **前置条件：U2 完成、Synthesizer 结果稳定后再开始**

### U4a：设计原则

当前 verification_items 是 Synthesizer 自己生成的，本质是"自我质疑"。

独立 Critique Pass 的输入：
- Synthesizer 的完整输出（key_points + analysis_items + synthesis）
- 原始文本（evidence_segments，不是 Synthesizer 的解读）

独立 Critique Pass 的任务：
- **只给它 Synthesizer 的结论和原始证据，不给它 Synthesizer 的推理过程**
- 独立评估每个 key_point 的证据支撑程度
- 标记 Synthesizer 的 synthesis 里有哪些地方超出了文本支持
- 生成独立的 `critique_items`（不覆盖 verification_items，而是作为独立字段）

### U4b：新 Schema

```json
"critique_items": [
  {
    "id": "cr-1",
    "target_id": "kp-2",          // 指向 key_point 或 analysis_item 的 id
    "target_kind": "key_point|analysis_item|synthesis",
    "verdict": "well_grounded|partially_grounded|overreach|unverifiable",
    "rationale": "...",
    "evidence_segment_ids": [...]
  }
]
```

### U4c：模型选择

Critique Pass 可以使用与 Reader/Synthesizer 相同的模型，但 **system prompt 要完全不同**：
- 角色：批判性审稿人，不是分析师
- 明确告知它不要重复 Synthesizer 的逻辑
- 只能用原始 evidence 支持或否定，不能凭印象判断

---

## 实施顺序与验收标准

### 阶段 U1（输入质量）

**交付物：**
- `html_parser.py`：`_trim_xiaohongshu_block_records()` 函数
- `llm_contract.py`：`_select_blocks_within_budget()`
- `config.py`：`llm_max_content_chars: int = 40000`

**验收：**
- [ ] 小红书笔记处理后，blocks 不含纯话题标签行和互动填充段落
- [ ] 10000 字公众号文章：blocks 不因 80 个限制被静默截断，文章结尾内容出现在 LLM 输入里
- [ ] 所有现有测试通过

---

### 阶段 U2（Prompt 重构）

**交付物：**
- `llm_contract.py`：`build_reader_envelope()` + `build_synthesizer_envelope()`
- `llm_pipeline.py`：`_reader_instructions()` + `_synthesizer_instructions()` + 双 pass 调用流程
- `models.py`：`ChapterEntry` dataclass + `StructuredResult.chapter_map` + `what_is_new` + `tensions`

**验收（用一篇真实公众号长文）：**
- [ ] `chapter_map` 字段有 3-8 个章节，每个章节有合理 role 标注
- [ ] `key_points` 的 details 包含"论点 + 支撑逻辑 + 与其他论点的关系"三个维度
- [ ] `synthesis.what_is_new` 非空且不是对 key_points 的重复
- [ ] `synthesis.tensions` 出现有意义的张力描述（如果文章确实存在）
- [ ] 处理耗时 < 60 秒（两次 API 调用）

---

### 阶段 U3（Visual Map）

**交付物：**
- `llm_pipeline.py`：TEXT_ANALYSIS_SCHEMA 新增 visual_map
- `pipeline/visual_render.py`：新文件，render_visual_map()
- `processor.py`：normalized.json 写入 visual_map_path
- `obsidian-plugin/note-builders.ts`：Digest note 顶部插入图片
- `obsidian-plugin/importer.ts`：复制 PNG 到 vault attachments

**验收：**
- [ ] 处理完成后 `job_dir/analysis/visual_map.png` 存在
- [ ] tree 类型图：节点颜色区分，根节点居左，叶节点可读
- [ ] 图片出现在 Obsidian Digest note 最顶部，论点文字在图之后
- [ ] GUI 结果页图片展示正常

---

### 阶段 U4（Critique Pass）

**交付物：**
- `llm_pipeline.py`：第三次 LLM 调用 + `_critique_instructions()`
- `models.py`：`CritiqueItem` dataclass + `StructuredResult.critique_items`
- `llm_contract.py`：`build_critique_envelope()`

**验收：**
- [ ] critique_items 与 verification_items 无重复内容
- [ ] verdict 分布合理（不能全是 well_grounded，也不能全是 overreach）
- [ ] Critique 使用的 evidence 引用是原始 evidence_segments，不是 Synthesizer 推断

---

## 关键约束

1. **向下兼容**：Windows 侧读取 `normalized.json` 的代码只能新增字段读取，不能依赖新字段存在（`visual_map_path` 缺失时 GUI 不崩溃）
2. **可跳过设计**：U4 Critique Pass 耗时较长（额外一次 API 调用），应支持通过配置关闭（`enable_critique_pass: bool = True`）
3. **graphviz 依赖**：U3 渲染需要系统安装 `graphviz`，在 WSL 环境里执行 `apt install graphviz` 即可
4. **不改变现有测试接口**：`analyze_asset()` 函数签名不变，新增内容通过 `LlmAnalysisResult` 字段透出

---

## 文件变更索引

| 文件 | 阶段 | 变更性质 |
|------|------|----------|
| `raw/html_parser.py` | U1a | 新增小红书分支 + `_trim_xiaohongshu_block_records()` |
| `pipeline/llm_contract.py` | U1b, U2 | `_select_blocks_within_budget()` + Reader/Synthesizer envelope builder |
| `core/config.py` | U1b | 新增 `llm_max_content_chars`，调整 `llm_max_evidence_segments` 默认值 |
| `pipeline/llm_pipeline.py` | U2, U3 | Reader + Synthesizer 双 pass；visual_map schema 字段；`visual_map_path` 字段 |
| `core/models.py` | U2, U3, U4 | `ChapterEntry`，`StructuredResult` 新字段，`CritiqueItem`，`LlmAnalysisResult.visual_map_path` |
| `pipeline/visual_render.py` | U3 | **新文件**，`render_visual_map()` |
| `inbox/processor.py` | U3 | normalized.json 写入 `visual_map_path` |
| `obsidian-plugin/note-builders.ts` | U3 | Digest note 顶部图片插入 |
| `obsidian-plugin/importer.ts` | U3 | 复制 PNG 到 vault attachments |
