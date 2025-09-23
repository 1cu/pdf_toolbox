"""Action registration and default action modules."""

from __future__ import annotations

import importlib
import inspect
import typing as t
from contextlib import suppress
from dataclasses import dataclass
from functools import cache
from threading import RLock
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


if "_registry" not in globals():
    _registry: dict[str, Action]
    _registry = {}
else:
    _registry = t.cast(dict[str, Action], _registry)

if "_definitions" not in globals():
    _definitions: dict[str, _ActionDefinition]
    _definitions = {}
else:
    _definitions = t.cast(dict[str, _ActionDefinition], _definitions)

if "_definition_refs" not in globals():
    _definition_refs: WeakKeyDictionary[t.Callable[..., t.Any], _ActionDefinition]
    _definition_refs = WeakKeyDictionary()
else:
    _definition_refs = t.cast(
        WeakKeyDictionary[t.Callable[..., t.Any], _ActionDefinition], _definition_refs
    )

_LOCK: RLock = t.cast(RLock, globals().get("_LOCK") or RLock())


def _definition_key(fn: t.Callable[..., t.Any]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}"


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
    definition = _ActionDefinition(
        name=name,
        category=category,
        requires_pptx_renderer=requires_pptx_renderer,
        visible=visible,
    )
    key = _definition_key(fn)
    with _LOCK:
        _definitions[key] = definition
        _definition_refs[fn] = definition


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
        _register_action(act)
        return fn

    return deco


def _definition_for(
    fn: t.Callable[..., t.Any],
) -> _ActionDefinition | None:
    with _LOCK:
        remembered = _definition_refs.get(fn)
        if remembered is not None:
            return remembered
        key = _definition_key(fn)
        remembered = _definitions.get(key)
        if remembered is not None:
            _definition_refs[fn] = remembered
        return remembered


def _register_action(act: Action, *, replace: bool = True) -> None:
    with _LOCK:
        if not replace and act.fqname in _registry:
            return
        _registry[act.fqname] = act


_T = t.TypeVar("_T")


def _resolve_attr(explicit: _T | None, default: _T) -> _T:
    return explicit if explicit is not None else default


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
    resolved_name = _resolve_attr(name, definition.name if definition else None)
    resolved_category = _resolve_attr(
        category, definition.category if definition else None
    )
    resolved_requires = _resolve_attr(
        requires_pptx_renderer,
        definition.requires_pptx_renderer if definition else False,
    )
    resolved_visible = _resolve_attr(
        visible,
        definition.visible if definition else True,
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
    active_keys: set[str] = set()
    for _, obj in inspect.getmembers(mod, inspect.isfunction):
        if _definition_for(obj) is None:
            continue
        active_keys.add(_definition_key(obj))
        act = build_action(obj)
        _register_action(act, replace=False)
    _prune_module_definitions(mod_name, active_keys)


def _prune_module_definitions(module: str, active_keys: set[str]) -> None:
    prefix = f"{module}."
    with _LOCK:
        stale = [
            key
            for key in _definitions
            if key.startswith(prefix) and key not in active_keys
        ]
        for key in stale:
            _definitions.pop(key, None)


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
    with _LOCK:
        return [act for act in _registry.values() if act.visible]


def __getattr__(name: str) -> t.Any:
    if name in ACTION_MODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    if name == "images":
        module = importlib.import_module(f"{__name__}.pdf_images")
        globals()["pdf_images"] = module
        globals()["images"] = module
        return module
    raise AttributeError(name)


__all__ = [
    "Action",
    "Param",
    "action",
    "extract",
    "list_actions",
    "miro",
    "pdf_images",
    "pptx",
    "unlock",
]
