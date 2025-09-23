"""End-to-end coverage for PPTX actions."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-

from pdf_toolbox.actions import pptx as pptx_actions
from pdf_toolbox.actions.pptx import pptx_to_images, pptx_to_pdf
from pdf_toolbox.renderers.pptx import BasePptxRenderer
from pdf_toolbox.utils import parse_page_spec


def test_pptx_to_images_e2e(
    monkeypatch,
    simple_pptx: str,
    sample_pdf: str,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "images"

    @contextmanager
    def fake_convert(input_pptx: str):
        assert Path(input_pptx).exists()
        yield sample_pdf

    monkeypatch.setattr(pptx_actions, "convert_pptx_to_pdf", fake_convert)

    result_dir = pptx_to_images(
        simple_pptx,
        out_dir=str(output_dir),
        image_format="PNG",
    )

    assert Path(result_dir) == output_dir
    generated = sorted(output_dir.glob("*.png"))
    assert len(generated) == 3
    for image_path in generated:
        assert image_path.is_file()
        assert image_path.stat().st_size > 0


def test_pptx_to_pdf_e2e(
    monkeypatch,
    simple_pptx: str,
    sample_pdf: str,
    tmp_path: Path,
) -> None:
    class DummyRenderer(BasePptxRenderer):
        name = "dummy"

        def to_images(  # noqa: PLR0913  # pdf-toolbox: renderer API requires many parameters | issue:-
            self,
            _input_pptx: str,
            out_dir: str | None = None,
            max_size_mb: float | None = None,
            image_format: str = "JPEG",
            quality: int | None = None,
            width: int | None = None,
            height: int | None = None,
            range_spec: str | None = None,
        ) -> str:
            del (
                out_dir,
                max_size_mb,
                image_format,
                quality,
                width,
                height,
                range_spec,
            )
            raise NotImplementedError

        def to_pdf(
            self,
            _input_pptx: str,
            output_path: str | None = None,
            notes: bool = False,
            handout: bool = False,
            range_spec: str | None = None,
        ) -> str:
            del notes, handout
            target = Path(output_path) if output_path else tmp_path / "auto.pdf"
            with fitz.open(sample_pdf) as source:
                selected = (
                    parse_page_spec(range_spec, source.page_count)
                    if range_spec
                    else list(range(1, source.page_count + 1))
                )
                result_doc = fitz.open()
                for page_no in selected:
                    result_doc.insert_pdf(
                        source,
                        from_page=page_no - 1,
                        to_page=page_no - 1,
                    )
                result_doc.save(target)
                result_doc.close()
            return str(target)

    monkeypatch.setattr(pptx_actions, "require_pptx_renderer", lambda: DummyRenderer())

    explicit_path = tmp_path / "slides.pdf"
    result_path = Path(
        pptx_to_pdf(simple_pptx, output_path=str(explicit_path), pages="2-3")
    )
    assert result_path == explicit_path
    with fitz.open(result_path) as doc:
        assert doc.page_count == 2

    auto_result = Path(pptx_to_pdf(simple_pptx, pages="1"))
    assert auto_result.exists()
    with fitz.open(auto_result) as doc:
        assert doc.page_count == 1
