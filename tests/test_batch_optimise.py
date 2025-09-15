from threading import Event, Thread

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-
import pytest

from pdf_toolbox.actions.optimise import batch_optimise_pdfs


def _make_pdf(path):
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    with path.open("ab") as fh:
        fh.write(b"% pad" + b"0" * 1000)


def test_batch_optimise(tmp_path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    _make_pdf(in_dir / "a.pdf")
    _make_pdf(in_dir / "b.pdf")

    outputs = batch_optimise_pdfs(str(in_dir))
    # outputs written to default subdir 'optimised'
    assert len(outputs) == 2
    for out_path in outputs:
        assert out_path.endswith(".pdf")


def test_batch_optimise_forwards_cancel(tmp_path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    _make_pdf(in_dir / "a.pdf")
    cancel = Event()

    def trigger_cancel():
        cancel.set()

    timer = Thread(target=trigger_cancel)
    timer.start()
    with pytest.raises(RuntimeError):
        batch_optimise_pdfs(str(in_dir), cancel=cancel)
    timer.join()
