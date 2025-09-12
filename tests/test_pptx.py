import shutil
import subprocess
from pathlib import Path

import pytest
from pptx import Presentation

from pdf_toolbox.pdf_pptx import pptx_to_images


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "TIFF", "SVG"])
def test_pptx_to_images_requires_libreoffice(tmp_path, fmt, monkeypatch):
    pptx_path = tmp_path / "dummy.pptx"
    Presentation().save(pptx_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        pptx_to_images(str(pptx_path), image_format=fmt)


def test_pptx_to_images_invalid_format(tmp_path):
    pptx_path = tmp_path / "dummy.pptx"
    Presentation().save(pptx_path)
    with pytest.raises(ValueError):
        pptx_to_images(str(pptx_path), image_format="BMP")


def test_pptx_to_images_converts(tmp_path, monkeypatch, sample_pdf):
    pptx_path = tmp_path / "sample.pptx"
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[5])
    prs.save(pptx_path)

    def fake_which(name: str):
        return "/usr/bin/libreoffice"

    def fake_run(cmd, **kwargs):
        outdir = Path(cmd[cmd.index("--outdir") + 1])
        pdf_target = outdir / f"{pptx_path.stem}.pdf"
        pdf_target.write_bytes(Path(sample_pdf).read_bytes())
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)

    out_dir = tmp_path / "out"
    images = pptx_to_images(
        str(pptx_path), image_format="PNG", slides="1", out_dir=str(out_dir)
    )
    assert len(images) == 1
    assert Path(images[0]).is_file()
