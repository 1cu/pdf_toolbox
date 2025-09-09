import sys
from pathlib import Path

import fitz

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import pdf_toolbox.unlock as unlock_module


def test_unlock_pdf(tmp_path, monkeypatch):
    sample = Path(__file__).parent / "fixtures" / "sample_locked.pdf"
    locked = tmp_path / "locked.pdf"
    locked.write_bytes(sample.read_bytes())

    original_open = fitz.open

    def open_with_password(filename, password="", **kwargs):
        doc = original_open(filename, **kwargs)
        if password:
            doc.authenticate(password)
        return doc

    monkeypatch.setattr(unlock_module, "fitz", fitz)
    monkeypatch.setattr(unlock_module.fitz, "open", open_with_password)

    out = unlock_module.unlock_pdf(str(locked), password="secret", out_dir=str(tmp_path))
    out_path = Path(out)
    assert out_path.exists()
    with fitz.open(out_path) as doc:
        assert not doc.is_encrypted
