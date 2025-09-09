import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from pdf_toolbox.rasterize import pdf_to_images


def test_pdf_to_images(tmp_path):
    sample = Path(__file__).parent / "fixtures" / "sample.pdf"
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(sample.read_bytes())
    outputs = pdf_to_images(str(pdf_path), dpi=72, out_dir=str(tmp_path))
    assert len(outputs) == 1
    assert Path(outputs[0]).exists()
