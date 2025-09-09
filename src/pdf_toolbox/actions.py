from __future__ import annotations

import inspect
import importlib
import pkgutil
import typing as t
from dataclasses import dataclass


@dataclass
class Param:
    name: str
    kind: str
    annotation: t.Any
    default: t.Any = inspect._empty


@dataclass
class Action:
    fqname: str
    name: str
    func: t.Callable
    params: list[Param]
    help: str
    category: str | None = None


_registry: dict[str, Action] = {}


def action(name: str | None = None, category: str | None = None):
    def deco(fn):
        act = build_action(fn, name=name, category=category)
        fn.__pdf_toolbox_action__ = True  # type: ignore[attr-defined]
        _registry[act.fqname] = act
        return fn

    return deco


def build_action(fn, name: str | None = None, category: str | None = None) -> Action:
    sig = inspect.signature(fn)
    params: list[Param] = []
    for p in sig.parameters.values():
        params.append(
            Param(
                name=p.name,
                kind=str(p.kind),
                annotation=p.annotation,
                default=p.default,
            )
        )
    return Action(
        fqname=f"{fn.__module__}.{fn.__name__}",
        name=name or fn.__name__.replace("_", " ").title(),
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
}


def _auto_discover(pkg: str = "pdf_toolbox") -> None:
    pkg_mod = importlib.import_module(pkg)
    for modinfo in pkgutil.walk_packages(pkg_mod.__path__, pkg_mod.__name__ + "."):
        if modinfo.name in _EXCLUDE:
            continue
        mod = importlib.import_module(modinfo.name)
        for _, obj in inspect.getmembers(mod, inspect.isfunction):
            if obj.__module__ != modinfo.name:
                continue
            if obj.__name__.startswith("_"):
                continue
            if getattr(obj, "__pdf_toolbox_action__", False):
                continue
            if not any([obj.__doc__, obj.__annotations__]):
                continue
            act = build_action(obj)
            _registry.setdefault(act.fqname, act)


def list_actions() -> list[Action]:
    if not _registry:
        _auto_discover()
    return list(_registry.values())


__all__ = ["Param", "Action", "action", "list_actions"]
