from pathlib import Path
import runpy
import sys


def test_docx_cli(pdf_with_image, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["docx.py", pdf_with_image, "--out-dir", str(tmp_path)]
    )
    runpy.run_module("pdf_toolbox.docx", run_name="__main__")
    assert (tmp_path / f"{Path(pdf_with_image).stem}.docx").exists()


def test_extract_cli_extract(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract.py",
            sample_pdf,
            "extract",
            "1-2",
            "--out-dir",
            str(tmp_path),
        ],
    )
    runpy.run_module("pdf_toolbox.extract", run_name="__main__")
    assert (tmp_path / f"{Path(sample_pdf).stem}_Auszug_1_2.pdf").exists()


def test_extract_cli_split(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract.py",
            sample_pdf,
            "split",
            "1",
            "--out-dir",
            str(tmp_path),
        ],
    )
    runpy.run_module("pdf_toolbox.extract", run_name="__main__")
    assert (tmp_path / f"{Path(sample_pdf).stem}_Split_1_1.pdf").exists()


def test_optimize_cli(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["optimize.py", sample_pdf, "--keep", "--out-dir", str(tmp_path)],
    )
    runpy.run_module("pdf_toolbox.optimize", run_name="__main__")
    assert (tmp_path / f"{Path(sample_pdf).stem}_optimized_default.pdf").exists()


def test_repair_cli(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["repair.py", sample_pdf, "--out-dir", str(tmp_path)]
    )
    runpy.run_module("pdf_toolbox.repair", run_name="__main__")
    assert (tmp_path / f"{Path(sample_pdf).stem}_repaired.pdf").exists()


def test_unlock_cli(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["unlock.py", sample_pdf, "--out-dir", str(tmp_path)]
    )
    runpy.run_module("pdf_toolbox.unlock", run_name="__main__")
    assert (tmp_path / f"{Path(sample_pdf).stem}_unlocked.pdf").exists()
