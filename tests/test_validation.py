import pytest

from pdf_toolbox.validation import validate_config, validate_pdf_path


def test_validate_pdf_path_ok(tmp_path):
    p = tmp_path / "a.pdf"
    p.write_text("data")
    assert validate_pdf_path(str(p)) == p


def test_validate_pdf_path_rejects_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_pdf_path(tmp_path / "missing.pdf")


def test_validate_pdf_path_rejects_dir(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    with pytest.raises(IsADirectoryError):
        validate_pdf_path(d)


def test_validate_pdf_path_rejects_non_pdf(tmp_path):
    p = tmp_path / "a.png"
    p.write_text("data")
    with pytest.raises(ValueError):
        validate_pdf_path(p)


def test_validate_config_ok():
    cfg = {"author": "A", "email": "a@example.com"}
    assert validate_config(cfg) == cfg


def test_validate_config_missing():
    with pytest.raises(ValueError):
        validate_config({"author": "A"})
