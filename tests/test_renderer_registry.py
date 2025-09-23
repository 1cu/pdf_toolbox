import sys
from pathlib import Path
from types import ModuleType

import pytest

from pdf_toolbox.renderers import registry
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer, RenderOptions


class _BaseStub(BasePptxRenderer):
    def to_images(
        self,
        _input_pptx: str,
        options: RenderOptions | None = None,
    ) -> str:
        del options
        return "images"

    def to_pdf(
        self,
        _input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        del output_path, notes, handout, range_spec
        return "pdf"


def _reset_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "_REGISTRY", {})
    monkeypatch.setitem(registry._ENTRY_POINT_STATE, "loaded", True)
    monkeypatch.setattr(registry, "_BUILTIN_MODULES", {})


def test_register_and_available(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    class DemoRenderer(_BaseStub):
        name = "demo"

    registered = registry.register(DemoRenderer)
    assert registered is DemoRenderer
    assert registry.available() == ("demo",)

    selected = registry.select("demo")
    assert isinstance(selected, DemoRenderer)


def test_register_requires_unique_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    class DemoRenderer(_BaseStub):
        name = "demo"

    registry.register(DemoRenderer)

    class OtherRenderer(_BaseStub):
        name = "demo"

    with pytest.raises(ValueError, match="demo"):
        registry.register(OtherRenderer)


def test_register_requires_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    class NamelessRenderer(_BaseStub):
        name = ""

    with pytest.raises(ValueError, match="non-empty"):
        registry.register(NamelessRenderer)


def test_available_renderers_filters_on_can_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)

    class WorkingRenderer(_BaseStub):
        name = "working"

        @classmethod
        def can_handle(cls) -> bool:
            return True

    class DisabledRenderer(_BaseStub):
        name = "disabled"

        @classmethod
        def can_handle(cls) -> bool:
            return False

    registry.register(WorkingRenderer)
    registry.register(DisabledRenderer)

    assert registry.available_renderers() == ["working"]


def test_selection_auto_none_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    class NullRenderer(_BaseStub):
        name = "null"

    class MsRenderer(_BaseStub):
        name = "ms_office"
        available = True

        @classmethod
        def can_handle(cls) -> bool:
            return cls.available

    class HttpRenderer(_BaseStub):
        name = "http_office"
        available = True

        @classmethod
        def can_handle(cls) -> bool:
            return cls.available

    registry.register(NullRenderer)
    registry.register(HttpRenderer)
    registry.register(MsRenderer)

    selected = registry.select("auto")
    assert isinstance(selected, MsRenderer)

    MsRenderer.available = False
    selected = registry.select("auto")
    assert isinstance(selected, HttpRenderer)

    HttpRenderer.available = False
    assert registry.select("auto") is None

    assert registry.select("none") is None
    assert registry.select("http_office") is None

    HttpRenderer.available = True
    http_instance = registry.select("http_office")
    assert isinstance(http_instance, HttpRenderer)


def test_entry_points_registration_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)
    monkeypatch.setattr(registry, "_ENTRY_POINT_STATE", {"loaded": False})

    class ClassRenderer(_BaseStub):
        name = "from_class"

    class InstanceRenderer(_BaseStub):
        name = "from_instance"

    class StringRenderer(_BaseStub):
        name = "from_string"

    class DuplicateRenderer(_BaseStub):
        name = "from_class"

    instance_renderer = InstanceRenderer()
    module_name = "tests.fake_registry_entry_points"
    fake_module = ModuleType(module_name)
    fake_module.__dict__["StringRenderer"] = StringRenderer
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    class FakeEntryPoint:
        def __init__(self, payload: object, name: str) -> None:
            self._payload = payload
            self.name = name

        def load(self) -> object:
            return self._payload

    entries = [
        FakeEntryPoint(ClassRenderer, "class"),
        FakeEntryPoint(DuplicateRenderer, "duplicate"),
        FakeEntryPoint(instance_renderer, "instance"),
        FakeEntryPoint(f"{module_name}:StringRenderer", "string"),
        FakeEntryPoint(f"{module_name}:MissingRenderer", "missing"),
    ]

    class FakeEntryPoints:
        def select(self, *, group: str) -> list[FakeEntryPoint]:
            assert group == registry._ENTRY_POINT_GROUP
            return entries

    monkeypatch.setattr(registry.metadata, "entry_points", lambda: FakeEntryPoints())

    available = registry.available()
    assert available == ("from_class", "from_instance", "from_string")


def test_entry_point_discovery_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)
    monkeypatch.setattr(registry, "_ENTRY_POINT_STATE", {"loaded": False})

    def boom() -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(registry.metadata, "entry_points", boom)

    assert registry.available() == ()


def test_entry_points_legacy_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)
    monkeypatch.setattr(registry, "_ENTRY_POINT_STATE", {"loaded": False})

    class LegacyEntry:
        def __init__(self, name: str, payload: object) -> None:
            self.name = name
            self._payload = payload

        def load(self) -> object:
            return self._payload

    class LegacyRenderer(_BaseStub):
        name = "legacy"

    entries = {registry._ENTRY_POINT_GROUP: [LegacyEntry("legacy", LegacyRenderer)]}
    monkeypatch.setattr(registry.metadata, "entry_points", lambda: entries)

    assert registry.available() == ("legacy",)


def test_entry_point_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)
    monkeypatch.setattr(registry, "_ENTRY_POINT_STATE", {"loaded": False})

    class ExplodingEntry:
        name = "explode"

        def load(self) -> object:
            raise RuntimeError("boom")

    class EntryPoints:
        def select(self, *, group: str) -> list[ExplodingEntry]:
            assert group == registry._ENTRY_POINT_GROUP
            return [ExplodingEntry()]

    monkeypatch.setattr(registry.metadata, "entry_points", lambda: EntryPoints())

    assert registry.available() == ()


def test_entry_point_string_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)
    monkeypatch.setattr(registry, "_ENTRY_POINT_STATE", {"loaded": False})

    class ImportEntry:
        name = "import"

        def load(self) -> str:
            return "pkg.module:Renderer"

    class EntryPoints:
        def select(self, *, group: str) -> list[ImportEntry]:
            assert group == registry._ENTRY_POINT_GROUP
            return [ImportEntry()]

    monkeypatch.setattr(registry.metadata, "entry_points", lambda: EntryPoints())
    monkeypatch.setattr(
        registry.importlib,
        "import_module",
        lambda module_name: (_ for _ in ()).throw(RuntimeError(module_name)),
    )

    assert registry.available() == ()


def test_available_triggers_builtin_import(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    class BuiltinRenderer(_BaseStub):
        name = "builtin"

    module_name = "tests.fake_builtin_renderer"
    fake_module = ModuleType(module_name)
    monkeypatch.setitem(sys.modules, module_name, fake_module)
    imported: dict[str, str] = {}

    def fake_import(name: str) -> ModuleType:
        imported["name"] = name
        registry.register(BuiltinRenderer)
        return fake_module

    monkeypatch.setattr(registry, "_load_entry_points", lambda: None)
    monkeypatch.setattr(registry, "_BUILTIN_MODULES", {"builtin": module_name})
    monkeypatch.setattr(registry.importlib, "import_module", fake_import)

    available = registry.available()
    assert available == ("builtin",)
    assert imported["name"] == module_name
    assert registry.available_renderers() == ["builtin"]


def test_builtin_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)
    monkeypatch.setattr(registry, "_ENTRY_POINT_STATE", {"loaded": False})
    monkeypatch.setattr(registry, "_BUILTIN_MODULES", {"broken": "pkg.broken"})
    monkeypatch.setattr(registry, "_load_entry_points", lambda: None)

    def boom(_module: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(registry.importlib, "import_module", boom)

    assert registry.available() == ()


def test_select_returns_none_for_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)
    assert registry.select("missing") is None


def test_assess_renderer_handles_constructor_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)

    class BrokenRenderer(_BaseStub):
        name = "broken"

        def __init__(self) -> None:
            raise RuntimeError("boom")

    registry.register(BrokenRenderer)
    assert registry.available_renderers() == []


def test_assess_renderer_handles_typeerror_instantiation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)

    class BrokenBoolRenderer(_BaseStub):
        name = "broken_bool"
        can_handle = True

        def __init__(self) -> None:
            raise RuntimeError("boom")

    registry.register(BrokenBoolRenderer)
    assert registry.available_renderers() == []


def test_assess_renderer_handles_non_callable_can_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)

    class BoolRenderer(_BaseStub):
        name = "bool"
        can_handle = True

    registry.register(BoolRenderer)
    assert registry.available_renderers() == ["bool"]


def test_assess_renderer_handles_instance_method_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)

    class NeedsArgRenderer(_BaseStub):
        name = "needs_arg"

        def can_handle(self, flag: str) -> bool:
            return bool(flag)

    registry.register(NeedsArgRenderer)
    assert registry.available_renderers() == []


def test_assess_renderer_handles_can_handle_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)

    class ExplodingRenderer(_BaseStub):
        name = "explode"

        @classmethod
        def can_handle(cls) -> bool:
            raise RuntimeError("boom")

    registry.register(ExplodingRenderer)
    assert registry.available_renderers() == []


def test_ensure_error_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    def fake_choice(cfg: dict[str, object] | None = None) -> str:
        if cfg is None:
            return "auto"
        value = cfg.get("pptx_renderer")
        assert isinstance(value, str)
        return value

    monkeypatch.setattr(registry, "get_pptx_renderer_choice", fake_choice)
    monkeypatch.setattr(registry, "select", lambda _name: None)

    with pytest.raises(registry.RendererSelectionError) as auto_info:
        registry.ensure()
    assert "auto-selection" in str(auto_info.value)

    with pytest.raises(registry.RendererSelectionError) as none_info:
        registry.ensure("none")
    assert "null PPTX renderer" in str(none_info.value)

    class CustomRenderer(_BaseStub):
        name = "custom"

    registry.register(CustomRenderer)

    with pytest.raises(registry.RendererSelectionError) as missing_info:
        registry.ensure("missing")
    message = str(missing_info.value)
    assert "Available providers" in message
    assert "custom" in message


def test_ensure_successful_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_registry(monkeypatch)

    class ReadyRenderer(_BaseStub):
        name = "ready"

    ready_instance = ReadyRenderer()

    def fake_choice(cfg: dict[str, object] | None = None) -> str:
        if cfg is None:
            return "ready"
        value = cfg.get("pptx_renderer")
        assert isinstance(value, str)
        return value

    def fake_select(name: str) -> BasePptxRenderer | None:
        if name == "ready":
            return ready_instance
        return None

    monkeypatch.setattr(registry, "get_pptx_renderer_choice", fake_choice)
    monkeypatch.setattr(registry, "select", fake_select)

    assert registry.ensure() is ready_instance
    assert registry.ensure("ready") is ready_instance


def test_convert_pptx_to_pdf_uses_renderer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _reset_registry(monkeypatch)

    class ConvertingRenderer(_BaseStub):
        name = "convert"

        def to_pdf(
            self,
            input_pptx: str,
            output_path: str | None = None,
            notes: bool = False,
            handout: bool = False,
            range_spec: str | None = None,
        ) -> str:
            del input_pptx, notes, handout, range_spec
            assert output_path is not None
            output = Path(output_path)
            output.write_text("pdf")
            return str(output)

    renderer = ConvertingRenderer()
    monkeypatch.setattr(registry, "ensure", lambda *_args, **_kwargs: renderer)

    input_path = tmp_path / "deck.pptx"
    input_path.write_text("pptx")

    with registry.convert_pptx_to_pdf(str(input_path)) as pdf_path:
        assert Path(pdf_path).exists()
