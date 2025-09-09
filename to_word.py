from __future__ import annotations

import argparse
import io
from pathlib import Path

import fitz  # type: ignore
from PIL import Image
from docx import Document

from common_utils import sane_output_dir


def pdf_to_docx(input_pdf: str, out_dir: str | None = None) -> str:
    pdf = fitz.open(input_pdf)
    docx_doc = Document()
    for page in pdf:
        text = page.get_text()
        if text:
            docx_doc.add_paragraph(text)
        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(pdf, xref)
            if pix.n > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            buf.seek(0)
            docx_doc.add_picture(buf)
    out_path = sane_output_dir(input_pdf, out_dir) / f"{Path(input_pdf).stem}.docx"
    docx_doc.save(out_path)
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to Word")
    parser.add_argument("input_pdf")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    pdf_to_docx(args.input_pdf, args.out_dir)
