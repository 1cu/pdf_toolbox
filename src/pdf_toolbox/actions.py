"""Action registration and discovery utilities."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import typing as t
from contextlib import suppress
from dataclasses import dataclass

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
_discovered = False


def _format_name(func_name: str) -> str:  # pragma: no cover - trivial
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


def action(name: str | None = None, category: str | None = None):
    """Register a function as an action."""

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
    if module_name.startswith("pdf_toolbox.builtin."):
        module_name = "pdf_toolbox." + module_name.split(".", 2)[2]
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


def _register_module(mod_name: str) -> None:
    """Import *mod_name* and register its actions."""
    if mod_name in _EXCLUDE:  # pragma: no cover - defensive
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


def _auto_discover(pkg: str = "pdf_toolbox.builtin") -> None:
    global _discovered  # noqa: PLW0603
    if _discovered:
        return
    pkg_mod = importlib.import_module(pkg)
    paths = getattr(pkg_mod, "__path__", [])
    found = False
    for modinfo in pkgutil.walk_packages(paths, pkg_mod.__name__ + "."):
        found = True
        _register_module(modinfo.name)
    if not found:  # pragma: no cover - fallback for limited environments
        with suppress(Exception):
            from importlib import resources  # noqa: PLC0415

            for res in resources.files(pkg_mod).iterdir():
                if res.name.endswith(".py") and res.name != "__init__.py":
                    _register_module(f"{pkg_mod.__name__}.{res.name[:-3]}")
    if not _registry:  # pragma: no cover - PyInstaller one-file builds
        # In some bundled environments (e.g., PyInstaller one-file builds),
        # neither ``pkgutil.walk_packages`` nor ``importlib.resources`` can
        # enumerate package modules.  If the package's loader exposes a table
        # of contents (PyInstaller's ``toc`` attribute), use it to discover
        # available modules.
        toc = getattr(getattr(pkg_mod.__spec__, "loader", None), "toc", [])
        for mod_name in toc:
            if mod_name.startswith(pkg_mod.__name__ + "."):
                with suppress(Exception):
                    _register_module(mod_name)
    if not _registry:  # pragma: no cover - explicit __all__ fallback
        for name in getattr(pkg_mod, "__all__", []):
            with suppress(Exception):
                _register_module(f"{pkg_mod.__name__}.{name}")
    _discovered = True


def list_actions() -> list[Action]:
    """Return all discovered actions."""
    _auto_discover()
    return list(_registry.values())


__all__ = ["Action", "Param", "action", "list_actions"]
