import sys
import stat
import pytest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.input_router import (
    FilePayload,
    ImagePayload,
    LocalInputError,
    TextPayload,
    UrlPayload,
    route_clipboard_image,
    route_file,
    route_text,
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
        mock_stat.return_value.st_mode = stat.S_IFREG
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
