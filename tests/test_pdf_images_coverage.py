"""Additional tests to improve pdf_images.py coverage."""

from __future__ import annotations

import fitz
import pytest
from PIL import Image

from pdf_toolbox.actions.pdf_images import (
    PdfImageOptions,
    pdf_to_images,
)


@pytest.mark.slow
def test_large_pdf_triggers_batching(tmp_path):
    """Test that a PDF with >200 pages triggers auto-batching."""
    # Create a PDF with 201 pages to exceed BATCH_THRESHOLD_PAGES (200)
    doc = fitz.open()
    for _ in range(201):
        doc.new_page(width=10, height=10)
    pdf_path = tmp_path / "large.pdf"
    doc.save(pdf_path)
    doc.close()

    # This should trigger the batch_size=10 path (line 229)
    outputs = pdf_to_images(
        str(pdf_path),
        PdfImageOptions(dpi=72, image_format="PNG", out_dir=str(tmp_path)),
    )
    assert len(outputs) == 201


def test_webp_with_quality_preset(noise_pdf, tmp_path):
    """Test WebP encoding with quality preset (lines 292-293)."""
    outputs = pdf_to_images(
        noise_pdf,
        PdfImageOptions(
            image_format="WEBP",
            quality="Low (70)",
            out_dir=str(tmp_path),
        ),
    )
    assert len(outputs) == 1
    assert outputs[0].endswith(".webp")


def test_tiff_format_encoding(noise_pdf, tmp_path):
    """Test TIFF format encoding (lines 368-370)."""
    outputs = pdf_to_images(
        noise_pdf,
        PdfImageOptions(
            image_format="TIFF",
            out_dir=str(tmp_path),
        ),
    )
    assert len(outputs) == 1
    with Image.open(outputs[0]) as img:
        assert img.format == "TIFF"


@pytest.fixture
def noise_pdf(tmp_path):
    """Create a minimal noise PDF for testing."""
    doc = fitz.open()
    page = doc.new_page(width=32, height=32)
    # Add some content
    rect = fitz.Rect(0, 0, 32, 32)
    page.draw_rect(rect, color=(1, 0, 0), fill=(0.5, 0.5, 0.5))
    pdf_path = tmp_path / "noise.pdf"
    doc.save(pdf_path)
    doc.close()
    return str(pdf_path)
