from pathlib import Path

import fitz  # type: ignore

from pdf_toolbox.optimize import optimize_pdf


def _pdf_with_pages(path, pages=2):
    d = fitz.open()
    for i in range(pages):
        p = d.new_page()
        p.insert_text((72, 72), f"Page {i + 1}")
    d.save(path)
    d.close()


def test_optimize_with_progress_no_compress(tmp_path):
    pdf = tmp_path / "in.pdf"
    _pdf_with_pages(pdf, pages=2)
    seen: list[tuple[int, int]] = []

    def cb(c, t):
        seen.append((c, t))

    out, ratio = optimize_pdf(
        str(pdf), compress_images=False, out_dir=str(tmp_path), progress_callback=cb
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
    pdf = tmp_path / "in.pdf"
    _pdf_with_pages(pdf, pages=3)
    seen: list[tuple[int, int]] = []

    def cb(c, t):
        seen.append((c, t))

    out, ratio = optimize_pdf(
        str(pdf), compress_images=True, out_dir=str(tmp_path), progress_callback=cb
    )
    assert (
        out and (tmp_path / out).exists()
        if not out.startswith("/")
        else Path(out).exists()
    )
    assert isinstance(ratio, float)
    # Expect at least page_count updates and a final tick
    assert seen and seen[-1][0] == seen[-1][1] == 3
