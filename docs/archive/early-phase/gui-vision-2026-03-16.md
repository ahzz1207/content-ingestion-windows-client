# GUI Vision 2026 - 2026-03-16

## 1. Purpose

This document defines the next design direction for the Windows client GUI after the current Phase 1 shell.

The central design question is no longer:

- how do we make a polite desktop wrapper for URL submission

It is now:

- how do we make the product feel like a forward-looking intelligence workspace worthy of 2026

The GUI should feel:

- confident
- editorial
- precise
- calm
- premium
- contemporary without becoming gimmicky

---

## 2. Current Assessment

The current GUI is usable, but its design center is still:

- utility shell
- workflow wrapper
- result inspector

That was the correct first milestone.
It is not the correct final identity.

The next GUI should stop feeling like:

- a thin desktop face for commands

And start feeling like:

- a knowledge instrument

---

## 3. Product Reframing

The future GUI should present three connected product modes:

1. ingest
2. understand
3. shape knowledge

That means the primary object on screen should no longer be only:

- the running job

It should increasingly become:

- the processed result
- the viewpoint cluster
- the evolving topic brief

This is the moment where the app can move beyond a collector and become the front door to a richer knowledge system.

---

## 4. Design North Star

The visual and interaction target should be:

- "an intelligence studio, not an admin console"

The app should not look like:

- a generic SaaS dashboard
- a cloned Notion panel
- a dark cyberpunk toy
- a Windows form with rounded corners added later

The app should feel like a modern editorial instrument:

- spacious
- asymmetric
- strongly typographic
- evidence-first
- quietly animated
- clear under pressure

---

## 5. Experience Principles

### 5.1 One Dominant Action

There should always be one obvious next move.

Examples:

- paste a URL
- review the processed result
- promote a result into knowledge

### 5.2 Result Over Process

Users care about what the system learned more than the fact that it used a browser, watcher, or CLI bridge.

The GUI should expose process only as much as needed for trust and troubleshooting.

### 5.3 Dense Meaning, Low Noise

The interface should feel information-rich but never cluttered.

Use:

- strong grouping
- large margins
- short labels
- carefully chosen contrast

Avoid:

- walls of uniform cards
- long button rows
- tiny badges everywhere

### 5.4 Cinematic Restraint

Motion should feel deliberate and premium, not playful.

Use:

- staged reveals
- soft fades
- panel morphs
- calm pulse for active stages

Avoid:

- bouncing
- shiny loading tricks
- decorative constant motion

---

## 6. Visual Direction

### 6.1 Overall Look

Recommended look:

- soft mineral light theme
- warm paper-like surfaces
- deep ink text
- one sharp signal accent
- one cool structural accent

This avoids the typical 2024-2025 trap of:

- purple gradient on dark blur

Recommended palette direction:

- background: pale stone / paper fog
- surface: warm translucent ivory
- primary text: dense blue-black
- signal accent: oxidized copper or ember
- secondary accent: deep teal or arctic cyan
- success / warning / error remain restrained, not neon

### 6.2 Typography

Typography should do more of the visual work than decoration.

Recommended pairing:

- UI sans: `Instrument Sans`, `Manrope`, or `Sora`
- editorial serif: `Newsreader` or `Source Serif 4`

Use the serif sparingly:

- large result headlines
- synthesis sections
- topic briefs

This immediately makes the product feel more distinctive than a standard desktop utility.

### 6.3 Surfaces

Recommended surface model:

- one atmospheric background
- two primary surface elevations
- one glass-like transient layer for overlays

Cards should not all look identical.
Different panels should signal role through:

- spacing
- corner radius
- texture
- border treatment

---

## 7. Information Architecture

The next GUI should evolve into four top-level zones.

### 7.1 Capture

Purpose:

- accept a URL
- show routing confidence
- start processing

### 7.2 Live Flow

Purpose:

- show what stage the system is in
- surface only the information needed to preserve trust

### 7.3 Result Story

Purpose:

- show the processed output as an interpretable narrative

Contents:

- headline
- summary
- key points
- verification state
- warnings
- evidence highlights

### 7.4 Knowledge Actions

Purpose:

- move from result to reuse

Actions:

- open result workspace
- open in Obsidian
- create topic note
- create comparison brief
- mark for publish

This changes the app from task runner to knowledge launcher.

---

## 8. Recommended Screen Model

### 8.1 Ready State

The current ready state should evolve from a centered form into a more intentional composition.

Recommended layout:

- large command ribbon for URL input
- left-aligned product statement
- right-side recent intelligence strip
- bottom environment rail

The right-side strip should show only a few meaningful items:

- most recent processed result
- an active topic brief
- last failed job if it matters

This makes the app feel alive before the user does anything.

### 8.2 In-Progress State

The in-progress experience should stop feeling like a waiting card.

Recommended layout:

- dominant stage title
- compact pipeline rail
- current domain / platform capsule
- live evidence preview area when available
- clear fallback or retry affordance

The user should feel:

- the machine is doing disciplined work

Not:

- the app is blocking and hoping

### 8.3 Result State

The result state should become the visual centerpiece of the product.

Recommended layout:

- editorial headline block
- confidence / verification band
- summary lead paragraph
- key points grid
- disagreement or warning strip when relevant
- evidence excerpts or image references
- action row for reuse

This should feel closer to a short intelligence brief than a generic result pane.

### 8.4 Workspace State

The current result workspace should evolve into a proper reading and triage surface.

Recommended structure:

- slim left rail for recent items and filters
- central reading column
- right utility rail for metadata and actions

This three-zone model is clearer than the current dialog-style inspection approach once the workspace becomes more important.

---

## 9. Signature Interaction Ideas

These are worth exploring because they fit the product rather than adding novelty for its own sake.

### 9.1 Command Ribbon

Instead of a plain input box, use a large horizontal ribbon with:

- URL field
- detected platform chip
- route hint
- single primary action

This becomes the product's visual signature.

### 9.2 Result Filmstrip

When attachments or captured images exist, show a narrow filmstrip of evidence frames or screenshots.

This makes the system feel more grounded in actual captured material.

### 9.3 Verification Band

Add a horizontal band that summarizes:

- verified
- mixed
- unclear
- warning-heavy

This gives the user a quick trust signal before reading details.

### 9.4 Promote Actions

Place knowledge actions directly beside the result, not buried in menus:

- `Open in Obsidian`
- `Create Topic`
- `Compare`
- `Publish Draft`

These reinforce the long-term product identity.

---

## 10. Motion Direction

Recommended motion language:

- fade and slight upward drift on state entry
- soft horizontal morph when moving from capture to result
- subtle pulse in the active stage rail
- staggered reveal of result sections

Recommended timing:

- fast enough to feel sharp
- slow enough to feel intentional

Motion should help with:

- attention
- hierarchy
- state continuity

Not with:

- spectacle

---

## 11. Content Hierarchy Rules

The GUI needs a stronger hierarchy than it has today.

Recommended rule set:

- headline first
- summary second
- trust / verification signal third
- metadata fourth
- raw details last

Technical details should remain available, but pushed down.

The user should never see:

- a JSON-like wall before understanding the result

---

## 12. Design System Direction

The current GUI should be refactored toward a small internal design system.

Recommended primitives:

- `CommandRibbon`
- `StatusRail`
- `EnvironmentPill`
- `ResultHero`
- `VerificationBand`
- `EvidenceStrip`
- `ActionCluster`
- `ResultListRail`
- `MetadataPanel`

Recommended foundation tokens:

- spacing scale
- radius scale
- elevation scale
- typography scale
- semantic color tokens
- motion durations

This is necessary if the app is going to stop being one oversized main window file.

---

## 13. PySide6 Implementation Direction

This design vision is still compatible with the current stack.

Recommended implementation path:

1. split `main_window.py` by screen and component role
2. introduce a central style-token module
3. bundle 1-2 deliberate fonts with the application
4. replace repeated inline stylesheet strings with reusable component-level style helpers
5. move result rendering into dedicated widgets instead of one monolithic window class

This is the right way to become more visually ambitious without destabilizing the app.

---

## 14. Suggested Phases

### Phase G2: Visual Reframe

Goal:

- make the app feel meaningfully more premium without changing core workflow

Deliverables:

- new command ribbon
- new top-level layout
- refined typography
- calmer palette
- better result hero section

### Phase G3: Intelligence Workspace

Goal:

- make processed knowledge the visual center

Deliverables:

- persistent workspace shell
- better recent result navigation
- verification band
- evidence strip
- promote-to-knowledge actions

### Phase G4: Obsidian Bridge

Goal:

- connect operational workflow with durable knowledge management

Deliverables:

- open note in Obsidian
- create or append topic note
- prepare publish draft

---

## 15. Anti-Patterns To Avoid

The next GUI should explicitly avoid:

- default dark mode as the main identity
- generic enterprise dashboard grids
- too many status badges
- purple-heavy AI styling
- fake futuristic chrome
- exposing internal workflow jargon in primary UI
- flattening every state into the same card layout

The product should feel advanced because it is disciplined, not because it is loud.

---

## 16. Working Recommendation

The next GUI should be designed as:

- a high-clarity intelligence studio
- with strong editorial typography
- restrained but distinctive motion
- result-first information hierarchy
- direct bridges into downstream knowledge workflows such as Obsidian

The immediate design task is not to add more features.
It is to establish a sharper visual and structural identity so the app feels like the front end of a serious knowledge product rather than a capable prototype.
