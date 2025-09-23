"""Action registration and default action modules."""

from __future__ import annotations

import importlib
import inspect
import typing as t
from contextlib import suppress
from dataclasses import dataclass
from functools import cache
from weakref import WeakKeyDictionary

from pdf_toolbox.i18n import tr


@dataclass
class Param:
    """Metadata for a function parameter."""

    name: str
    kind: str
    annotation: t.Any
    default: t.Any = inspect._empty


@dataclass
class Action:
    """Registered action with metadata."""

    fqname: str
    key: str
    func: t.Callable[..., t.Any]
    params: list[Param]
    help: str
    category: str | None = None
    requires_pptx_renderer: bool = False
    visible: bool = True

    @property
    def name(self) -> str:
        """Return translated action name."""
        translated = tr(self.key)
        return translated if translated != self.key else _format_name(self.key)


@dataclass
class _ActionDefinition:
    """Configuration captured when an action is decorated."""

    name: str | None
    category: str | None
    requires_pptx_renderer: bool
    visible: bool


_registry: dict[str, Action] = {}
if "_definitions" not in globals():
    _definitions: WeakKeyDictionary[t.Callable[..., t.Any], _ActionDefinition]
    _definitions = WeakKeyDictionary()
else:
    _definitions = t.cast(
        WeakKeyDictionary[t.Callable[..., t.Any], _ActionDefinition], _definitions
    )


def _format_name(func_name: str) -> str:
    acronyms = {
        "pdf": "PDF",
        "png": "PNG",
        "jpeg": "JPEG",
        "jpg": "JPG",
        "tiff": "TIFF",
    }
    connectors = {"to", "and", "or", "from"}
    parts: list[str] = []
    for index, token in enumerate(func_name.split("_")):
        low = token.lower()
        if low in acronyms:
            parts.append(acronyms[low])
        elif low.endswith("s") and low[:-1] in acronyms:
            parts.append(acronyms[low[:-1]] + "s")
        elif low in connectors:
            parts.append(low)
        elif index == 0:
            parts.append(low.capitalize())
        else:
            parts.append(low)
    return " ".join(parts)


def _remember_definition(
    fn: t.Callable[..., t.Any],
    *,
    name: str | None,
    category: str | None,
    visible: bool,
    requires_pptx_renderer: bool,
) -> None:
    """Store metadata for *fn* so discovery can rebuild the registry."""
    _definitions[fn] = _ActionDefinition(
        name=name,
        category=category,
        requires_pptx_renderer=requires_pptx_renderer,
        visible=visible,
    )


def action(
    name: str | None = None,
    *,
    category: str | None = None,
    visible: bool = True,
    requires_pptx_renderer: bool = False,
):
    """Register *fn* as an action.

    Only functions decorated with :func:`action` are considered actions. The
    ``visible`` flag controls whether the action is returned by
    :func:`list_actions`.
    """

    def deco(fn: t.Callable[..., t.Any]):
        _remember_definition(
            fn,
            name=name,
            category=category,
            visible=visible,
            requires_pptx_renderer=requires_pptx_renderer,
        )
        act = build_action(
            fn,
            name=name,
            category=category,
            requires_pptx_renderer=requires_pptx_renderer,
            visible=visible,
        )
        _registry[act.fqname] = act
        return fn

    return deco


def _definition_for(
    fn: t.Callable[..., t.Any],
) -> _ActionDefinition | None:
    return _definitions.get(fn)


def build_action(
    fn: t.Callable[..., t.Any],
    name: str | None = None,
    category: str | None = None,
    *,
    requires_pptx_renderer: bool | None = None,
    visible: bool | None = None,
) -> Action:
    sig = inspect.signature(fn)
    hints = t.get_type_hints(fn, include_extras=True)
    params: list[Param] = []
    for param in sig.parameters.values():
        ann = hints.get(param.name, param.annotation)
        params.append(
            Param(
                name=param.name,
                kind=str(param.kind),
                annotation=ann,
                default=param.default,
            )
        )
    definition = _definition_for(fn)
    resolved_name = (
        name if name is not None else definition.name if definition else None
    )
    resolved_category = (
        category
        if category is not None
        else definition.category
        if definition
        else None
    )
    resolved_requires = (
        requires_pptx_renderer
        if requires_pptx_renderer is not None
        else definition.requires_pptx_renderer
        if definition
        else False
    )
    resolved_visible = (
        visible if visible is not None else definition.visible if definition else True
    )
    module_name = fn.__module__
    return Action(
        fqname=f"{module_name}.{fn.__name__}",
        key=resolved_name or fn.__name__,
        func=fn,
        params=params,
        help=(fn.__doc__ or "").strip(),
        category=resolved_category,
        requires_pptx_renderer=resolved_requires,
        visible=resolved_visible,
    )


_EXCLUDE = {
    "pdf_toolbox.actions",
    "pdf_toolbox.gui",
    "pdf_toolbox.utils",
    "pdf_toolbox.__init__",
    "pdf_toolbox.i18n",
    "pdf_toolbox.validation",
}

_ALLOWED_PREFIXES = ("pdf_toolbox.",)


def _register_module(mod_name: str) -> None:
    """Import *mod_name* so that decorated actions register themselves."""
    if not mod_name.startswith(_ALLOWED_PREFIXES):
        msg = f"module outside allowed packages: {mod_name}"
        raise ValueError(msg)
    if mod_name in _EXCLUDE:
        return
    mod = importlib.import_module(mod_name)
    for _, obj in inspect.getmembers(mod, inspect.isfunction):
        if _definition_for(obj) is None:
            continue
        act = build_action(obj)
        _registry.setdefault(act.fqname, act)


ACTION_MODULES = [
    "pptx",
    "extract",
    "pdf_images",
    "miro",
    "unlock",
]


@cache
def _auto_discover() -> None:
    for name in ACTION_MODULES:
        with suppress(Exception):
            _register_module(f"{__name__}.{name}")


def list_actions() -> list[Action]:
    """Return all discovered actions."""
    _auto_discover()
    return [act for act in _registry.values() if act.visible]


for _mod in ACTION_MODULES:
    with suppress(Exception):
        importlib.import_module(f"{__name__}.{_mod}")

__all__ = [
    "Action",
    "Param",
    "action",
    "extract",
    "images",
    "list_actions",
    "miro",
    "pptx",
    "unlock",
]
