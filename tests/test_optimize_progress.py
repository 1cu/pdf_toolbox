from pathlib import Path

import fitz  # type: ignore

from pdf_toolbox.builtin.optimize import optimize_pdf


def _pdf_with_pages(path, pages=2):
    document = fitz.open()
    for page_index in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"Page {page_index + 1}")

    document.save(path)
    document.close()


def test_optimize_with_progress_no_compress(tmp_path):
    pdf_path = tmp_path / "in.pdf"
    _pdf_with_pages(pdf_path, pages=2)
    seen: list[tuple[int, int]] = []

    def callback(current, total):
        seen.append((current, total))

    out, ratio = optimize_pdf(
        str(pdf_path),
        compress_images=False,
        out_dir=str(tmp_path),
        progress_callback=callback,
    )
    assert (
        out and (tmp_path / out).exists()
        if not out.startswith("/")
        else Path(out).exists()
    )
    assert isinstance(ratio, float)
    # Only one final tick when not compressing images
    assert seen and seen[-1][0] == seen[-1][1] == 1


def test_optimize_with_progress_with_compress(tmp_path):
    pdf_path = tmp_path / "in.pdf"
    _pdf_with_pages(pdf_path, pages=3)
    seen: list[tuple[int, int]] = []

    def callback(current, total):
        seen.append((current, total))

    out, ratio = optimize_pdf(
        str(pdf_path),
        compress_images=True,
        out_dir=str(tmp_path),
        progress_callback=callback,
    )
    assert (
        out and (tmp_path / out).exists()
        if not out.startswith("/")
        else Path(out).exists()
    )
    assert isinstance(ratio, float)
    # Expect at least page_count updates and a final tick
    assert seen and seen[-1][0] == seen[-1][1] == 3
