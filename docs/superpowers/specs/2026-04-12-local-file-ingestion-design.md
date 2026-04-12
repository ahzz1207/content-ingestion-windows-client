# Local File Ingestion Design

**Date:** 2026-04-12
**Status:** Approved for implementation

## Context

The current ingestion pipeline only accepts URLs. Users sometimes already have a PDF, an image, or a block of plain text they want analyzed without going through a browser capture. This feature adds a parallel local-file entry path that routes these inputs through the same WSL analysis chain.

## Goals

- Accept PDF, image (PNG/JPG/WEBP), and plain text as direct inputs alongside URLs.
- Support three input mechanisms: file picker button, drag-and-drop, and clipboard paste (text or image) into the existing input area.
- Auto-detect input type and route silently — no extra modal or format selector shown to the user.
- Reuse the existing shared inbox protocol, WSL processing chain, polling, and result display without modification.

## Non-Goals

- No `.docx`, `.xlsx`, or other Office formats.
- No OCR on images (pure vision/multimodal path only).
- No changes to the URL ingestion flow.
- No new result display components (GPT handles result UI coordination — see GPT handoff section).

## Architecture

### Isolation principle

Local file support is a **parallel entry path**, not an extension of the URL path. The URL flow is not modified. New code is contained in two new Windows modules and two new WSL modules.

```
User action
  ├─ URL input / submit     →  existing platform_router + workflow (unchanged)
  ├─ File button / drop     →  InputRouter → LocalFileJob → SharedInbox → WSL
  └─ Paste text / image     →  InputRouter → LocalFileJob → SharedInbox → WSL
```

---

## Windows Side

### New module: `input_router.py`

Pure detection logic, no side effects.

**Detection priority (highest first):**

1. Clipboard contains image data → `ImagePayload`
2. String matches URL pattern (`http://` / `https://`) → `UrlPayload` (existing flow)
3. String is a valid, readable file path with supported extension → `FilePayload`
4. Any other non-empty string → `TextPayload`

**Supported file extensions:**
- PDF: `.pdf`
- Image: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
- Text: `.txt`, `.md`

**Output types:**

```python
@dataclass
class UrlPayload:
    url: str

@dataclass
class FilePayload:
    path: Path
    content_type: str  # "pdf" | "image" | "text"

@dataclass
class ImagePayload:
    data: bytes
    suffix: str  # ".png"

@dataclass
class TextPayload:
    text: str
```

**Validation (raises `LocalInputError` before submission):**
- File not found or not readable
- Unsupported extension
- File too large: PDF > 50 MB, image > 20 MB, text file > 10 MB
- Text payload shorter than 50 characters

### New module: `local_file_job.py`

Packages a local payload into an inbox job. Returns `job_id`.

```python
def submit_local(
    payload: FilePayload | ImagePayload | TextPayload,
    shared_root: Path,
    requested_mode: str = "auto",
) -> str:
    job_id = _generate_job_id()          # same format as existing
    job_dir = shared_root / "incoming" / job_id
    job_dir.mkdir(parents=True)
    _write_payload(job_dir, payload)      # copies file or writes text/image bytes
    _write_metadata(job_dir, payload, job_id, requested_mode)
    (job_dir / "READY").touch()
    return job_id
```

**`source_url` convention for local inputs:**
- File: `file:///H:/absolute/path/to/file.pdf`
- Pasted image: `local://image/<job_id>`
- Pasted text: `local://text/<job_id>`

**`platform`:** always `"local"`

**`content_type`:** `"pdf"` | `"image"` | `"text"`

**`content_shape`:** `"document"` (PDF/text) | `"image"` (image)

### Changes to `main_window.py`

Minimal additions only — URL flow is not touched:

1. **File button**: Opens `QFileDialog` filtered to supported extensions. On selection, calls `input_router.route_file(path)` then `local_file_job.submit_local(...)`. On success, hands `job_id` to the existing polling mechanism.

2. **Drag-and-drop**: Implement `dragEnterEvent` / `dropEvent` on the main window. Accepts `application/x-qt-windows-mime;value="FileName"` (file drop) and `text/plain` (text drop). Routes through same `InputRouter` → `local_file_job` path.

3. **Clipboard paste**: Intercept paste in the URL input field. If `QApplication.clipboard().mimeData()` contains image data, extract bytes and route as `ImagePayload`. If it contains text that is not a URL, route as `TextPayload`.

After submitting a local job, the existing `_start_task_polling(job_id)` is called directly — no new polling logic needed.

### Error display

`LocalInputError` is caught in `main_window.py` and shown via the existing `footer_label` error display. No new error UI.

---

## WSL Side

### New module: `raw/pdf_parser.py`

Dependencies: `PyMuPDF` (`fitz`)

```python
def parse_pdf(payload_path: Path, metadata: dict, ...) -> ContentAsset:
    doc = fitz.open(str(payload_path))
    # 1. Extract full text across all pages
    content_text = "\n\n".join(page.get_text() for page in doc)
    # 2. Render each page as PNG into attachments/pages/page_N.png
    #    role="analysis_frame" so multimodal chain picks them up
    # 3. Build and return ContentAsset
```

Page images are written to `job_dir/attachments/pages/page_N.png` and registered as `Attachment(role="analysis_frame")` on the asset. The existing multimodal verification pass picks them up via `_collect_frame_paths()` without modification.

**Limit:** render at most 20 pages as frames (same as existing video frame limit). If the PDF exceeds 20 pages, render evenly-spaced pages across the document.

### New module: `raw/image_parser.py`

```python
def parse_image(payload_path: Path, metadata: dict, ...) -> ContentAsset:
    # content_text = ""  (no text content)
    # content_shape = "image"
    # Copy payload image to attachments/image/source.<ext>
    # Register as Attachment(role="analysis_frame")
    # Return ContentAsset with empty blocks
```

### Changes to `raw/__init__.py`

Extend `parse_payload` dispatch by file extension — existing branches are not modified:

```python
def parse_payload(payload_path, metadata, ...):
    suffix = payload_path.suffix.lower()
    if suffix == ".html":
        return parse_html(...)       # unchanged
    if suffix in (".txt", ".md"):
        return parse_text(...)       # unchanged
    if suffix == ".pdf":
        return parse_pdf(...)        # new
    if suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return parse_image(...)      # new
    raise ParseError(f"Unsupported payload format: {suffix}")
```

### Changes to `inbox/protocol.py`

Add new payload filenames to `PAYLOAD_FILENAMES`:

```python
PAYLOAD_FILENAMES = (
    "payload.html", "payload.txt", "payload.md",  # existing
    "payload.pdf",                                  # new
    "payload.png", "payload.jpg", "payload.jpeg", "payload.webp", "payload.gif",  # new
)
```

### Changes to `pipeline/llm_pipeline.py`

Add an early branch in `analyze_asset()` for image-only assets:

```python
def analyze_asset(job_dir, asset, settings, requested_mode="auto"):
    if asset.content_shape == "image":
        return _analyze_image_asset(job_dir, asset, settings)
    # ... existing Reader → Synthesizer flow unchanged
```

`_analyze_image_asset()` is a self-contained function that:
1. Calls a single multimodal LLM pass with the image attachment
2. Asks the LLM to determine mode and produce the full editorial result in one call
3. Optionally calls `generate_visual_summary` if image card model is configured
4. Returns `LlmAnalysisResult` in the same shape as the existing path

The schema used is the existing `ARGUMENT_ANALYSIS_SCHEMA` with mode auto-selected by the LLM instruction.

---

## Data Flow Summary

```
PDF
  Windows: copy payload.pdf → job_dir
  WSL parse_pdf: extract text + render ≤20 page PNGs as analysis_frames
  WSL analyze: Reader pass (text) → Synthesizer → multimodal verification (page PNGs)

Image
  Windows: copy/save payload.png → job_dir
  WSL parse_image: image → analysis_frame attachment, content_text=""
  WSL analyze: _analyze_image_asset() single multimodal pass, mode auto

Text (pasted or .txt file)
  Windows: write payload.txt → job_dir
  WSL parse_text: existing path, unchanged
  WSL analyze: existing Reader → Synthesizer path, unchanged
```

---

## Error Handling

| Failure | Where caught | Outcome |
|---------|-------------|---------|
| File too large / wrong type | Windows `input_router` | `LocalInputError` → footer label |
| File unreadable / missing | Windows `input_router` | `LocalInputError` → footer label |
| PDF encrypted / corrupt | WSL `pdf_parser` | `ParseError` → job moves to `failed/` |
| Image format unreadable | WSL `image_parser` | `ParseError` → job moves to `failed/` |
| PyMuPDF not installed | WSL `parse_payload` | `ImportError` caught, clear message in `failed/` |
| LLM returns no result for image | WSL `_analyze_image_asset` | `status="skipped"`, result page shows skip reason |

---

## Testing

**Windows (unit):**
- `test_input_router.py`: URL detection, file detection, image detection, text detection, edge cases (empty string, short text, bad extension)
- `test_local_file_job.py`: job dir structure, metadata fields, READY file, source_url format

**WSL (unit):**
- `test_pdf_parser.py`: text extraction, page frame count limit, missing dependency handling
- `test_image_parser.py`: attachment registration, content_text empty, content_shape
- `test_parse_payload_dispatch.py`: extension routing for all new types
- `test_analyze_image_asset.py`: image branch taken when content_shape="image", returns correct result shape

---

## GPT Handoff: UI and Result Display

The following items are explicitly delegated to GPT for visual implementation:

### 1. File input UI components (`main_window.py`)

- File picker button: placement relative to existing URL input, icon, label text
- Drag-and-drop visual feedback: highlight border or overlay when file is hovering over the window
- Paste detection UX: whether to show a brief toast/chip indicating "检测到图片" or "检测到长文本" before submitting
- Mode selector visibility: whether to show the argument/guide/review selector for local files (architecture leaves `requested_mode="auto"` as default, UI can expose it optionally)

### 2. Result display for local file results

The result display uses the same `InlineResultView` and `product_view` rendering as URL results. However, local file results need small adjustments:

- **Hero byline/source**: `source_url` is `file://...` or `local://...` — the existing byline renderer should hide or reformat this gracefully (not show a raw `file://` path to the user)
- **"Open source" action**: the existing "open in browser" button makes no sense for local files — it should be hidden or replaced with "Show in Explorer" for file inputs
- **Title display**: for pasted text/image with no title, the hero title will be empty or auto-generated — GPT should decide how to handle the empty-title state visually

GPT should write a handoff request to `data/collab/requests/` when ready to coordinate on these points.

---

## Files Changed

**Windows (new):**
- `src/windows_client/app/input_router.py`
- `src/windows_client/app/local_file_job.py`
- `tests/unit/test_input_router.py`
- `tests/unit/test_local_file_job.py`

**Windows (modified, minimal):**
- `src/windows_client/gui/main_window.py` — drag-drop, file button, paste intercept
- `src/windows_client/job_exporter/models.py` — no change needed if `local_file_job` bypasses `ExportRequest`

**WSL (new):**
- `src/content_ingestion/raw/pdf_parser.py`
- `src/content_ingestion/raw/image_parser.py`
- `tests/unit/test_pdf_parser.py`
- `tests/unit/test_image_parser.py`

**WSL (modified, minimal):**
- `src/content_ingestion/raw/__init__.py` — extend dispatch
- `src/content_ingestion/inbox/protocol.py` — add payload filenames
- `src/content_ingestion/pipeline/llm_pipeline.py` — add image branch
