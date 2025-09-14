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
        if action_obj.fqname == "pdf_toolbox.builtin.optimise.optimise_pdf"
    )
    assert opt_action.category == "PDF"


def test_action_name_formatting():
    actions_list = list_actions()
    image_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.builtin.images.pdf_to_images"
    )
    assert image_action.name == "PDF to Images"


def test_literal_parameters_resolved():
    actions_list = list_actions()
    pdf_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.builtin.images.pdf_to_images"
    )

    pdf_format_ann = next(
        param for param in pdf_action.params if param.name == "image_format"
    ).annotation
    pdf_dpi_ann = next(
        param for param in pdf_action.params if param.name == "dpi"
    ).annotation

    from typing import Literal, get_args, get_origin

    from pdf_toolbox.builtin.images import DPI_PRESETS

    assert get_origin(pdf_format_ann) is Literal
    assert set(get_args(pdf_format_ann)) == {"PNG", "JPEG", "TIFF", "WEBP", "SVG"}
    dpi_args = get_args(pdf_dpi_ann)
    assert int in dpi_args
    literal = next(arg for arg in dpi_args if get_origin(arg) is Literal)
    assert set(get_args(literal)) == set(DPI_PRESETS.keys())


def test_format_name_plural_acronyms():
    assert actions._format_name("pdfs_to_pngs") == "PDFs to PNGs"


def test_register_module_skips_undocumented():
    import types

    mod = types.ModuleType("pdf_toolbox.undoc_mod")
    mod.foo = lambda x: x
    sys.modules["pdf_toolbox.undoc_mod"] = mod
    actions._register_module("pdf_toolbox.undoc_mod")
    assert "pdf_toolbox.undoc_mod.foo" not in actions._registry


def test_auto_discover_populates_registry():
    actions._registry.clear()
    actions._auto_discover.cache_clear()
    actions_list = list_actions()
    assert any(
        action_obj.fqname == "pdf_toolbox.builtin.images.pdf_to_images"
        for action_obj in actions_list
    )


def test_builtin_import_registers_actions():
    """Importing pdf_toolbox.builtin loads actions without discovery."""
    import importlib

    # Ensure builtin modules are re-imported
    saved = {
        name: mod
        for name, mod in sys.modules.items()
        if name.startswith("pdf_toolbox.builtin")
    }
    for name in list(saved):
        sys.modules.pop(name)

    actions._registry.clear()
    actions._auto_discover.cache_clear()

    importlib.import_module("pdf_toolbox.builtin")
    assert any(
        act.fqname == "pdf_toolbox.builtin.images.pdf_to_images"
        for act in actions._registry.values()
    )

    sys.modules.update(saved)
    actions._registry.clear()
    actions._auto_discover.cache_clear()


def test_register_module_ignores_nodoc_functions():
    import types

    mod = types.ModuleType("pdf_toolbox.dummy_mod")

    def func_without_docs():
        pass

    mod.func_without_docs = func_without_docs
    sys.modules["pdf_toolbox.dummy_mod"] = mod
    actions._registry.clear()
    actions._auto_discover.cache_clear()
    actions._register_module("pdf_toolbox.dummy_mod")
    assert not actions._registry
    actions.list_actions()
