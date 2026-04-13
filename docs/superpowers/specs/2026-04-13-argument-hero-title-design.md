# Argument Hero Title — Design Spec

**Date:** 2026-04-13  
**Scope:** WSL only, argument mode only

## Problem

`hero_title` ← `author_thesis` (full thesis sentence, 30-60 chars)  
`hero_dek` ← `core_summary` (paraphrase of the same idea)  
Result: two lines saying the same thing in different words.

## Solution

Add a new `hero_title` field (7-20 chars short label) to the Synthesizer output.
Promote `author_thesis` to the dek position so it carries real informational weight.

| Field | Length | Role | Display position |
|-------|--------|------|-----------------|
| `hero_title` (new) | 7-20 chars | Short hook/label | Hero headline |
| `author_thesis` (existing) | unchanged | Full thesis | Dek (replaces core_summary) |

## Changes — `llm_pipeline.py` only

1. **`ARGUMENT_ANALYSIS_SCHEMA`** — add `hero_title: string` with description
2. **`_synthesizer_instructions_argument()`** — add `hero_title` to required fields + generation rule
3. **`_argument_product_view()`** — `hero_title ← hero_title`, `hero_dek ← author_thesis`

Fallback chain: `hero_title` → truncated `author_thesis` → `core_summary`

## Out of scope

- guide / review modes (later)
- models.py (mode_payload stays as dict)
- Windows GUI (consumes product_view.hero.title unchanged)
