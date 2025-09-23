"""End-to-end coverage for high-level actions."""

from __future__ import annotations

import json
import math
from pathlib import Path

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-
import pytest
from PIL import Image

from pdf_toolbox.actions.extract import extract_range, split_pdf
from pdf_toolbox.actions.miro import miro_export
from pdf_toolbox.actions.pdf_images import DPI_PRESETS, pdf_to_images
from pdf_toolbox.actions.unlock import unlock_pdf


def test_extract_range_e2e(sample_pdf: str, tmp_path: Path) -> None:
    """`extract_range` writes the expected subset with metadata."""
    output = Path(extract_range(sample_pdf, "1-2", out_dir=str(tmp_path)))

    assert output.exists()

    with fitz.open(output) as doc:
        assert doc.page_count == 2
        metadata = doc.metadata or {}
        assert metadata.get("author") == "Tester"
        assert metadata.get("subject", "").endswith("extract_range")


def test_split_pdf_e2e(sample_pdf: str, tmp_path: Path) -> None:
    """`split_pdf` emits sequential chunks with the right page counts."""
    outputs = [Path(path) for path in split_pdf(sample_pdf, 2, out_dir=str(tmp_path))]

    assert [path.exists() for path in outputs] == [True, True]

    counts: list[int] = []
    for path in outputs:
        with fitz.open(path) as doc:
            counts.append(doc.page_count)
            metadata = doc.metadata or {}
            assert metadata.get("author") == "Tester"
            assert metadata.get("subject", "").endswith("split_pdf")

    assert counts == [2, 1]


def test_pdf_to_images_e2e(sample_pdf: str, tmp_path: Path) -> None:
    """`pdf_to_images` renders with DPI and dimension/size overrides."""
    dpi_outputs = pdf_to_images(
        sample_pdf,
        pages="2",
        image_format="PNG",
        dpi="High (300 dpi)",
        out_dir=str(tmp_path),
    )

    assert len(dpi_outputs) == 1
    dpi_image_path = Path(dpi_outputs[0])
    assert dpi_image_path.exists()

    with Image.open(dpi_image_path) as img:
        dpi_width_px, dpi_height_px = img.size
        assert img.format == "PNG"
        assert dpi_width_px > 0
        assert dpi_height_px > 0

    with fitz.open(sample_pdf) as doc:
        page = doc.load_page(1)
        rect = page.rect
        expected_width = math.ceil(rect.width / 72 * DPI_PRESETS["High (300 dpi)"])
        expected_height = math.ceil(rect.height / 72 * DPI_PRESETS["High (300 dpi)"])

    assert (dpi_width_px, dpi_height_px) == (expected_width, expected_height)

    dimension_dir = tmp_path / "dimensions"
    max_size_mb = 1.0
    dimension_outputs = pdf_to_images(
        sample_pdf,
        pages="1-2",
        image_format="JPEG",
        width=640,
        height=480,
        quality="Medium (85)",
        max_size_mb=max_size_mb,
        out_dir=str(dimension_dir),
    )

    assert len(dimension_outputs) == 2
    max_bytes = int(max_size_mb * 1024 * 1024)
    with fitz.open(sample_pdf) as doc:
        first = doc.load_page(0)
        rect = first.rect
        w_in = rect.width / 72
        h_in = rect.height / 72
        expected_dpi = round(max(640 / w_in, 480 / h_in))
        expected_dim_width = math.ceil(rect.width / 72 * expected_dpi)
        expected_dim_height = math.ceil(rect.height / 72 * expected_dpi)

    for output in dimension_outputs:
        path = Path(output)
        assert path.exists()
        assert path.suffix.lower() == ".jpeg"
        assert path.stat().st_size <= max_bytes
        with Image.open(path) as img:
            width_px, height_px = img.size
            assert img.format == "JPEG"
            assert (width_px, height_px) == (
                expected_dim_width,
                expected_dim_height,
            )


def test_unlock_pdf_e2e(tmp_path: Path) -> None:
    """`unlock_pdf` removes encryption and preserves content."""
    protected = tmp_path / "protected.pdf"
    doc = fitz.open()
    try:
        page = doc.new_page(width=200, height=200)
        page.insert_text((72, 72), "Locked page")
        doc.save(
            str(protected),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="secret",
        )
    finally:
        doc.close()

    locked = fitz.open(str(protected))
    try:
        assert bool(locked.needs_pass)
        assert not locked.authenticate("wrong")
        assert locked.authenticate("secret")
    finally:
        locked.close()

    output = Path(unlock_pdf(str(protected), password="secret", out_dir=str(tmp_path)))

    assert output.exists()

    with fitz.open(output) as unlocked:
        assert not bool(unlocked.needs_pass)
        text = unlocked.load_page(0).get_text().strip()
        assert "Locked" in text
        metadata = unlocked.metadata or {}
        assert metadata.get("author") == "Tester"
        assert metadata.get("subject", "").endswith("unlocked")


@pytest.mark.parametrize(
    "profile",
    ["custom", "standard"],
    ids=["custom", "legacy-standard"],
)
def test_miro_export_custom_profile_e2e(
    sample_pdf: str, tmp_path: Path, profile: str
) -> None:
    """Custom and legacy "standard" exports delegate to the image renderer."""
    out_dir = tmp_path / profile
    outputs = [
        Path(path)
        for path in miro_export(
            sample_pdf,
            out_dir=str(out_dir),
            export_profile=profile,
            image_format="JPEG",
            dpi="Medium (150 dpi)",
            quality="Medium (85)",
            pages="1-2",
        )
    ]

    assert len(outputs) == 2
    for path in outputs:
        assert path.exists()
        with Image.open(path) as img:
            assert img.format == "JPEG"
            width_px, height_px = img.size
            assert width_px > 0
            assert height_px > 0


def test_miro_export_miro_profile_e2e(sample_pdf: str, tmp_path: Path) -> None:
    """The Miro profile generates a manifest alongside exported pages."""
    out_dir = tmp_path / "miro"
    outputs = [
        Path(path)
        for path in miro_export(
            sample_pdf,
            out_dir=str(out_dir),
            export_profile="miro",
            pages="1-2",
        )
    ]

    assert len(outputs) == 2
    for path in outputs:
        assert path.exists()
        assert path.stat().st_size > 0

    manifest_path = out_dir / "miro_export.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert [entry["page"] for entry in manifest] == [1, 2]
    for entry, path in zip(manifest, outputs, strict=False):
        fmt = entry.get("format")
        if fmt:
            assert path.suffix.lower() == f".{fmt.lower()}"
        if entry.get("vector_export"):
            assert path.suffix.lower() == ".svg"
        assert entry.get("filesize_bytes", 0) > 0
