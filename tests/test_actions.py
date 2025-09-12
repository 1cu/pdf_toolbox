import sys

from pdf_toolbox import actions
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
        a for a in actions_list if a.fqname == "pdf_toolbox.images.pdf_to_images"
    )
    assert img.name == "PDF to images"


def test_literal_parameters_resolved():
    actions_list = list_actions()
    pdf_act = next(
        a for a in actions_list if a.fqname == "pdf_toolbox.images.pdf_to_images"
    )

    pdf_fmt = next(p for p in pdf_act.params if p.name == "image_format").annotation
    pdf_dpi = next(p for p in pdf_act.params if p.name == "dpi").annotation

    from typing import Literal, get_args, get_origin

    from pdf_toolbox.images import DPI_PRESETS

    assert get_origin(pdf_fmt) is Literal
    assert set(get_args(pdf_fmt)) == {"PNG", "JPEG", "TIFF", "WEBP", "SVG"}
    dpi_args = get_args(pdf_dpi)
    assert int in dpi_args
    lit = next(a for a in dpi_args if get_origin(a) is Literal)
    assert set(get_args(lit)) == set(DPI_PRESETS.keys())


def test_format_name_plural_acronyms():
    assert actions._format_name("pdfs_to_pngs") == "PDFs to PNGs"


def test_register_module_skips_undocumented(tmp_path, monkeypatch):
    mod_path = tmp_path / "undoc_mod.py"
    mod_path.write_text("def foo(x):\n    return x\n")
    monkeypatch.syspath_prepend(tmp_path)
    actions._register_module("undoc_mod")
    assert "undoc_mod.foo" not in actions._registry


def test_auto_discover_populates_registry():
    from pdf_toolbox import images

    had_attr = getattr(images.pdf_to_images, "__pdf_toolbox_action__", None)
    if had_attr is not None:
        delattr(images.pdf_to_images, "__pdf_toolbox_action__")
    actions._registry.clear()
    actions._discovered = False
    actions_list = list_actions()
    if had_attr is not None:
        images.pdf_to_images.__pdf_toolbox_action__ = had_attr
    assert any(a.fqname == "pdf_toolbox.images.pdf_to_images" for a in actions_list)


def test_auto_discover_loader_toc(monkeypatch):
    """Discovery works when package loader exposes a ``toc`` attribute."""
    import importlib.resources as ir
    import types

    pkg = sys.modules["pdf_toolbox"]
    original_loader = pkg.__spec__.loader
    monkeypatch.setattr(actions.pkgutil, "walk_packages", lambda *_, **__: [])
    monkeypatch.setattr(
        ir, "files", lambda *_, **__: (_ for _ in ()).throw(FileNotFoundError)
    )
    pkg.__spec__.loader = types.SimpleNamespace(toc=["pdf_toolbox.images"])
    saved = {
        name: mod
        for name, mod in sys.modules.items()
        if name.startswith("pdf_toolbox.")
        and name not in {"pdf_toolbox.actions", "pdf_toolbox.utils"}
    }
    for name in saved:
        sys.modules.pop(name)
    actions._registry.clear()
    actions._discovered = False
    try:
        actions.list_actions()
        assert any(
            a.fqname == "pdf_toolbox.images.pdf_to_images"
            for a in actions._registry.values()
        )
    finally:
        pkg.__spec__.loader = original_loader
        sys.modules.update(saved)
        actions._registry.clear()
        actions._discovered = False


def test_register_module_ignores_nodoc_functions(monkeypatch):
    import types

    mod = types.ModuleType("dummy_mod")

    def func_without_docs():
        pass

    mod.func_without_docs = func_without_docs
    sys.modules["dummy_mod"] = mod
    actions._registry.clear()
    actions._discovered = False
    actions._register_module("dummy_mod")
    assert not actions._registry
