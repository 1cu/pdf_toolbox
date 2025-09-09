import sys
from pathlib import Path

import fitz
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from pdf_toolbox.extract import extract_range, split_pdf


def _create_pdf(tmp_path: Path, pages: int) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    path = tmp_path / "input.pdf"
    doc.save(path)
    return path


def test_extract_range_valid(tmp_path):
    pdf_path = _create_pdf(tmp_path, 3)
    out = extract_range(str(pdf_path), 1, 2)
    result = fitz.open(out)
    assert result.page_count == 2


def test_extract_range_invalid_start(tmp_path):
    pdf_path = _create_pdf(tmp_path, 3)
    with pytest.raises(ValueError, match="start_page must be >= 1"):
        extract_range(str(pdf_path), 0, 2)


def test_extract_range_start_gt_end(tmp_path):
    pdf_path = _create_pdf(tmp_path, 3)
    with pytest.raises(
        ValueError, match=r"start_page \(3\) must not exceed end_page \(2\)"
    ):
        extract_range(str(pdf_path), 3, 2)


def test_extract_range_end_gt_pagecount(tmp_path):
    pdf_path = _create_pdf(tmp_path, 3)
    with pytest.raises(
        ValueError, match=r"end_page \(5\) exceeds document page count \(3\)"
    ):
        extract_range(str(pdf_path), 1, 5)


def test_split_pdf_valid(tmp_path):
    pdf_path = _create_pdf(tmp_path, 5)
    outputs = split_pdf(str(pdf_path), 2)
    assert len(outputs) == 3
    counts = [fitz.open(p).page_count for p in outputs]
    assert counts == [2, 2, 1]


def test_split_pdf_invalid_pages(tmp_path):
    pdf_path = _create_pdf(tmp_path, 3)
    with pytest.raises(ValueError, match="pages_per_file must be >= 1"):
        split_pdf(str(pdf_path), 0)
