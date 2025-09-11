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
_discovered = False


def _format_name(func_name: str) -> str:
    acronyms = {
        "pdf": "PDF",
        "docx": "DOCX",
        "pptx": "PPTX",
        "png": "PNG",
        "jpeg": "JPEG",
        "jpg": "JPG",
        "tiff": "TIFF",
    }
    connectors = {"to", "and", "or", "from"}
    parts: list[str] = []
    for i, tok in enumerate(func_name.split("_")):
        low = tok.lower()
        if low in acronyms:
            parts.append(acronyms[low])
        elif low.endswith("s") and low[:-1] in acronyms:
            parts.append(acronyms[low[:-1]] + "s")
        elif low in connectors:
            parts.append(low)
        elif i == 0:
            parts.append(low.capitalize())
        else:
            parts.append(low)
    return " ".join(parts)


def action(name: str | None = None, category: str | None = None):
    def deco(fn):
        act = build_action(fn, name=name, category=category)
        fn.__pdf_toolbox_action__ = True  # type: ignore[attr-defined]
        _registry[act.fqname] = act
        return fn

    return deco


def build_action(fn, name: str | None = None, category: str | None = None) -> Action:
    sig = inspect.signature(fn)
    hints = t.get_type_hints(fn, include_extras=True)
    params: list[Param] = []
    for p in sig.parameters.values():
        ann = hints.get(p.name, p.annotation)
        params.append(
            Param(
                name=p.name,
                kind=str(p.kind),
                annotation=ann,
                default=p.default,
            )
        )
    return Action(
        fqname=f"{fn.__module__}.{fn.__name__}",
        name=name or _format_name(fn.__name__),
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


def _register_module(mod_name: str) -> None:
    """Import *mod_name* and register its actions."""
    if mod_name in _EXCLUDE:
        return
    mod = importlib.import_module(mod_name)
    for _, obj in inspect.getmembers(mod, inspect.isfunction):
        if obj.__module__ != mod_name:
            continue
        if obj.__name__.startswith("_"):
            continue
        if getattr(obj, "__pdf_toolbox_action__", False):
            continue
        if not any([obj.__doc__, obj.__annotations__]):
            continue
        act = build_action(obj)
        _registry.setdefault(act.fqname, act)


def _auto_discover(pkg: str = "pdf_toolbox") -> None:
    global _discovered
    if _discovered:
        return
    pkg_mod = importlib.import_module(pkg)
    paths = getattr(pkg_mod, "__path__", [])
    found = False
    for modinfo in pkgutil.walk_packages(paths, pkg_mod.__name__ + "."):
        found = True
        _register_module(modinfo.name)
    if not found:
        try:
            from importlib import resources

            for res in resources.files(pkg_mod).iterdir():
                if res.name.endswith(".py") and res.name != "__init__.py":
                    _register_module(f"{pkg_mod.__name__}.{res.name[:-3]}")
        except Exception:
            pass
    _discovered = True


def list_actions() -> list[Action]:
    _auto_discover()
    return list(_registry.values())


__all__ = ["Param", "Action", "action", "list_actions"]
