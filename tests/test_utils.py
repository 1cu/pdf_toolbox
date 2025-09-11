import sys
from pathlib import Path

from pdf_toolbox._fitz import fitz

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import pytest

from pdf_toolbox.utils import (
    ensure_libs,
    open_pdf,
    parse_page_spec,
    sane_output_dir,
    save_pdf,
    update_metadata,
)


def test_sane_output_dir(tmp_path):
    base = tmp_path / "input.pdf"
    base.write_text("data")
    target = sane_output_dir(base, None)
    assert target == tmp_path

    custom = tmp_path / "out"
    result = sane_output_dir(base, custom)
    assert result == custom
    assert custom.exists()


def test_sane_output_dir_rejects_file(tmp_path):
    base = tmp_path / "input.pdf"
    base.write_text("data")
    file_target = tmp_path / "out.png"
    with pytest.raises(ValueError, match="directory, not a file"):
        sane_output_dir(base, file_target)


def test_update_metadata(tmp_path):
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({})
    update_metadata(doc, "note")
    meta = doc.metadata
    assert "note" in meta.get("subject", "")
    assert meta.get("author") == "Tester"


def test_open_save_pdf(tmp_path):
    doc = fitz.open()
    doc.new_page()
    out = tmp_path / "test.pdf"
    save_pdf(doc, out)
    reopened = open_pdf(out)
    assert reopened.page_count == 1
    reopened.close()


def test_ensure_libs_missing(monkeypatch):
    monkeypatch.setattr(
        "pdf_toolbox.utils.REQUIRED_LIBS", ["nonexistent_mod"], raising=False
    )
    with pytest.raises(RuntimeError, match="see documentation"):
        ensure_libs()


def test_ensure_libs_missing_hint(monkeypatch):
    import importlib

    original = importlib.import_module

    def fake_import(name, *args, **kwargs):
        if name == "PIL.Image":
            raise ImportError
        return original(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr("pdf_toolbox.utils.REQUIRED_LIBS", ["PIL.Image"], raising=False)

    with pytest.raises(RuntimeError, match="pip install pillow"):
        ensure_libs()


def test_ensure_libs_ok(monkeypatch):
    monkeypatch.setattr("pdf_toolbox.utils.REQUIRED_LIBS", ["sys"], raising=False)
    ensure_libs()


def test_ensure_libs_skips_win32(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(
        "pdf_toolbox.utils.REQUIRED_LIBS", ["win32com.client"], raising=False
    )
    ensure_libs()


def test_parse_page_spec_examples():
    assert parse_page_spec(None, 6) == [1, 2, 3, 4, 5, 6]
    assert parse_page_spec("1-2", 6) == [1, 2]
    assert parse_page_spec("1", 6) == [1]
    assert parse_page_spec("-2", 6) == [1, 2]
    assert parse_page_spec("1,5,6", 6) == [1, 5, 6]
    assert parse_page_spec("1-", 3) == [1, 2, 3]


def test_parse_page_spec_invalid():
    with pytest.raises(ValueError):
        parse_page_spec("2-1", 5)
    with pytest.raises(ValueError):
        parse_page_spec("0", 5)
    with pytest.raises(ValueError):
        parse_page_spec("a", 5)
