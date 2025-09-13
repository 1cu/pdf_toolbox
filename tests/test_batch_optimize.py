import fitz  # type: ignore

from pdf_toolbox.optimize import batch_optimize_pdfs


def _make_pdf(path):
    d = fitz.open()
    d.new_page()
    d.save(path)
    d.close()


def test_batch_optimize(tmp_path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    _make_pdf(in_dir / "a.pdf")
    _make_pdf(in_dir / "b.pdf")

    out = batch_optimize_pdfs(str(in_dir))
    # outputs written to default subdir 'optimized'
    assert len(out) == 2
    for p in out:
        assert p.endswith(".pdf")
