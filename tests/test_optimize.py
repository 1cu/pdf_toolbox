import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from pdf_toolbox.optimize import optimize_pdf


def test_optimize_pdf(tmp_path):
    sample = Path(__file__).parent / "fixtures" / "sample.pdf"
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(sample.read_bytes())
    out, reduction = optimize_pdf(str(pdf_path), quality="screen", out_dir=str(tmp_path))
    assert out is not None
    out_path = Path(out)
    assert out_path.exists()
    assert reduction <= 1
