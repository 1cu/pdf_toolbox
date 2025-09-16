"""Action registration and default action modules."""

from __future__ import annotations

import importlib
import inspect
import typing as t
from contextlib import suppress
from dataclasses import dataclass
from functools import cache

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
    func: t.Callable
    params: list[Param]
    help: str
    category: str | None = None

    @property
    def name(self) -> str:
        """Return translated action name."""
        translated = tr(self.key)
        return translated if translated != self.key else _format_name(self.key)


_registry: dict[str, Action] = {}


def _format_name(func_name: str) -> str:
    acronyms = {
        "pdf": "PDF",
        "docx": "DOCX",
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


def action(
    name: str | None = None,
    *,
    category: str | None = None,
    visible: bool = True,
):
    """Register *fn* as an action.

    Only functions decorated with :func:`action` are considered actions. The
    ``visible`` flag controls whether the action is returned by
    :func:`list_actions`.
    """

    def deco(fn):
        act = build_action(fn, name=name, category=category)
        fn.__pdf_toolbox_action__ = visible  # type: ignore[attr-defined]  # pdf-toolbox: attach custom attribute for action registration | issue:-
        _registry[act.fqname] = act
        return fn

    return deco


def build_action(fn, name: str | None = None, category: str | None = None) -> Action:
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
    module_name = fn.__module__
    return Action(
        fqname=f"{module_name}.{fn.__name__}",
        key=name or fn.__name__,
        func=fn,
        params=params,
        help=(fn.__doc__ or "").strip(),
        category=category,
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
        if getattr(obj, "__pdf_toolbox_action__", False):
            act = build_action(obj)
            _registry.setdefault(act.fqname, act)


ACTION_MODULES = [
    "docx",
    "pptx",
    "extract",
    "pdf_images",
    "miro",
    "optimise",
    "repair",
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
    return [
        act
        for act in _registry.values()
        if getattr(act.func, "__pdf_toolbox_action__", False)
    ]


for _mod in ACTION_MODULES:
    with suppress(Exception):
        importlib.import_module(f"{__name__}.{_mod}")

__all__ = [
    "Action",
    "Param",
    "action",
    "docx",
    "extract",
    "images",
    "list_actions",
    "miro",
    "optimise",
    "pptx",
    "repair",
    "unlock",
]
