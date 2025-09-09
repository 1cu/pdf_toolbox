from pathlib import Path

import pytest

from pdf_toolbox.extract import extract_range, split_pdf


def test_extract_range(sample_pdf, tmp_path):
    out = extract_range(sample_pdf, 1, 2, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_extract_range_invalid(sample_pdf, tmp_path):
    with pytest.raises(ValueError):
        extract_range(sample_pdf, 0, 2, out_dir=str(tmp_path))
    with pytest.raises(ValueError):
        extract_range(sample_pdf, 2, 1, out_dir=str(tmp_path))
    with pytest.raises(ValueError):
        extract_range(sample_pdf, 1, 5, out_dir=str(tmp_path))


def test_split_pdf(sample_pdf, tmp_path):
    outputs = split_pdf(sample_pdf, 2, out_dir=str(tmp_path))
    assert len(outputs) == 2
    assert all(Path(p).exists() for p in outputs)
