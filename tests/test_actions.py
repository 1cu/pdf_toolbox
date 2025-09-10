import sys

import pdf_toolbox.actions as actions
from pdf_toolbox.actions import list_actions


def test_registry_filters_internal_functions():
    actions_list = list_actions()
    fqnames = {a.fqname for a in actions_list}
    assert "pdf_toolbox.actions.list_actions" not in fqnames
    assert "pdf_toolbox.gui.load_config" not in fqnames


def test_decorator_preserves_category():
    actions_list = list_actions()
    opt = next(
        a for a in actions_list if a.fqname == "pdf_toolbox.optimize.optimize_pdf"
    )
    assert opt.category == "PDF"


def test_action_name_formatting():
    actions_list = list_actions()
    img = next(
        a for a in actions_list if a.fqname == "pdf_toolbox.rasterize.pdf_to_images"
    )
    assert img.name == "PDF to images"


def test_literal_parameters_resolved():
    actions_list = list_actions()
    pdf_act = next(
        a for a in actions_list if a.fqname == "pdf_toolbox.rasterize.pdf_to_images"
    )

    pdf_fmt = next(p for p in pdf_act.params if p.name == "image_format").annotation
    pdf_dpi = next(p for p in pdf_act.params if p.name == "dpi").annotation

    from typing import Literal, get_args, get_origin
    from pdf_toolbox.rasterize import DPI_PRESETS

    assert get_origin(pdf_fmt) is Literal
    assert set(get_args(pdf_fmt)) == {"PNG", "JPEG", "TIFF"}
    dpi_args = get_args(pdf_dpi)
    assert int in dpi_args
    lit = next(a for a in dpi_args if get_origin(a) is Literal)
    assert set(get_args(lit)) == set(DPI_PRESETS.keys())

    if sys.platform == "win32":
        pptx_act = next(
            a
            for a in actions_list
            if a.fqname == "pdf_toolbox.pptx.pptx_to_images_via_powerpoint"
        )
        pptx_fmt = next(
            p for p in pptx_act.params if p.name == "image_format"
        ).annotation
        assert get_origin(pptx_fmt) is Literal
        assert set(get_args(pptx_fmt)) == {"PNG", "JPEG", "TIFF"}
    else:
        assert not any(
            a.fqname == "pdf_toolbox.pptx.pptx_to_images_via_powerpoint"
            for a in actions_list
        )


def test_format_name_plural_acronyms():
    assert actions._format_name("pdfs_to_pngs") == "PDFs to PNGs"


def test_auto_discover_populates_registry():
    from pdf_toolbox import rasterize

    had_attr = getattr(rasterize.pdf_to_images, "__pdf_toolbox_action__", None)
    if had_attr is not None:
        delattr(rasterize.pdf_to_images, "__pdf_toolbox_action__")
    actions._registry.clear()
    actions_list = list_actions()
    if had_attr is not None:
        setattr(rasterize.pdf_to_images, "__pdf_toolbox_action__", had_attr)
    assert any(a.fqname == "pdf_toolbox.rasterize.pdf_to_images" for a in actions_list)
