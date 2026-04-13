import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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
    parts = job_id.split("_")
    assert len(parts) == 3
    assert len(parts[0]) == 8
    assert len(parts[1]) == 6
    assert len(parts[2]) == 6
