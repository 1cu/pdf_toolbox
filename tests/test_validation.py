from pathlib import Path

import pytest

from pdf_toolbox.validation import (
    SUPPORTED_INPUT_SUFFIXES,
    is_supported_input,
    validate_config,
    validate_pdf_path,
)


def test_validate_pdf_path_ok(tmp_path):
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("data")
    assert validate_pdf_path(str(pdf_path)) == pdf_path.resolve()


def test_validate_pdf_path_rejects_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="File not found"):
        validate_pdf_path(tmp_path / "missing.pdf")


def test_validate_pdf_path_rejects_dir(tmp_path):
    directory = tmp_path / "d"
    directory.mkdir()
    with pytest.raises(IsADirectoryError, match="Expected a file"):
        validate_pdf_path(directory)


def test_validate_pdf_path_rejects_non_pdf(tmp_path):
    pdf_path = tmp_path / "a.png"
    pdf_path.write_text("data")
    with pytest.raises(ValueError, match="must be one of PDF"):
        validate_pdf_path(pdf_path)


def test_validate_pdf_path_accepts_pptx(tmp_path):
    pptx_path = tmp_path / "deck.PPTX"
    pptx_path.write_text("data")
    assert validate_pdf_path(pptx_path, allowed_suffixes={".pdf", ".pptx"}) == pptx_path.resolve()


def test_validate_pdf_path_normalises_suffixes(tmp_path):
    pptx_path = tmp_path / "deck.PPTX"
    pptx_path.write_text("data")
    assert validate_pdf_path(pptx_path, allowed_suffixes={"pdf", "pptx"}) == pptx_path.resolve()


def test_is_supported_input_handles_pdf_and_pptx():
    assert is_supported_input("file.pdf")
    assert is_supported_input(Path("deck.PPTX"))
    assert not is_supported_input("notes.txt")


def test_supported_input_suffixes_are_frozen_and_constant():
    assert isinstance(SUPPORTED_INPUT_SUFFIXES, frozenset)
    assert frozenset({".pdf", ".pptx"}) == SUPPORTED_INPUT_SUFFIXES
    extended = SUPPORTED_INPUT_SUFFIXES | {".docx"}
    assert ".docx" not in SUPPORTED_INPUT_SUFFIXES
    assert extended != SUPPORTED_INPUT_SUFFIXES
    with pytest.raises(AttributeError):
        object.__getattribute__(SUPPORTED_INPUT_SUFFIXES, "add")


def test_validate_config_ok():
    config = {"author": "A", "email": "a@example.com"}
    assert validate_config(config) == config


def test_validate_config_missing():
    with pytest.raises(ValueError, match="Missing required config field"):
        validate_config({"author": "A"})
