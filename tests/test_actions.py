import sys
import typing as t

import pytest

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
        if action_obj.fqname == "pdf_toolbox.actions.unlock.unlock_pdf"
    )
    assert opt_action.category == "PDF"


def test_action_name_formatting():
    actions_list = list_actions()
    image_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.actions.pdf_images.pdf_to_images"
    )
    assert image_action.name == "PDF to Images"


def test_literal_parameters_resolved():
    actions_list = list_actions()
    pdf_action = next(
        action_obj
        for action_obj in actions_list
        if action_obj.fqname == "pdf_toolbox.actions.pdf_images.pdf_to_images"
    )

    pdf_format_ann = next(
        param for param in pdf_action.params if param.name == "image_format"
    ).annotation
    pdf_dpi_ann = next(
        param for param in pdf_action.params if param.name == "dpi"
    ).annotation

    from typing import Literal, get_args, get_origin

    from pdf_toolbox.actions.pdf_images import DPI_PRESETS

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
        action_obj.fqname == "pdf_toolbox.actions.pdf_images.pdf_to_images"
        for action_obj in actions_list
    )


def test_actions_import_registers_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """_register_module() registers decorated actions from stubbed modules."""
    import importlib
    import types

    for name in actions.ACTION_MODULES:
        fullname = f"pdf_toolbox.actions.{name}"
        stub = t.cast(t.Any, types.ModuleType(fullname))
        if name == "pdf_images":

            def fake_action() -> None:
                """Fake action for registry checks."""
                pass

            fake_action.__module__ = fullname
            stub.fake_action = actions.action()(fake_action)
        monkeypatch.setitem(sys.modules, fullname, stub)

    actions._registry.clear()
    actions._auto_discover.cache_clear()
    module = importlib.reload(actions)
    try:
        module._registry.clear()
        module._auto_discover.cache_clear()
        module._register_module("pdf_toolbox.actions.pdf_images")
        assert any(
            act.fqname == "pdf_toolbox.actions.pdf_images.fake_action"
            for act in module._registry.values()
        )
    finally:
        module._registry.clear()
        module._auto_discover.cache_clear()


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


def test_register_module_rejects_untrusted_prefix():
    with pytest.raises(ValueError, match="outside allowed packages"):
        actions._register_module("malicious.mod")


def test_register_module_skips_excluded(monkeypatch):
    called = False

    def fail_import(_name):
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr(actions.importlib, "import_module", fail_import)
    actions._register_module("pdf_toolbox.actions")
    assert not called


def test_auto_discover_suppresses_errors(monkeypatch):
    def boom(_name):
        raise RuntimeError("boom")

    monkeypatch.setattr(actions, "_register_module", boom)
    actions._auto_discover.cache_clear()
    actions._auto_discover()
    actions._auto_discover.cache_clear()
