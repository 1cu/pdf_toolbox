import runpy
import sys
from pathlib import Path


def run_cli(module: str, argv: list[str], monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    sys.modules.pop(f"pdf_toolbox.{module}", None)
    runpy.run_module(f"pdf_toolbox.{module}", run_name="__main__")


def test_docx_cli(pdf_with_image, tmp_path, monkeypatch):
    run_cli(
        "docx",
        ["docx.py", pdf_with_image, "--out-dir", str(tmp_path)],
        monkeypatch,
    )
    assert (tmp_path / f"{Path(pdf_with_image).stem}.docx").exists()


def test_extract_cli_extract(sample_pdf, tmp_path, monkeypatch):
    run_cli(
        "extract",
        [
            "extract.py",
            sample_pdf,
            "extract",
            "1-2",
            "--out-dir",
            str(tmp_path),
        ],
        monkeypatch,
    )
    assert (tmp_path / f"{Path(sample_pdf).stem}_Extract_1_2.pdf").exists()


def test_extract_cli_split(sample_pdf, tmp_path, monkeypatch):
    run_cli(
        "extract",
        [
            "extract.py",
            sample_pdf,
            "split",
            "1",
            "--out-dir",
            str(tmp_path),
        ],
        monkeypatch,
    )
    assert (tmp_path / f"{Path(sample_pdf).stem}_Split_1_1.pdf").exists()


def test_optimize_cli(sample_pdf, tmp_path, monkeypatch):
    run_cli(
        "optimize",
        ["optimize.py", sample_pdf, "--keep", "--out-dir", str(tmp_path)],
        monkeypatch,
    )
    assert (tmp_path / f"{Path(sample_pdf).stem}_optimized_default.pdf").exists()


def test_repair_cli(sample_pdf, tmp_path, monkeypatch):
    run_cli(
        "repair",
        ["repair.py", sample_pdf, "--out-dir", str(tmp_path)],
        monkeypatch,
    )
    assert (tmp_path / f"{Path(sample_pdf).stem}_repaired.pdf").exists()


def test_unlock_cli(sample_pdf, tmp_path, monkeypatch):
    run_cli(
        "unlock",
        ["unlock.py", sample_pdf, "--out-dir", str(tmp_path)],
        monkeypatch,
    )
    assert (tmp_path / f"{Path(sample_pdf).stem}_unlocked.pdf").exists()
