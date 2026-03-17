# GUI Direction: Editorial Intelligence Workspace

Date: 2026-03-17

## Summary

The next GUI direction should move away from a pure black-and-red "terminal collector" look.

The Windows client is no longer just a URL capture shell. Its real long-term role is:

- collect a link
- route the job into the Windows -> WSL pipeline
- present structured output from the processor
- become the front door of a knowledge workflow that later connects to Obsidian

Because of that, the GUI should feel closer to an analysis desk or editorial workspace than a cyber dashboard.

Recommended direction:

- Quiet Premium
- Editorial
- Knowledge Workspace

Short label for the style:

- Editorial Intelligence Workspace

## Why This Direction Fits Better

The previous visual experiment had energy, but it leaned too far toward:

- downloader / terminal shell
- operations console
- security-tool aesthetics

That creates the wrong emotional frame for this product.

This application is ultimately about:

- reading
- judging
- summarizing
- comparing viewpoints
- turning processed output into durable knowledge artifacts

So the interface should support long attention spans and reflective work, not just trigger a sense of speed or technical aggression.

## Product Identity

The GUI should feel like:

- a research desk
- an analyst notebook
- a viewpoint workspace

It should not feel like:

- a browser automation panel
- a scraping console
- a system admin dashboard

## Core Design Principles

### 1. Content Is The Hero

The processed result, summary, key points, and evidence should dominate the experience.

The user should feel that the GUI exists to help them understand and retain insight, not merely to launch jobs.

### 2. Calm Over Aggression

Avoid pure black backgrounds and harsh red contrast as the default visual language.

Use a darker, softer editorial atmosphere:

- deep graphite
- warm white
- muted gray
- restrained accent color

### 3. Reading First, Operations Second

Status, pills, path labels, and runtime details are important, but secondary.

The visual hierarchy should put:

1. title
2. summary
3. viewpoint structure
4. actions
5. technical metadata

### 4. Structured Intelligence, Not Generic Cards

Cards should feel like notes, briefs, and dossiers.

They should not feel like interchangeable dashboard widgets.

### 5. Visual Seriousness With A Human Tone

The product should look advanced and modern, but not cold in a hostile way.

The ideal mood is:

- intelligent
- composed
- deliberate
- premium

## Recommended Visual Language

### Color Direction

Base:

- background: deep graphite, not pure black
- panel background: slightly warmer charcoal
- elevated surfaces: soft dark stone

Text:

- primary text: warm white
- secondary text: mist gray
- tertiary text: muted neutral gray

Accent:

- primary accent: copper orange, cinnabar, or muted amber-red
- avoid highly saturated alarm red as the main brand accent

Support colors:

- blue-gray for system cues
- muted amber for pending states
- gentle green only when needed for successful completion

Suggested palette family:

- `#121315`
- `#17191C`
- `#1F2226`
- `#F2EEE8`
- `#C8C1B8`
- `#8A857D`
- `#C96A3D`
- `#D08E43`

### Typography Direction

Use clearer editorial layering:

- Headings: confident, modern sans serif with more character
- Body: highly readable sans serif
- Technical strings: restrained monospace only where it adds meaning

Typography hierarchy should feel closer to:

- report cover
- research brief
- reading workspace

and less like:

- log viewer
- terminal skin

### Texture And Depth

Use subtle atmosphere instead of loud effects:

- soft panel contrast
- faint shadows
- very light grain or paper-like softness if needed
- minimal glow usage

No giant neon glow fields.

No heavy cyber styling.

## Homepage Proposal

### Goal

The homepage should feel like the opening page of a research instrument.

### Structure

Top:

- product title
- one-sentence explanation
- compact environment readiness strip

Center:

- main link input
- one dominant action
- one secondary action for opening recent results

Side or lower support area:

- supported platform cues
- recent result snippets
- short explanation of what happens after submit

### Tone

The first screen should say:

- this tool helps me turn links into structured insight

not:

- this tool is a dramatic browser automation launcher

### Homepage Visual Notes

- lighter atmosphere than the previous black-red draft
- more breathing room
- larger content margins
- more elegant typography
- status chips should be quieter and smaller
- input should feel refined, not aggressive

## Result Workspace Proposal

### Goal

The result page should feel like opening a briefing document.

### Structure

Left rail:

- recent results
- compact, readable, low-noise
- more like a notebook index than a queue monitor

Main panel:

- title
- source and author context
- summary
- key point sections
- verification and evidence
- actions

Secondary details:

- technical metadata behind a calmer reveal
- not in the main attention path

### Reading Experience

The main panel should feel closer to:

- brief
- memo
- note
- analytical summary

and less like:

- result inspector
- processing console

### Workspace Visual Notes

- summary blocks should look like readable editorial sections
- evidence items should feel trustworthy and structured
- action buttons should be cleaner and quieter
- status should still exist, but not visually dominate the page

## Fastest Practical Path In PySide6

The right move is still to keep PySide6 for now.

Do not restart this effort with a Tauri rewrite just to get a different look.

### Phase A: Visual Reframe

Change only the visual system:

- revise color tokens
- revise font hierarchy
- reduce aggressive contrast
- adjust surface, border, and spacing rules
- redesign button styles

This gives the largest perception shift for the smallest engineering cost.

### Phase B: Homepage Recomposition

Keep the existing flow, but reshape:

- hero area
- input block
- helper messaging
- status strip

### Phase C: Workspace Recomposition

Rebuild result hierarchy around:

- briefing title
- summary lead
- viewpoint sections
- evidence blocks
- metadata foldout

### Phase D: Structural Cleanup

Only after the visual language feels right:

- continue component extraction
- build reusable panels
- align future Obsidian-oriented actions

## What To Avoid In The Next Iteration

- pure black as the dominant surface everywhere
- bright red as the primary visual identity
- large glowing effects
- "hacker terminal" cues
- oversized runtime status indicators
- treating metadata as equal in importance to the summary

## A Better Emotional Target

When the user opens the app, the ideal reaction is:

- this looks serious
- this looks readable
- this feels like a tool for thought
- I want to stay here and organize what I learned

Not:

- this looks intense
- this looks like a downloader
- this looks like a monitoring console

## Recommended Next Step

For the next GUI pass, the team should explicitly adopt:

- Editorial Intelligence Workspace

And the first implementation pass should focus on:

1. new color and typography system
2. homepage recomposition
3. result workspace reading hierarchy

If this direction holds up in practice, it will align much better with the project's long-term Obsidian and knowledge-management ambition than the previous high-contrast black-red approach.

这个文档方向很好，我有几点建议：

  ---
  认同的部分

  "Content is the hero" 和 "Reading first, operations second"
  是非常正确的判断。这个工具的终态是知识加工，不是运维面板。把结果阅读体验放在最
  高优先级，比炫酷的终端风格更有长期价值。

  "Notes/briefs/dossiers" 的隐喻 也比 "dashboard" 好得多。用户打开这个工具的心智
  模型应该是"我来看看今天采集到了什么"，而不是"我来检查系统状态"。

  ---
  建议调整的部分

  1. 色板：暖色调方向对了，但 copper accent 需要谨慎

  #C96A3D (copper) 和 #D08E43 (amber) 作为 accent 色，情绪是对的——沉稳、有质感、
  不刺眼。但在暗色背景上，橙铜色系的可用状态色空间会很窄：

  - Success 绿、Error 红、Warning 黄 都是常用状态色
  - Copper/Amber 和 Warning 黄太接近，容易混淆语义
  - 在 PySide6 的 QSS 里精确控制这种微妙的暖色对比度会比较痛苦

  建议： 保留暖色方向，但把 accent 稍微拉向更独特的位置。两个备选：

  Option A: 暖金偏灰  #B8956A  — 更克制，像旧书脊的烫金
  Option B: 砖红偏棕  #A65D4E  — 更沉，像皮革封面

  或者保持 copper #C96A3D 作为 accent，但把它只用于主 CTA 和选中态，不用于
  warning，避免语义冲突。

  2. 缺少的一环：三字体方案仍然值得保留

  文档没提到字体策略。在 PySide6 里也完全可以做三字体分层：

  # QSS 或 setFont() 里区分
  FONT_UI    = QFont("Inter", 13)        # 界面元素
  FONT_MONO  = QFont("JetBrains Mono", 12)  # URL、job ID、日志
  FONT_SERIF = QFont("Source Han Serif SC", 20)  # 结果页标题

  这对"editorial"气质的加成非常大。一个纯 sans-serif
  的界面看起来像工具，加入衬线标题后立刻有了"杂志/简报"的感觉。

  3. Phase C 的"briefing structure"需要更具体的层级定义

  文档说 "Rebuild result hierarchy around briefing/summary/evidence
  structure"，这是最关键的一步。建议明确定义信息层级：

  Layer 1 (Hero):    标题 (serif, 大字)  +  状态 badge
  Layer 2 (Glance):  一句话摘要  +  tags  +  来源/作者/日期
  Layer 3 (Brief):   核心观点列表 (3-7 条，带编号)
  Layer 4 (Evidence): 事实验证表  +  反驳分析
  Layer 5 (Deep):    原文预览  +  延伸阅读  +  技术元数据

  Layer 1-2 是用户打开后 0.5 秒内 要看到的。Layer 3 是 扫一眼 要掌握的。Layer
  4-5 是 想深入 才展开的。

  这个层级在 PySide6 里可以用 QScrollArea + 折叠面板实现，不需要复杂框架。

  4. 建议补充：Command Palette 在 PySide6 里也能做

  不需要 Tauri/React 才能做 Command Palette。PySide6 里就是一个 QDialog +
  QLineEdit + QListWidget：

  ⌘K → 弹出浮层 → 输入过滤 → 回车执行

  这个交互模式的价值是减少界面上的按钮和入口，让主界面更干净，更符合"calm over
  aggression"原则。建议加入 Phase B 或 Phase C。

  5. 关于"不做 Tauri 重写"的节奏建议

  完全同意先用 PySide6 迭代功能。但建议在 PySide6 的实现中有意识地做好分层：

  view layer    (QWidget, QSS)     ← 未来替换为 React
  ─────────────────────────────────
  view model    (dataclass/dict)   ← 保持不变
  ─────────────────────────────────
  service layer (workflow.py)      ← 保持不变

  这样等功能稳定后，Tauri 重写只需要替换 view
  layer，下面两层原封不动搬过来。现在 workflow.py 和 view_models.py
  已经做了这个分离，继续保持就好。

  ---
  总结

  ┌────────────────────────┬────────────────────────────────────────────────┐
  │       Codex 方案       │                    我的建议                    │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ Copper/Amber accent    │ 保留，但严格限定用途，和 warning               │
  │                        │ 状态色拉开距离                                 │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ 未提字体               │ 加入三字体方案 (sans + mono + serif)           │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ Briefing structure     │ 定义明确的 5 层信息层级                        │
  │ (Phase C)              │                                                │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ 未提 Command Palette   │ 在 PySide6 里也做，放 Phase B/C                │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ PySide6 only           │ 同意，但保持 view/viewmodel/service            │
  │                        │ 三层分离为未来迁移铺路                         │
  └────────────────────────┴────────────────────────────────────────────────┘

  整体方向是对的。"Editorial Intelligence Workspace" 这个定位比我之前的
  "Obsidian Terminal" 更适合这个产品的长期身份——毕竟用户要的是知识，不是终端
