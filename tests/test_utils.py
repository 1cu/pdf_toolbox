import sys
from pathlib import Path

import fitz

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import pytest

from pdf_toolbox.utils import ensure_libs, sane_output_dir, update_metadata


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


def test_ensure_libs_missing(monkeypatch):
    monkeypatch.setattr(
        "pdf_toolbox.utils.REQUIRED_LIBS", ["nonexistent_mod"], raising=False
    )
    with pytest.raises(RuntimeError):
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
