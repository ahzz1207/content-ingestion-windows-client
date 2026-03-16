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
