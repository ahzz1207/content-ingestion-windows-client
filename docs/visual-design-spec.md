# Visual Design Specification

**Codename:** Obsidian Terminal
**Version:** 1.0
**Date:** 2026-03-16
**Stack:** Tauri v2 + React + TailwindCSS

---

## 1. Design Philosophy

### Core Identity

Content Ingestion 的 GUI 不是一个"工具壳"，而是一个**知识仪器 (Knowledge Instrument)**。
它的视觉气质应该介于 **开发者工具** 和 **消费级产品** 之间：

- 看起来像终端，用起来像杂志
- 信息密度高，但阅读压力低
- 每一帧都值得截图

### Style References

| 产品 | 借鉴维度 |
|------|---------|
| **Linear** | 布局节奏、暗色调性、渐变按钮 |
| **Warp Terminal** | 终端美学、等宽字体运用、命令感 |
| **Raycast** | Command Palette 交互范式 |
| **Arc Browser** | 空间组织、侧边栏层次 |
| **Obsidian** | 知识工具气质、Markdown 渲染 |
| **Vercel Dashboard** | 数据展示、状态指示、微交互 |

### Anti-patterns (明确不做)

- 不做拟物设计 (skeuomorphism)
- 不用圆润卡通图标
- 不用纯白背景 (#FFFFFF)
- 不堆功能入口——一切通过 Command Palette
- 不用传统菜单栏/工具栏
- 不用 Electron 风格的 "web page in a box" 质感

---

## 2. Color System

### Dark Theme (Primary & Only)

```
Token                  Hex        Usage
─────────────────────────────────────────────────────
--bg-base              #0D0F12    窗口底色
--bg-surface           #151820    卡片、面板
--bg-elevated          #1C2028    弹层、悬浮面板
--bg-input             #111318    输入框背景
--bg-hover             #1A1E28    hover 状态背景

--border-default       #2A2F3A    分割线、边框
--border-subtle        #1F2330    极淡边框
--border-focus         #7C6AFF40  焦点环 (带透明度)

--text-primary         #E8EAED    正文
--text-secondary       #8B919A    辅助信息
--text-muted           #4A5060    占位符、禁用态
--text-inverse         #0D0F12    深色文字 (用于亮色按钮)

--accent-primary       #7C6AFF    主色 — 冷紫 (知识/智能)
--accent-hover         #8B7AFF    主色 hover
--accent-glow          #7C6AFF20  光晕背景
--accent-gradient-from #7C6AFF    渐变起点
--accent-gradient-to   #4F46E5    渐变终点

--status-success       #34D399    成功 — 薄荷绿
--status-warning       #FBBF24    警告 — 琥珀
--status-error         #F87171    错误 — 珊瑚红
--status-info          #60A5FA    信息 — 天蓝
--status-pending       #8B919A    等待中 — 灰

--status-success-bg    #34D39915  成功背景
--status-warning-bg    #FBBF2415  警告背景
--status-error-bg      #F8717115  错误背景
```

### Platform Accent Colors

每个平台有一个微妙的标识色，用于 tag pill 和进度条：

```
Token                  Hex        Platform
─────────────────────────────────────────────────────
--platform-wechat      #07C160    微信绿
--platform-youtube     #FF0000    YouTube 红
--platform-bilibili    #00A1D6    B站蓝
--platform-xiaohongshu #FE2C55    小红书粉
--platform-generic     #8B919A    通用灰
```

---

## 3. Typography

### Font Stack

```css
/* 界面正文 — 几何感无衬线 */
--font-sans: 'Inter', 'Geist Sans', -apple-system, 'PingFang SC', sans-serif;

/* 代码/数据/进度日志 — 等宽 */
--font-mono: 'JetBrains Mono', 'Geist Mono', 'Fira Code', 'Cascadia Code', monospace;

/* 笔记标题/结果展示 — 中文衬线 (阅读感) */
--font-serif: 'Source Han Serif SC', 'Noto Serif CJK SC', 'STSongti-SC', serif;
```

### Type Scale

```
Token          Size    Weight    Line-Height    Usage
──────────────────────────────────────────────────────────
--text-hero    28px    600       1.2            结果页大标题
--text-title   20px    600       1.3            页面标题
--text-sub     15px    500       1.4            小标题
--text-body    13px    400       1.5            正文
--text-caption 11px    400       1.5            辅助文字、时间戳
--text-mono-sm 12px    400       1.6            终端日志、代码
--text-mono-lg 14px    400       1.5            输入框文字
```

### Typography Rules

1. **界面元素** (按钮、标签、状态) 一律用 `--font-sans`
2. **用户数据展示** (URL、文件名、job ID) 一律用 `--font-mono`
3. **笔记标题** 在结果页用 `--font-serif`，营造"杂志感"
4. **中文正文** 用 `--font-sans`，不用衬线
5. 英文和数字混排时不额外调整，Inter 的中英混排表现良好

---

## 4. Spacing & Layout

### Spacing Scale (8px base)

```
--space-1:   4px     极小间距 (图标与文字)
--space-2:   8px     紧凑间距 (行内元素)
--space-3:  12px     标准内边距
--space-4:  16px     卡片内边距
--space-5:  20px     区块间距
--space-6:  24px     段落间距
--space-8:  32px     大区块间距
--space-10: 40px     页面级间距
--space-16: 64px     英雄区域留白
```

### Border Radius

```
--radius-sm:   4px    小元素 (tag pill)
--radius-md:   6px    按钮、输入框
--radius-lg:  10px    卡片
--radius-xl:  14px    对话框、弹层
--radius-full: 9999px 圆形 (头像、状态指示器)
```

### Layout Grid

```
窗口尺寸:     1080 x 720 (默认), 可调
最大内容宽:   680px (居中，阅读最佳宽度)
侧边栏宽:     280px (Result Workspace)
间距:         页面边距 40px，内容间距 24px
```

---

## 5. Shadows & Effects

### Elevation Shadows

```css
--shadow-sm:   0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md:   0 4px 12px rgba(0, 0, 0, 0.4);
--shadow-lg:   0 8px 24px rgba(0, 0, 0, 0.5);
--shadow-glow: 0 0 0 2px var(--accent-primary), 0 0 20px var(--accent-glow);
```

### Backdrop Effects

```css
/* 弹层毛玻璃 */
--backdrop-blur: blur(16px) saturate(180%);

/* Command Palette 背景遮罩 */
--overlay: rgba(0, 0, 0, 0.6);
```

---

## 6. Iconography

### Style

- **Outline** 风格，1.5px 线宽
- 推荐图标库：[Lucide Icons](https://lucide.dev/) — 与 Linear 同源
- 尺寸：16px (inline) / 20px (button) / 24px (hero)
- 颜色：默认 `--text-secondary`，active 状态 `--text-primary`

### Key Icons

```
概念          图标              用途
────────────────────────────────────────────
Ingest       ArrowDownToLine   主操作按钮
URL          Link2             输入框前缀
Processing   Loader2 (旋转)    进度中
Success      CheckCircle2      成功
Failed       XCircle           失败
Pending      Clock             等待中
Command      Command (⌘)      Command Palette
Back         ArrowLeft         返回
Settings     Settings2         设置
Obsidian     BookOpen          Obsidian 导出
WeChat       MessageCircle     微信平台
YouTube      Play              YouTube
Bilibili     Tv2               B站
Expand       ChevronDown       折叠展开
```

---

## 7. Motion & Animation

### Principles

1. **有目的地动** — 每个动画都要传达信息 (状态变化、层级关系)
2. **快而不闪** — 过渡时长 150-250ms，不超过 400ms
3. **统一缓动** — `cubic-bezier(0.16, 1, 0.3, 1)` (easeOutExpo)

### Motion Tokens

```css
--duration-fast:    150ms;
--duration-normal:  200ms;
--duration-slow:    300ms;
--duration-enter:   250ms;
--duration-exit:    200ms;

--ease-default:     cubic-bezier(0.16, 1, 0.3, 1);  /* easeOutExpo */
--ease-spring:      cubic-bezier(0.34, 1.56, 0.64, 1); /* overshoot */
--ease-in:          cubic-bezier(0.4, 0, 1, 1);
```

### Key Animations

| 场景 | 效果 | 时长 |
|------|------|------|
| 页面切换 | crossfade + subtle slideY(8px) | 200ms |
| Command Palette 打开 | scale(0.96→1) + fade | 150ms |
| Command Palette 关闭 | scale(1→0.96) + fade | 120ms |
| 进度行出现 | fadeIn + slideY(4px)，150ms 间隔逐行 | 150ms per line |
| 卡片 hover | translateY(-2px) + shadow-md | 150ms |
| 状态色扫入 | 左边框 width(0→3px) + 背景色 fade | 250ms |
| 成功完成 | checkmark SVG path 描绘动画 | 400ms |
| 标签淡入 | opacity(0→1) + scale(0.9→1) | 200ms |
| 输入框聚焦 | border-glow 渐显 | 200ms |
| Toast 通知 | slideY(-8px→0) + fadeIn | 200ms |

---

## 8. Component Catalog (Design Tokens Only)

以下是需要实现的核心 UI 组件清单。具体实现代码不在本文档范围内。

### Input

```
状态        边框                背景          文字
───────────────────────────────────────────────
Default    --border-subtle     --bg-input    --text-muted (placeholder)
Focus      --border-focus      --bg-input    --text-primary
Filled     --border-subtle     --bg-input    --text-primary (mono)
Error      --status-error/40   --bg-input    --text-primary
```

### Button

```
变体         背景                        文字             边框
───────────────────────────────────────────────────────────────
Primary     gradient(accent)            --text-inverse   none
Secondary   transparent                 --text-secondary --border-default
Ghost       transparent                 --text-secondary none
Danger      --status-error-bg           --status-error   --status-error/30
```

### Card

```
背景:   --bg-surface
边框:   --border-subtle
圆角:   --radius-lg
内边距: --space-4
Hover:  border → --border-default, translateY(-2px)
```

### Tag Pill

```
背景:   accent-color/15
文字:   accent-color
圆角:   --radius-full
内边距: 2px 10px
字号:   --text-caption
字体:   --font-sans, weight 500
```

### Status Indicator

```
状态      颜色               形式
─────────────────────────────────────
Done     --status-success   filled dot + text
Running  --accent-primary   pulsing dot + text
Failed   --status-error     filled dot + text
Pending  --status-pending   hollow dot + text
```

### Progress Log Line

```
字体:   --font-mono, --text-mono-sm
布局:   [icon 16px] [message flex-1] [status badge] [detail right-aligned]
行高:   32px
背景:   transparent → --bg-hover (hover)
```

---

## 9. Responsive Behavior

| 窗口宽度 | 布局变化 |
|---------|---------|
| ≥1080px | 双栏 (侧边栏 + 内容) |
| 800-1079px | 单栏，侧边栏折叠为抽屉 |
| <800px | 紧凑模式，卡片行变竖排 |

最小窗口尺寸：800 x 500。

---

## 10. Accessibility

- 所有交互元素支持键盘导航 (Tab / Enter / Esc)
- Command Palette 是主要键盘入口
- 颜色对比度符合 WCAG AA (在暗色背景上 ≥ 4.5:1)
- 状态指示不仅靠颜色，同时有图标和文字
- 动画尊重 `prefers-reduced-motion` 媒体查询
