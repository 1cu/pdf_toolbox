import sys

from pdf_toolbox import actions
from pdf_toolbox.actions import list_actions


def test_registry_filters_internal_functions():
    actions_list = list_actions()
    fqnames = {action_obj.fqname for action_obj in actions_list}
    assert "pdf_toolbox.actions.list_actions" not in fqnames
    assert "pdf_toolbox.gui.load_config" not in fqnames


def test_decorator_preserves_category():
    actions_list = list_actions()
    opt_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.optimize.optimize_pdf"
    )
    assert opt_action.category == "PDF"


def test_action_name_formatting():
    actions_list = list_actions()
    image_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.images.pdf_to_images"
    )
    assert image_action.name == "PDF to Images"


def test_literal_parameters_resolved():
    actions_list = list_actions()
    pdf_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.images.pdf_to_images"
    )

    pdf_format_ann = next(
        param for param in pdf_action.params if param.name == "image_format"
    ).annotation
    pdf_dpi_ann = next(
        param for param in pdf_action.params if param.name == "dpi"
    ).annotation

    from typing import Literal, get_args, get_origin

    from pdf_toolbox.images import DPI_PRESETS

    assert get_origin(pdf_format_ann) is Literal
    assert set(get_args(pdf_format_ann)) == {"PNG", "JPEG", "TIFF", "WEBP", "SVG"}
    dpi_args = get_args(pdf_dpi_ann)
    assert int in dpi_args
    literal = next(arg for arg in dpi_args if get_origin(arg) is Literal)
    assert set(get_args(literal)) == set(DPI_PRESETS.keys())


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
    assert any(
        action_obj.fqname == "pdf_toolbox.images.pdf_to_images"
        for action_obj in actions_list
    )


def test_auto_discover_loader_toc(monkeypatch):
    """Discovery works when package loader exposes a ``toc`` attribute."""
    import importlib.resources as ir
    import types

    pkg = sys.modules["pdf_toolbox.builtin"]
    original_loader = pkg.__spec__.loader
    monkeypatch.setattr(actions.pkgutil, "walk_packages", lambda *_, **__: [])
    monkeypatch.setattr(
        ir, "files", lambda *_, **__: (_ for _ in ()).throw(FileNotFoundError)
    )
    pkg.__spec__.loader = types.SimpleNamespace(toc=["pdf_toolbox.builtin.images"])
    saved = {
        name: mod
        for name, mod in sys.modules.items()
        if name.startswith("pdf_toolbox.builtin.")
    }
    for name in saved:
        sys.modules.pop(name)
    actions._registry.clear()
    actions._discovered = False
    try:
        actions.list_actions()
        assert any(
            action_obj.fqname == "pdf_toolbox.images.pdf_to_images"
            for action_obj in actions._registry.values()
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
    actions.list_actions()
