from pathlib import Path

import pytest

from pdf_toolbox.builtin.extract import extract_range, split_pdf


def test_extract_range(sample_pdf, tmp_path):
    output = extract_range(sample_pdf, "1-2", out_dir=str(tmp_path))
    assert Path(output).exists()


def test_extract_range_open_end(sample_pdf, tmp_path):
    output = extract_range(sample_pdf, "2-", out_dir=str(tmp_path))
    assert Path(output).exists()


def test_extract_range_single_page(sample_pdf, tmp_path):
    output = extract_range(sample_pdf, "2", out_dir=str(tmp_path))
    assert Path(output).exists()


def test_extract_range_multiple(sample_pdf, tmp_path):
    output = extract_range(sample_pdf, "1,3", out_dir=str(tmp_path))
    assert Path(output).exists()


def test_extract_range_to_page(sample_pdf, tmp_path):
    output = extract_range(sample_pdf, "-2", out_dir=str(tmp_path))
    assert Path(output).exists()


def test_extract_range_default_outdir(sample_pdf):
    output = extract_range(sample_pdf, "1-2")
    assert Path(output).parent == Path(sample_pdf).parent


def test_extract_range_invalid(sample_pdf, tmp_path):
    with pytest.raises(ValueError, match="out of range"):
        extract_range(sample_pdf, "0-2", out_dir=str(tmp_path))
    with pytest.raises(ValueError, match="end must be greater"):
        extract_range(sample_pdf, "2-1", out_dir=str(tmp_path))
    with pytest.raises(ValueError, match="out of range"):
        extract_range(sample_pdf, "1-5", out_dir=str(tmp_path))


def test_split_pdf(sample_pdf, tmp_path):
    outputs = split_pdf(sample_pdf, 2, out_dir=str(tmp_path))
    assert len(outputs) == 2
    assert all(Path(output_path).exists() for output_path in outputs)
