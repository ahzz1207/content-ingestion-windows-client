# Inline Result First-Screen Image-Led Design

## Context

The current inline result page works for full-window reading, but it breaks down in narrower, non-fullscreen usage. Three concrete problems were identified from live GUI usage:

1. The top hero area consumes too much vertical space before the user sees any meaningful result content.
2. The new WSL-generated `insight_card.png` is not consistently visible in the current reading flow, even though the Windows client already has code paths to display it.
3. In non-fullscreen mode, the first screen of the main reading area is dominated by text framing and empty space instead of showing the most information-dense artifact.

The selected direction is the image-led `B` layout explored during visual brainstorming: keep a compact header with the title and one-sentence takeaway, then make the generated image summary the dominant first-screen artifact, with long-form text pushed lower.

## Goals

- Improve first-screen information density in `InlineResultView`, especially below the narrow-layout breakpoint.
- Replace the current text-heavy first screen with an image-led first screen whenever `insight_card.png` exists.
- Reduce the amount of vertical whitespace consumed by the hero and action strip.
- Keep the page readable when `insight_card.png` is missing by falling back to a compact text-first layout instead of leaving a visually empty screen.
- Preserve the existing Windows/WSL contract boundary: Windows only consumes `insight_card_path` and existing structured result fields.

## Non-Goals

- No backend contract changes.
- No new image-generation logic.
- No changes to WSL prompt/schema/output generation.
- No redesign of the full desktop-width reading experience beyond what is necessary to support the compact first-screen layout.

## Current State

`InlineResultView` currently renders the main reading stream in this order:

1. Hero shell
2. Insight card frame
3. Takeaways
4. Verification
5. Bottom line
6. Divergent/gaps/warnings
7. Long-form reading browser

This order means the image card is technically early, but the hero still occupies too much height. In narrow mode, the right rail simply moves below the main stream, but the first-screen composition is not rebalanced. The user still lands on a large decorative header plus introductory text before reaching the most valuable artifact.

The image summary support already exists in `InlineResultView.load_entry()`:

- It reads `entry.details["insight_card_path"]`
- Loads the PNG into a `QPixmap`
- Shows `_card_frame` when the pixmap is valid

So the missing visual summary is currently a runtime/output availability issue, not a missing Windows rendering capability.

## Proposed Design

### 1. Two first-screen modes

The inline result page should explicitly support two first-screen compositions:

- `image-led` mode: used when `insight_card_path` exists and the image loads successfully.
- `compact-text` mode: used when no insight card is available.

This should be treated as a presentational state inside `InlineResultView`, not as a new backend mode.

### 2. Compact hero in narrow usage

The current immersive hero should be visually compressed, with the strongest compression applied in narrow mode.

The compact hero keeps only:

- title
- one-sentence takeaway
- lightweight metadata (`byline`, `source`, chips)
- action row

The compact hero should remove the feeling of a large ornamental cover block. It should read as a short framing header above the actual result.

Concrete design implications:

- reduce top/bottom padding in `ImmersiveHero`, `HeroTopBar`, and `HeroCard`
- reduce spacing between title, takeaway, metadata, and chips
- reduce extra separation between the hero and the next content block
- keep actions visible, but avoid making the action strip visually heavier than the result itself

### 3. Image-led first screen

When the insight card exists, it becomes the primary first-screen content block below the compact hero.

Behavior:

- `_card_frame` should appear immediately after the compact hero
- in narrow mode it should be visually dominant and large enough to occupy most of the remaining first-screen space
- the long-form text browser should remain below the fold more often than it does today
- the text directly above the image should stay short; do not add another summary block above the image

The first screen should feel like:

- short framing header
- large image summary
- clear downward transition into deeper reading

### 4. Text condensation above the fold

The user explicitly wants the text above the image to be further condensed.

So the header area should use only one primary summary line:

- `hero_take`, already derived from product-view `dek` / `bottom_line` or brief summary fields

Do not add a second stacked summary paragraph above the image.

If supporting metadata is shown, it must remain visually secondary:

- byline/source in small text
- chips in a compact row

### 5. Graceful fallback when image is absent

When no image is available, the page should still improve over the current experience.

Fallback behavior:

- keep the same compact hero treatment
- keep the next text block close to the hero with minimal dead space
- ensure the browser or top structured block begins earlier in the scroll
- do not reserve any large empty slot for the missing image

This prevents the narrow result page from feeling broken while WSL image generation is still being integrated on some flows.

### 6. Keep right rail secondary in narrow mode

The context rail should continue to move below the main stream in narrow mode. The redesign should not attempt to keep side context beside the hero in narrow layouts. The core reading decision is to prioritize the main result artifact, not supporting actions.

## Implementation Shape

### Files expected to change

- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/main_window.py`
- `tests/unit/test_main_window.py`
- `tests/unit/test_result_renderer.py` only if shared rendering assumptions need coverage updates

### Likely widget/layout changes

In `inline_result_view.py`:

- add an internal notion of whether the current entry has a renderable insight card
- add narrow-vs-wide presentation handling for hero/card spacing
- tune `_apply_layout_mode()` so narrow layout does more than stack the rail; it should also activate compact first-screen spacing
- reduce hero paddings and inter-section spacing in the main reading stream
- potentially adjust image scaling behavior so the card feels large enough in narrow layouts without overflowing awkwardly

In `main_window.py` stylesheet:

- reduce `ImmersiveHero` visual mass
- reduce `HeroTopBar`, `HeroActionStrip`, and `HeroCard` padding/radius where needed
- refine `ImageSummaryCard` presentation so it reads as the primary content artifact rather than a secondary accessory card

## Data Flow and Contract Notes

No new backend fields are required.

The design depends on existing fields only:

- `entry.details["insight_card_path"]`
- hero/title/takeaway fields already resolved into the entry/brief/product-view path

This keeps the Windows implementation decoupled from WSL internals and consistent with the collaboration contract.

## Error Handling and Edge Cases

### Missing image path

If `insight_card_path` is absent, stay in `compact-text` mode.

### Invalid image path or unreadable image

If the path exists but `QPixmap` fails to load, hide the image card and stay in `compact-text` mode.

### Very small window sizes

For very narrow windows, avoid any fixed height that causes the image or hero to become unusable. The layout should remain scrollable and let the image scale down proportionally.

### Long titles

Long titles should wrap, but the compact hero styling should still keep the overall block notably shorter than today.

## Testing Strategy

Testing should focus on behavior, not pixel-perfect screenshots.

Minimum coverage:

- narrow layout applies the compact first-screen arrangement
- result with a valid insight card shows the image-led block near the top of the reading stream
- result without an insight card does not leave an empty placeholder block
- existing flows for guide/review/argument product-view rendering still work
- no regressions in the main window result-page tests that exercise inline result loading

Manual verification should include:

- non-fullscreen window with insight card present
- non-fullscreen window with no insight card
- fullscreen/large window sanity check
- guide/review result with real product-view payload

## Open Questions

1. Whether the narrow-layout compact treatment should also apply to medium-width windows slightly above the current `1100px` breakpoint.
2. Whether the image summary heading (`视觉总结`) should stay visible in the image-led first screen or be visually de-emphasized further.

The current recommendation is:

- keep the existing breakpoint for the first implementation
- keep the heading, but visually subordinate it to the image itself

## Recommended Next Step

Write a focused implementation plan for the Windows inline result view only, then execute with tests first. The implementation should stay minimal and avoid restructuring unrelated result-page code.
