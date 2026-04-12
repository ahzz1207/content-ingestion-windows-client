# Local File Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PDF / image / plain-text as direct inputs alongside URLs, routing through the same WSL analysis chain.

**Architecture:** Windows side detects input type (URL / file / pasted image / pasted text) via a pure `InputRouter` module, packages it into a shared-inbox job via `LocalFileJob`, then hands the `job_id` to the existing polling mechanism. WSL side gains two new raw parsers (`pdf_parser`, `image_parser`), extended dispatch in `raw/__init__`, and a new `_analyze_image_asset` branch in `llm_pipeline` that skips the Reader pass for image-only content.

**Tech Stack:** Python 3.10, PySide6 (Windows GUI), PyMuPDF `fitz` (WSL PDF rendering), existing OpenAI-compatible SDK for multimodal LLM calls.

**Working directory:** `.worktrees/local-file-ingestion`

---

## Stream A — Windows Side

### Task A1: `input_router.py` — input type detection

**Files:**
- Create: `src/windows_client/app/input_router.py`
- Create: `tests/unit/test_input_router.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_input_router.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from windows_client.app.input_router import (
    route_text, route_file, route_clipboard_image,
    UrlPayload, FilePayload, ImagePayload, TextPayload,
    LocalInputError,
)


def test_route_text_url():
    result = route_text("https://example.com/article")
    assert isinstance(result, UrlPayload)
    assert result.url == "https://example.com/article"


def test_route_text_http_url():
    result = route_text("http://example.com/")
    assert isinstance(result, UrlPayload)


def test_route_text_long_text():
    text = "这是一段很长的文章内容，" * 10
    result = route_text(text)
    assert isinstance(result, TextPayload)
    assert result.text == text.strip()


def test_route_text_too_short_raises():
    with pytest.raises(LocalInputError, match="too short"):
        route_text("短")


def test_route_file_pdf(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_bytes(b"%PDF-1.4 fake content")
    result = route_file(f)
    assert isinstance(result, FilePayload)
    assert result.content_type == "pdf"


def test_route_file_image_png(tmp_path):
    f = tmp_path / "photo.png"
    f.write_bytes(b"\x89PNG fake")
    result = route_file(f)
    assert isinstance(result, FilePayload)
    assert result.content_type == "image"


def test_route_file_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("some text", encoding="utf-8")
    result = route_file(f)
    assert isinstance(result, FilePayload)
    assert result.content_type == "text"


def test_route_file_unsupported_raises(tmp_path):
    f = tmp_path / "doc.docx"
    f.write_bytes(b"fake docx")
    with pytest.raises(LocalInputError, match="Unsupported"):
        route_file(f)


def test_route_file_missing_raises(tmp_path):
    with pytest.raises(LocalInputError, match="not found"):
        route_file(tmp_path / "missing.pdf")


def test_route_file_too_large_pdf_raises(tmp_path):
    f = tmp_path / "big.pdf"
    f.write_bytes(b"x")
    with patch.object(f.__class__, "stat") as mock_stat:
        mock_stat.return_value.st_size = 60 * 1024 * 1024
        with pytest.raises(LocalInputError, match="too large"):
            route_file(f)


def test_route_clipboard_image():
    data = b"\x89PNG\r\n\x1a\n" + b"x" * 100
    result = route_clipboard_image(data)
    assert isinstance(result, ImagePayload)
    assert result.suffix == ".png"
    assert result.data == data


def test_route_clipboard_image_too_large_raises():
    data = b"x" * (21 * 1024 * 1024)
    with pytest.raises(LocalInputError, match="too large"):
        route_clipboard_image(data)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd .worktrees/local-file-ingestion
python -m pytest tests/unit/test_input_router.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'windows_client.app.input_router'`

- [ ] **Step 3: Implement `input_router.py`**

Create `src/windows_client/app/input_router.py`:

```python
"""Detect and classify user input: URL, local file, pasted image, or plain text."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_SUPPORTED_PDF = frozenset({".pdf"})
_SUPPORTED_IMAGE = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})
_SUPPORTED_TEXT = frozenset({".txt", ".md"})
_SUPPORTED_FILE = _SUPPORTED_PDF | _SUPPORTED_IMAGE | _SUPPORTED_TEXT

MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_TEXT_BYTES = 10 * 1024 * 1024
MIN_TEXT_CHARS = 50


class LocalInputError(Exception):
    pass


@dataclass(slots=True)
class UrlPayload:
    url: str


@dataclass(slots=True)
class FilePayload:
    path: Path
    content_type: str  # "pdf" | "image" | "text"


@dataclass(slots=True)
class ImagePayload:
    data: bytes
    suffix: str  # ".png"


@dataclass(slots=True)
class TextPayload:
    text: str


def route_text(text: str) -> UrlPayload | FilePayload | TextPayload:
    """Route a string (URL input / pasted text / file path) to the correct payload type."""
    stripped = text.strip()
    if _URL_RE.match(stripped):
        return UrlPayload(url=stripped)
    candidate = Path(stripped)
    if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in _SUPPORTED_FILE:
        return route_file(candidate)
    if len(stripped) < MIN_TEXT_CHARS:
        raise LocalInputError(f"Text too short (minimum {MIN_TEXT_CHARS} characters). Paste a URL or longer text.")
    return TextPayload(text=stripped)


def route_file(path: Path) -> FilePayload:
    """Validate and classify a file path."""
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_FILE:
        raise LocalInputError(
            f"Unsupported file type: {suffix}. Supported: PDF, images (.png .jpg .jpeg .webp .gif), .txt, .md"
        )
    if not path.exists():
        raise LocalInputError(f"File not found: {path}")
    if not path.is_file():
        raise LocalInputError(f"Not a file: {path}")
    size = path.stat().st_size
    if suffix in _SUPPORTED_PDF and size > MAX_PDF_BYTES:
        raise LocalInputError("PDF too large (max 50 MB)")
    if suffix in _SUPPORTED_IMAGE and size > MAX_IMAGE_BYTES:
        raise LocalInputError("Image too large (max 20 MB)")
    if suffix in _SUPPORTED_TEXT and size > MAX_TEXT_BYTES:
        raise LocalInputError("Text file too large (max 10 MB)")
    if suffix in _SUPPORTED_PDF:
        content_type = "pdf"
    elif suffix in _SUPPORTED_IMAGE:
        content_type = "image"
    else:
        content_type = "text"
    return FilePayload(path=path, content_type=content_type)


def route_clipboard_image(data: bytes) -> ImagePayload:
    """Wrap raw clipboard image bytes."""
    if len(data) > MAX_IMAGE_BYTES:
        raise LocalInputError("Pasted image too large (max 20 MB)")
    return ImagePayload(data=data, suffix=".png")
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/test_input_router.py -v
```

Expected: all 12 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/windows_client/app/input_router.py tests/unit/test_input_router.py
git commit -m "feat(windows): add InputRouter for local file/text/image detection"
```

---

### Task A2: `local_file_job.py` — package inputs into inbox jobs

**Files:**
- Create: `src/windows_client/app/local_file_job.py`
- Create: `tests/unit/test_local_file_job.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_local_file_job.py`:

```python
import json
from pathlib import Path
from windows_client.app.input_router import FilePayload, ImagePayload, TextPayload
from windows_client.app.local_file_job import submit_local


def test_submit_pdf_creates_job_structure(tmp_path):
    shared_root = tmp_path / "inbox"
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    payload = FilePayload(path=pdf, content_type="pdf")

    job_id = submit_local(payload, shared_root=shared_root)

    job_dir = shared_root / "incoming" / job_id
    assert job_dir.exists()
    assert (job_dir / "payload.pdf").exists()
    assert (job_dir / "metadata.json").exists()
    assert (job_dir / "READY").exists()


def test_submit_pdf_metadata_fields(tmp_path):
    shared_root = tmp_path / "inbox"
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    payload = FilePayload(path=pdf, content_type="pdf")

    job_id = submit_local(payload, shared_root=shared_root, requested_mode="guide")

    meta = json.loads((shared_root / "incoming" / job_id / "metadata.json").read_text())
    assert meta["job_id"] == job_id
    assert meta["platform"] == "local"
    assert meta["content_type"] == "pdf"
    assert meta["content_shape"] == "document"
    assert meta["requested_mode"] == "guide"
    assert meta["source_url"].startswith("file:///")


def test_submit_image_payload(tmp_path):
    shared_root = tmp_path / "inbox"
    payload = ImagePayload(data=b"\x89PNG fake", suffix=".png")

    job_id = submit_local(payload, shared_root=shared_root)

    job_dir = shared_root / "incoming" / job_id
    assert (job_dir / "payload.png").read_bytes() == b"\x89PNG fake"
    meta = json.loads((job_dir / "metadata.json").read_text())
    assert meta["content_type"] == "image"
    assert meta["content_shape"] == "image"
    assert meta["source_url"] == f"local://image/{job_id}"


def test_submit_text_payload(tmp_path):
    shared_root = tmp_path / "inbox"
    payload = TextPayload(text="这是一段很长的文本内容" * 10)

    job_id = submit_local(payload, shared_root=shared_root)

    job_dir = shared_root / "incoming" / job_id
    assert (job_dir / "payload.txt").read_text(encoding="utf-8") == payload.text
    meta = json.loads((job_dir / "metadata.json").read_text())
    assert meta["content_type"] == "text"
    assert meta["source_url"] == f"local://text/{job_id}"


def test_job_id_format(tmp_path):
    shared_root = tmp_path / "inbox"
    payload = TextPayload(text="x" * 100)
    job_id = submit_local(payload, shared_root=shared_root)
    # Format: YYYYMMDD_HHMMSS_xxxxxx
    parts = job_id.split("_")
    assert len(parts) == 3
    assert len(parts[0]) == 8   # date
    assert len(parts[1]) == 6   # time
    assert len(parts[2]) == 6   # hex
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/unit/test_local_file_job.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'windows_client.app.local_file_job'`

- [ ] **Step 3: Implement `local_file_job.py`**

Create `src/windows_client/app/local_file_job.py`:

```python
"""Package a local file / pasted text / pasted image into a shared-inbox job."""
from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from windows_client.app.input_router import FilePayload, ImagePayload, TextPayload


def submit_local(
    payload: FilePayload | ImagePayload | TextPayload,
    shared_root: Path,
    requested_mode: str = "auto",
) -> str:
    """Write payload + metadata into shared_root/incoming/<job_id>/ and touch READY.

    Returns the new job_id.
    """
    job_id = _generate_job_id()
    job_dir = shared_root / "incoming" / job_id
    job_dir.mkdir(parents=True)
    source_url, content_type, content_shape = _write_payload(job_dir, payload, job_id)
    _write_metadata(job_dir, job_id, source_url, content_type, content_shape, requested_mode)
    (job_dir / "READY").touch()
    return job_id


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_job_id() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(3)


def _write_payload(
    job_dir: Path,
    payload: FilePayload | ImagePayload | TextPayload,
    job_id: str,
) -> tuple[str, str, str]:
    """Copy/write payload file. Returns (source_url, content_type, content_shape)."""
    if isinstance(payload, FilePayload):
        suffix = payload.path.suffix.lower()
        dest = job_dir / f"payload{suffix}"
        shutil.copy2(payload.path, dest)
        source_url = payload.path.as_uri()
        content_shape = "image" if payload.content_type == "image" else "document"
        return source_url, payload.content_type, content_shape

    if isinstance(payload, ImagePayload):
        dest = job_dir / f"payload{payload.suffix}"
        dest.write_bytes(payload.data)
        return f"local://image/{job_id}", "image", "image"

    # TextPayload
    dest = job_dir / "payload.txt"
    dest.write_text(payload.text, encoding="utf-8")
    return f"local://text/{job_id}", "text", "document"


def _write_metadata(
    job_dir: Path,
    job_id: str,
    source_url: str,
    content_type: str,
    content_shape: str,
    requested_mode: str,
) -> None:
    metadata = {
        "job_id": job_id,
        "source_url": source_url,
        "platform": "local",
        "collector": "windows-client-local",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "content_type": content_type,
        "content_shape": content_shape,
        "requested_mode": requested_mode,
    }
    (job_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/test_local_file_job.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/windows_client/app/local_file_job.py tests/unit/test_local_file_job.py
git commit -m "feat(windows): add LocalFileJob to package local inputs into inbox jobs"
```

---

### Task A3: Wire into `main_window.py` — file button, drag-drop, paste

**Files:**
- Modify: `src/windows_client/gui/main_window.py`

> **GPT handoff note:** This task adds the backend wiring only (event handlers calling `InputRouter` + `LocalFileJob`). Visual design of the file button, drag-drop highlight, and paste toast is delegated to GPT — see `data/collab/handoff/` for the UI spec.

- [ ] **Step 1: Find the submit handler and URL input widget**

Read `src/windows_client/gui/main_window.py` and locate:
- The URL input `QLineEdit` widget (search for `url_input`)
- `_on_submit()` or the equivalent method that calls `_run_export()`
- The `__init__` or `_setup_ui()` method where widgets are created

- [ ] **Step 2: Add imports at top of `main_window.py`**

Add after existing imports:

```python
from windows_client.app.input_router import (
    LocalInputError,
    route_clipboard_image,
    route_file,
    route_text,
    FilePayload,
    ImagePayload,
    TextPayload,
    UrlPayload,
)
from windows_client.app.local_file_job import submit_local
```

- [ ] **Step 3: Add `_submit_local_payload` helper method**

Add this private method to `MainWindow`:

```python
def _submit_local_payload(self, payload: FilePayload | ImagePayload | TextPayload) -> None:
    """Package a local payload into the inbox and start polling."""
    shared_root = self.workflow.service.settings.effective_shared_inbox_root
    try:
        job_id = submit_local(payload, shared_root=shared_root)
    except Exception as exc:
        self.footer_label.setText(f"提交失败：{exc}")
        return
    self._start_task_polling(job_id)
```

- [ ] **Step 4: Modify the submit handler to check input type**

Find the method that handles URL submission (called when user presses Enter or clicks submit). Wrap it to detect local input first:

```python
def _on_submit(self) -> None:
    text = self.url_input.text().strip()
    if not text:
        return
    try:
        routed = route_text(text)
    except LocalInputError as exc:
        self.footer_label.setText(str(exc))
        return
    if isinstance(routed, UrlPayload):
        # existing URL flow — unchanged
        self._handle_url_submit(routed.url)
        return
    # local text or file path
    self._submit_local_payload(routed)
```

If the existing submit method already has URL-handling logic inline, extract it into `_handle_url_submit(url: str)` first, then wrap as above.

- [ ] **Step 5: Add file picker button handler**

Find where toolbar/action buttons are created. Add a file picker slot:

```python
def _on_open_file(self) -> None:
    from PySide6.QtWidgets import QFileDialog
    path_str, _ = QFileDialog.getOpenFileName(
        self,
        "打开文件",
        "",
        "支持的文件 (*.pdf *.png *.jpg *.jpeg *.webp *.gif *.txt *.md)",
    )
    if not path_str:
        return
    from pathlib import Path
    try:
        payload = route_file(Path(path_str))
    except LocalInputError as exc:
        self.footer_label.setText(str(exc))
        return
    self._submit_local_payload(payload)
```

Connect this slot to the file button when GPT creates it.

- [ ] **Step 6: Add drag-and-drop support**

In `__init__` or `_setup_ui`, enable drops:

```python
self.setAcceptDrops(True)
```

Add event handlers to `MainWindow`:

```python
def dragEnterEvent(self, event) -> None:
    md = event.mimeData()
    if md.hasUrls() or md.hasText():
        event.acceptProposedAction()

def dropEvent(self, event) -> None:
    md = event.mimeData()
    if md.hasUrls():
        url = md.urls()[0]
        if url.isLocalFile():
            from pathlib import Path
            try:
                payload = route_file(Path(url.toLocalFile()))
            except LocalInputError as exc:
                self.footer_label.setText(str(exc))
                return
            self._submit_local_payload(payload)
        else:
            self.url_input.setText(url.toString())
            self._on_submit()
    elif md.hasText():
        self.url_input.setText(md.text())
        self._on_submit()
```

- [ ] **Step 7: Add clipboard image paste detection**

Override `keyPressEvent` or intercept Ctrl+V on the url_input. Simpler: install an event filter on `url_input`:

```python
# In __init__, after url_input is created:
self.url_input.installEventFilter(self)

def eventFilter(self, obj, event) -> bool:
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeySequence
    from PySide6.QtWidgets import QApplication
    if obj is self.url_input and event.type() == QEvent.KeyPress:
        if event.matches(QKeySequence.Paste):
            clipboard = QApplication.clipboard()
            mime = clipboard.mimeData()
            if mime.hasImage():
                img = clipboard.image()
                if not img.isNull():
                    from PySide6.QtCore import QBuffer, QIODevice
                    import io
                    buf = QBuffer()
                    buf.open(QIODevice.WriteOnly)
                    img.save(buf, "PNG")
                    data = bytes(buf.data())
                    try:
                        payload = route_clipboard_image(data)
                    except LocalInputError as exc:
                        self.footer_label.setText(str(exc))
                        return True
                    self._submit_local_payload(payload)
                    return True  # consumed
    return super().eventFilter(obj, event)
```

- [ ] **Step 8: Run full Windows tests**

```bash
python -m pytest tests/unit/ -q
```

Expected: 349+ passed (existing 347 + A1 + A2 tests), 0 failed.

- [ ] **Step 9: Commit**

```bash
git add src/windows_client/gui/main_window.py
git commit -m "feat(windows): wire file button, drag-drop, paste into local file submission"
```

---

## Stream B — WSL Side

### Task B1: Extend inbox protocol + `raw/__init__` dispatch

**Files:**
- Modify: `src/content_ingestion/inbox/protocol.py`
- Modify: `src/content_ingestion/raw/__init__.py`

- [ ] **Step 1: Extend `PAYLOAD_FILENAMES` in `protocol.py`**

Open `src/content_ingestion/inbox/protocol.py`. Find the line:

```python
PAYLOAD_FILENAMES = ("payload.html", "payload.txt", "payload.md")
```

Replace with:

```python
PAYLOAD_FILENAMES = (
    "payload.html", "payload.txt", "payload.md",
    "payload.pdf",
    "payload.png", "payload.jpg", "payload.jpeg", "payload.webp", "payload.gif",
)
```

- [ ] **Step 2: Extend `parse_payload` dispatch in `raw/__init__.py`**

Open `src/content_ingestion/raw/__init__.py`. Current content:

```python
from .html_parser import parse_html
from .text_parser import parse_text

def parse_payload(payload_path, metadata, capture_manifest=None):
    suffix = payload_path.suffix.lower()
    if suffix == ".html":
        return parse_html(payload_path, metadata, capture_manifest=capture_manifest)
    return parse_text(payload_path, metadata, capture_manifest=capture_manifest)
```

Replace with:

```python
from .html_parser import parse_html
from .text_parser import parse_text

_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


def parse_payload(payload_path, metadata, capture_manifest=None):
    suffix = payload_path.suffix.lower()
    if suffix == ".html":
        return parse_html(payload_path, metadata, capture_manifest=capture_manifest)
    if suffix in (".txt", ".md"):
        return parse_text(payload_path, metadata, capture_manifest=capture_manifest)
    if suffix == ".pdf":
        from .pdf_parser import parse_pdf
        return parse_pdf(payload_path, metadata, capture_manifest=capture_manifest)
    if suffix in _IMAGE_SUFFIXES:
        from .image_parser import parse_image
        return parse_image(payload_path, metadata, capture_manifest=capture_manifest)
    raise ValueError(f"Unsupported payload format: {suffix}")
```

- [ ] **Step 3: Run existing WSL tests to verify no regressions**

```bash
cd /home/ahzz1207/codex-demo
python3 -m pytest tests/ -q
```

Expected: 90 passed (same as before).

- [ ] **Step 4: Commit**

```bash
git add src/content_ingestion/inbox/protocol.py src/content_ingestion/raw/__init__.py
git commit -m "feat(wsl): extend inbox protocol and raw dispatch for pdf/image payloads"
```

---

### Task B2: `raw/pdf_parser.py` — extract text + render page frames

**Files:**
- Create: `src/content_ingestion/raw/pdf_parser.py`
- Create: `tests/unit/test_pdf_parser.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_pdf_parser.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from content_ingestion.raw.pdf_parser import parse_pdf


FAKE_METADATA = {
    "job_id": "test_job",
    "source_url": "file:///tmp/report.pdf",
    "platform": "local",
    "collector": "windows-client-local",
    "collected_at": "2026-04-12T00:00:00+00:00",
    "content_type": "pdf",
    "content_shape": "document",
    "requested_mode": "auto",
}


def _make_mock_doc(num_pages: int, text_per_page: str = "Page text"):
    """Build a minimal fitz.Document mock."""
    pages = []
    for i in range(num_pages):
        page = MagicMock()
        page.get_text.return_value = f"{text_per_page} {i + 1}"
        pix = MagicMock()
        pix.save = MagicMock()
        page.get_pixmap.return_value = pix
        pages.append(page)

    doc = MagicMock()
    doc.__len__ = lambda self: num_pages
    doc.__iter__ = lambda self: iter(pages)
    doc.__getitem__ = lambda self, idx: pages[idx]
    return doc


def test_parse_pdf_extracts_text(tmp_path):
    payload = tmp_path / "payload.pdf"
    payload.write_bytes(b"%PDF")

    mock_doc = _make_mock_doc(3, "Hello page")
    with patch("content_ingestion.raw.pdf_parser.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock(return_value=MagicMock())
        asset = parse_pdf(payload, FAKE_METADATA)

    assert "Hello page 1" in asset.content_text
    assert "Hello page 2" in asset.content_text


def test_parse_pdf_creates_page_frames(tmp_path):
    payload = tmp_path / "payload.pdf"
    payload.write_bytes(b"%PDF")

    mock_doc = _make_mock_doc(3)
    with patch("content_ingestion.raw.pdf_parser.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock(return_value=MagicMock())
        asset = parse_pdf(payload, FAKE_METADATA)

    analysis_frames = [a for a in asset.attachments if a.role == "analysis_frame"]
    assert len(analysis_frames) == 3


def test_parse_pdf_caps_frames_at_20(tmp_path):
    payload = tmp_path / "payload.pdf"
    payload.write_bytes(b"%PDF")

    mock_doc = _make_mock_doc(50)
    with patch("content_ingestion.raw.pdf_parser.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock(return_value=MagicMock())
        asset = parse_pdf(payload, FAKE_METADATA)

    analysis_frames = [a for a in asset.attachments if a.role == "analysis_frame"]
    assert len(analysis_frames) == 20


def test_parse_pdf_content_shape(tmp_path):
    payload = tmp_path / "payload.pdf"
    payload.write_bytes(b"%PDF")

    mock_doc = _make_mock_doc(1)
    with patch("content_ingestion.raw.pdf_parser.fitz") as mock_fitz:
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock(return_value=MagicMock())
        asset = parse_pdf(payload, FAKE_METADATA)

    assert asset.content_shape == "document"


def test_parse_pdf_missing_fitz(tmp_path, monkeypatch):
    payload = tmp_path / "payload.pdf"
    payload.write_bytes(b"%PDF")

    import builtins
    real_import = builtins.__import__

    def no_fitz(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("No module named 'fitz'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_fitz)

    # patch the module-level fitz reference
    with patch.dict("sys.modules", {"fitz": None}):
        with pytest.raises(ImportError, match="PyMuPDF"):
            import importlib
            import content_ingestion.raw.pdf_parser as pdf_mod
            importlib.reload(pdf_mod)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/unit/test_pdf_parser.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'content_ingestion.raw.pdf_parser'`

- [ ] **Step 3: Implement `pdf_parser.py`**

Create `src/content_ingestion/raw/pdf_parser.py`:

```python
"""Parse a PDF payload: extract text and render page images as analysis_frame attachments."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore[assignment]

from content_ingestion.core.models import Attachment, ContentAsset

MAX_FRAMES = 20
PAGE_RENDER_DPI = 150


def parse_pdf(
    payload_path: Path,
    metadata: dict,
    capture_manifest=None,
) -> ContentAsset:
    """Extract text and render page frames from a PDF payload."""
    if fitz is None:
        raise ImportError(
            "PyMuPDF is required for PDF parsing. Install it with: pip install pymupdf"
        )

    doc = fitz.open(str(payload_path))
    total_pages = len(doc)

    # --- Text extraction ---
    content_text = "\n\n".join(page.get_text() for page in doc)

    # --- Page frame rendering ---
    if total_pages <= MAX_FRAMES:
        frame_indices = list(range(total_pages))
    else:
        step = total_pages / MAX_FRAMES
        frame_indices = [int(i * step) for i in range(MAX_FRAMES)]

    frames_dir = payload_path.parent / "attachments" / "pages"
    frames_dir.mkdir(parents=True, exist_ok=True)

    attachments: list[Attachment] = []
    mat = fitz.Matrix(PAGE_RENDER_DPI / 72, PAGE_RENDER_DPI / 72)
    for idx in frame_indices:
        page = doc[idx]
        pix = page.get_pixmap(matrix=mat)
        frame_path = frames_dir / f"page_{idx:04d}.png"
        pix.save(str(frame_path))
        rel_path = frame_path.relative_to(payload_path.parent).as_posix()
        attachments.append(
            Attachment(
                id=f"frame-page-{idx:04d}",
                kind="image",
                role="analysis_frame",
                media_type="image/png",
                path=rel_path,
                description=f"Page {idx + 1} of {total_pages}",
            )
        )

    title = metadata.get("title_hint") or payload_path.stem
    return ContentAsset(
        source_url=metadata.get("source_url", ""),
        source_platform=metadata.get("platform", "local"),
        content_shape="document",
        title=title,
        content_text=content_text,
        attachments=attachments,
    )
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_pdf_parser.py -v
```

Expected: 4 tests pass (skip the fitz-import test if it's awkward to mock at module level — that's acceptable).

- [ ] **Step 5: Commit**

```bash
git add src/content_ingestion/raw/pdf_parser.py tests/unit/test_pdf_parser.py
git commit -m "feat(wsl): add pdf_parser with text extraction and page frame rendering"
```

---

### Task B3: `raw/image_parser.py` — image as analysis_frame

**Files:**
- Create: `src/content_ingestion/raw/image_parser.py`
- Create: `tests/unit/test_image_parser.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_image_parser.py`:

```python
from pathlib import Path
from content_ingestion.raw.image_parser import parse_image

FAKE_METADATA = {
    "job_id": "test_job",
    "source_url": "local://image/test_job",
    "platform": "local",
    "collector": "windows-client-local",
    "collected_at": "2026-04-12T00:00:00+00:00",
    "content_type": "image",
    "content_shape": "image",
    "requested_mode": "auto",
}


def test_parse_image_content_shape(tmp_path):
    img = tmp_path / "payload.png"
    img.write_bytes(b"\x89PNG fake")
    asset = parse_image(img, FAKE_METADATA)
    assert asset.content_shape == "image"


def test_parse_image_content_text_empty(tmp_path):
    img = tmp_path / "payload.png"
    img.write_bytes(b"\x89PNG fake")
    asset = parse_image(img, FAKE_METADATA)
    assert asset.content_text == ""


def test_parse_image_has_analysis_frame_attachment(tmp_path):
    img = tmp_path / "payload.png"
    img.write_bytes(b"\x89PNG fake")
    asset = parse_image(img, FAKE_METADATA)
    frames = [a for a in asset.attachments if a.role == "analysis_frame"]
    assert len(frames) == 1
    assert frames[0].media_type == "image/png"


def test_parse_image_copies_file(tmp_path):
    img = tmp_path / "payload.png"
    img.write_bytes(b"\x89PNG real content")
    asset = parse_image(img, FAKE_METADATA)
    copied = tmp_path / "attachments" / "image" / "source.png"
    assert copied.exists()
    assert copied.read_bytes() == b"\x89PNG real content"


def test_parse_image_jpeg(tmp_path):
    img = tmp_path / "payload.jpg"
    img.write_bytes(b"\xff\xd8\xff fake jpeg")
    asset = parse_image(img, FAKE_METADATA)
    frames = [a for a in asset.attachments if a.role == "analysis_frame"]
    assert frames[0].media_type == "image/jpeg"


def test_parse_image_source_platform(tmp_path):
    img = tmp_path / "payload.png"
    img.write_bytes(b"\x89PNG")
    asset = parse_image(img, FAKE_METADATA)
    assert asset.source_platform == "local"
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/unit/test_image_parser.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'content_ingestion.raw.image_parser'`

- [ ] **Step 3: Implement `image_parser.py`**

Create `src/content_ingestion/raw/image_parser.py`:

```python
"""Parse an image payload: register the image as an analysis_frame attachment."""
from __future__ import annotations

import shutil
from pathlib import Path

from content_ingestion.core.models import Attachment, ContentAsset

_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def parse_image(
    payload_path: Path,
    metadata: dict,
    capture_manifest=None,
) -> ContentAsset:
    """Register an image payload as a single analysis_frame attachment."""
    suffix = payload_path.suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix, "image/png")

    dest_dir = payload_path.parent / "attachments" / "image"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"source{suffix}"
    shutil.copy2(payload_path, dest)
    rel_path = dest.relative_to(payload_path.parent).as_posix()

    attachment = Attachment(
        id="frame-source-image",
        kind="image",
        role="analysis_frame",
        media_type=media_type,
        path=rel_path,
        description="Source image",
    )

    title = metadata.get("title_hint") or payload_path.stem
    return ContentAsset(
        source_url=metadata.get("source_url", ""),
        source_platform=metadata.get("platform", "local"),
        content_shape="image",
        title=title,
        content_text="",
        attachments=[attachment],
    )
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_image_parser.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Run full WSL suite**

```bash
python3 -m pytest tests/ -q
```

Expected: 96+ passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add src/content_ingestion/raw/image_parser.py tests/unit/test_image_parser.py
git commit -m "feat(wsl): add image_parser registering image as analysis_frame attachment"
```

---

### Task B4: `llm_pipeline.py` — image-only analysis branch

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Create: `tests/unit/test_analyze_image_asset.py`

- [ ] **Step 1: Define `IMAGE_ANALYSIS_SCHEMA` and `_image_analysis_instructions`**

In `src/content_ingestion/pipeline/llm_pipeline.py`, add after the existing schema constants (after `READER_SCHEMA`):

```python
IMAGE_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **_SHARED_EDITORIAL_SCHEMA_PROPS,
        "resolved_mode": {
            "type": "string",
            "enum": ["argument", "guide", "review"],
        },
        "author_thesis": {"type": "string"},
    },
    "required": [
        *_SHARED_EDITORIAL_REQUIRED,
        "resolved_mode",
        "author_thesis",
    ],
}
```

Add the instruction function near the other instruction functions:

```python
def _image_analysis_instructions() -> str:
    return """你是一位内容分析专家。你将收到一张图片，请仔细分析其内容并给出结构化的分析结果。

任务：
1. 判断图片内容最适合哪种分析模式（resolved_mode）：
   - argument：观点分析、议题讨论、评述类内容
   - guide：教程、操作指南、流程说明类内容
   - review：评测、推荐、品鉴类内容
2. 提炼图片核心信息，填写所有文本字段。

规则：
- 所有文本字段必须用中文填写
- core_summary：对图片内容的一句话核心概括
- bottom_line：读者最应该记住的一个判断或结论
- author_thesis：图片表达的核心论点或主题
- audience_fit：这张图最适合谁看
- save_worthy_points：3-5个值得记录的要点
- content_kind：内容类型（article/opinion/analysis/report/tutorial/review/news）
- author_stance：内容立场（objective/advocacy/critical/skeptical/promotional/explanatory/mixed）"""
```

- [ ] **Step 2: Add `_analyze_image_asset` function**

Add this function after `analyze_asset`:

```python
def _analyze_image_asset(
    job_dir: Path,
    asset: "ContentAsset",
    settings: "Settings",
) -> "LlmAnalysisResult":
    """Single multimodal LLM pass for image-only content. Skips Reader pass."""
    from content_ingestion.core.models import EditorialBase, EditorialResult, StructuredResult

    result = LlmAnalysisResult(
        status="pass",
        provider=settings.llm_provider,
        base_url=settings.openai_base_url,
        schema_mode="json_schema",
        analysis_model=settings.multimodal_model or settings.analysis_model,
        steps=[
            {"name": "resolve_openai_api_key", "status": "success", "details": "api key available"},
            {"name": "load_openai_sdk", "status": "success", "details": "openai package available"},
        ],
    )

    frame_paths = _collect_frame_paths(job_dir, asset)
    if not frame_paths:
        result.status = "skipped"
        result.skip_reason = "no image attachment found"
        result.steps.append({"name": "image_analysis", "status": "skipped", "details": "no analysis_frame attachment"})
        return result

    client = _create_client(settings)
    model = settings.multimodal_model or settings.analysis_model
    analysis_dir = job_dir / "analysis" / "llm"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # Build a minimal multimodal envelope: text context + image
    text_context = json.dumps({
        "task": "analyze_image",
        "source_url": asset.source_url,
        "title": asset.title or "",
    }, ensure_ascii=False)
    content: list[dict] = [{"type": "input_text", "text": text_context}]
    for frame_path in frame_paths[:1]:  # single image
        content.append({"type": "input_image", "image_url": _image_data_url(frame_path)})
    input_payload = [{"role": "user", "content": content}]

    try:
        payload = _call_structured_response(
            client=client,
            model=model,
            instructions=_image_analysis_instructions(),
            input_payload=input_payload,
            schema_name="image_analysis",
            schema=IMAGE_ANALYSIS_SCHEMA,
        )
    except Exception as exc:
        result.status = "skipped"
        result.skip_reason = f"image analysis LLM call failed: {exc}"
        result.steps.append({"name": "image_analysis", "status": "skipped", "details": str(exc)})
        return result

    (analysis_dir / "image_analysis_result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result.steps.append({"name": "image_analysis", "status": "success", "details": model})

    resolved_mode = str(payload.get("resolved_mode") or "argument")
    result.resolved_mode = resolved_mode
    result.requested_mode = "auto"
    result.mode_confidence = 1.0

    editorial_base = EditorialBase(
        core_summary=str(payload.get("core_summary") or ""),
        bottom_line=str(payload.get("bottom_line") or ""),
        content_kind=str(payload.get("content_kind") or ""),
        author_stance=str(payload.get("author_stance") or ""),
        audience_fit=str(payload.get("audience_fit") or ""),
        save_worthy_points=list(payload.get("save_worthy_points") or []),
    )
    mode_payload = {"author_thesis": str(payload.get("author_thesis") or "")}
    product_view = _build_product_view(resolved_mode, editorial_base, mode_payload)

    structured_result = StructuredResult(
        content_kind=editorial_base.content_kind,
        author_stance=editorial_base.author_stance,
        editorial=EditorialResult(
            resolved_mode=resolved_mode,
            mode_confidence=1.0,
            base=editorial_base,
            mode_payload=mode_payload,
        ),
        product_view=product_view,
    )
    result.structured_result = structured_result
    result.content_kind = editorial_base.content_kind
    result.author_stance = editorial_base.author_stance
    result.summary = editorial_base.core_summary

    # Optionally generate visual summary card
    insight_card_path = None
    if settings.image_card_model:
        try:
            from google import genai
            from google.genai import types as genai_types
            from content_ingestion.pipeline.visual_summary import generate_visual_summary
            image_api_key = settings.image_card_api_key or settings.openai_api_key
            image_base_url = settings.image_card_base_url or "https://zenmux.ai/api/vertex-ai"
            image_client = genai.Client(
                api_key=image_api_key, vertexai=True,
                http_options=genai_types.HttpOptions(api_version="v1", base_url=image_base_url),
            )
            card_output = job_dir / "analysis" / "insight_card.png"
            card_step = generate_visual_summary(
                client=image_client, model=settings.image_card_model,
                structured_result=structured_result, resolved_mode=resolved_mode,
                asset_title=asset.title or "", output_path=card_output,
            )
            result.steps.append(card_step)
            if card_step["status"] == "success":
                insight_card_path = card_output.relative_to(job_dir).as_posix()
        except Exception as exc:
            result.warnings.append(f"Visual summary card skipped: {exc}")

    output_path = analysis_dir / "analysis_result.json"
    output_path.write_text(
        json.dumps({
            "status": result.status,
            "resolved_mode": result.resolved_mode,
            "requested_mode": result.requested_mode,
            "result": _serialize_structured_result(result.structured_result),
            "summary": result.summary,
            "insight_card_path": insight_card_path,
            "warnings": result.warnings,
            "steps": result.steps,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result.output_path = output_path.relative_to(job_dir).as_posix()
    return result
```

- [ ] **Step 3: Add the branch in `analyze_asset`**

Find the start of `analyze_asset`. Add the image branch immediately after the `openai_sdk_available()` check:

```python
def analyze_asset(job_dir, asset, settings, requested_mode="auto"):
    # ... existing early returns for missing API key / SDK ...

    # Image-only path: skip Reader pass, run single multimodal call
    if asset.content_shape == "image":
        return _analyze_image_asset(job_dir, asset, settings)

    # ... existing Reader → Synthesizer flow unchanged ...
```

- [ ] **Step 4: Write tests for the image branch**

Create `tests/unit/test_analyze_image_asset.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch
from content_ingestion.core.models import ContentAsset, Attachment
from content_ingestion.pipeline.llm_pipeline import analyze_asset


def _make_image_asset(job_dir: Path) -> ContentAsset:
    img_dir = job_dir / "attachments" / "image"
    img_dir.mkdir(parents=True)
    img_file = img_dir / "source.png"
    img_file.write_bytes(b"\x89PNG")
    return ContentAsset(
        source_url="local://image/test",
        source_platform="local",
        content_shape="image",
        title="Test Image",
        content_text="",
        attachments=[
            Attachment(
                id="frame-source-image",
                kind="image",
                role="analysis_frame",
                media_type="image/png",
                path="attachments/image/source.png",
                description="Source image",
            )
        ],
    )


def _fake_image_payload():
    return {
        "core_summary": "这是一张测试图片的核心摘要",
        "bottom_line": "底线结论",
        "content_kind": "analysis",
        "author_stance": "objective",
        "audience_fit": "通用读者",
        "save_worthy_points": ["要点一", "要点二"],
        "resolved_mode": "argument",
        "author_thesis": "核心论点",
    }


def test_analyze_asset_takes_image_branch(tmp_path):
    asset = _make_image_asset(tmp_path)
    settings = MagicMock()
    settings.openai_api_key = "sk-test"
    settings.analysis_model = "gpt-5.2"
    settings.multimodal_model = "gpt-5.2"
    settings.image_card_model = None
    settings.openai_base_url = None
    settings.llm_provider = "zenmux"

    with patch("content_ingestion.pipeline.llm_pipeline.openai_sdk_available", return_value=True), \
         patch("content_ingestion.pipeline.llm_pipeline._create_client"), \
         patch("content_ingestion.pipeline.llm_pipeline._call_structured_response",
               return_value=_fake_image_payload()), \
         patch("content_ingestion.pipeline.llm_pipeline._image_data_url", return_value="data:image/png;base64,fake"):
        result = analyze_asset(job_dir=tmp_path, asset=asset, settings=settings)

    assert result.status == "pass"
    assert result.resolved_mode == "argument"
    assert result.summary == "这是一张测试图片的核心摘要"


def test_analyze_image_skips_reader_pass(tmp_path):
    """Verify Reader pass is NOT called for image content."""
    asset = _make_image_asset(tmp_path)
    settings = MagicMock()
    settings.openai_api_key = "sk-test"
    settings.analysis_model = "gpt-5.2"
    settings.multimodal_model = "gpt-5.2"
    settings.image_card_model = None
    settings.openai_base_url = None
    settings.llm_provider = "zenmux"

    call_count = {"n": 0}

    def fake_call(**kwargs):
        call_count["n"] += 1
        return _fake_image_payload()

    with patch("content_ingestion.pipeline.llm_pipeline.openai_sdk_available", return_value=True), \
         patch("content_ingestion.pipeline.llm_pipeline._create_client"), \
         patch("content_ingestion.pipeline.llm_pipeline._call_structured_response",
               side_effect=fake_call), \
         patch("content_ingestion.pipeline.llm_pipeline._image_data_url", return_value="data:image/png;base64,fake"):
        analyze_asset(job_dir=tmp_path, asset=asset, settings=settings)

    # Only 1 LLM call (image analysis), not 2 (reader + synthesizer)
    assert call_count["n"] == 1


def test_analyze_image_no_frame_returns_skipped(tmp_path):
    asset = ContentAsset(
        source_url="local://image/test",
        source_platform="local",
        content_shape="image",
        title="Empty",
        content_text="",
        attachments=[],  # no frame
    )
    settings = MagicMock()
    settings.openai_api_key = "sk-test"
    settings.analysis_model = "gpt-5.2"
    settings.multimodal_model = "gpt-5.2"
    settings.image_card_model = None
    settings.openai_base_url = None
    settings.llm_provider = "zenmux"

    with patch("content_ingestion.pipeline.llm_pipeline.openai_sdk_available", return_value=True), \
         patch("content_ingestion.pipeline.llm_pipeline._create_client"):
        result = analyze_asset(job_dir=tmp_path, asset=asset, settings=settings)

    assert result.status == "skipped"
```

- [ ] **Step 5: Run tests**

```bash
python3 -m pytest tests/unit/test_analyze_image_asset.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Run full WSL suite**

```bash
python3 -m pytest tests/ -q
```

Expected: 99+ passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_analyze_image_asset.py
git commit -m "feat(wsl): add image-only analysis branch skipping Reader pass"
```

---

## GPT Handoff

After Stream A and B are complete, write a handoff to `data/collab/handoff/claude-to-gpt-2026-04-12-local-file-ui.md` covering:

1. **File button placement** — where in the existing toolbar/URL bar to add the open-file button, icon suggestion, label
2. **Drag-and-drop visual feedback** — border highlight or overlay when dragging a file over the window
3. **Paste detection UX** — brief chip or footer message "检测到图片，正在提交..." before/during submission
4. **Result page adjustments for local files:**
   - Hero byline: hide `file://...` and `local://...` URLs; show filename or "本地文件" instead
   - "Open source" action button: hide for `platform == "local"`, optionally replace with "Show in Explorer" for `file://` source_url
   - Empty title state: when `asset.title` is empty (pasted text/image), show "未命名文档" or derive from first line of content

---

## Final Verification

After all tasks complete:

```bash
# Windows
cd .worktrees/local-file-ingestion
python -m pytest tests/unit/ -q

# WSL
cd /home/ahzz1207/codex-demo
python3 -m pytest tests/ -q
```

Both suites must pass before merging.
