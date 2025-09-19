"""Runtime registry for PPTX rendering providers."""

from __future__ import annotations

import importlib
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from importlib import metadata
from pathlib import Path
from typing import Any, cast

from pdf_toolbox.config import PptxRendererChoice, get_pptx_renderer_choice
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.utils import logger

_REGISTRY: dict[str, type[BasePptxRenderer]] = {}
_ENTRY_POINT_STATE = {"loaded": False}
_ENTRY_POINT_GROUP = "pdf_toolbox.pptx_renderers"
_AUTO_PRIORITY = ("ms_office", "http_office")
_BUILTIN_MODULES = {
    "lightweight": "pdf_toolbox.renderers.lightweight_stub",
    "http_office": "pdf_toolbox.renderers.http_office",
    "ms_office": "pdf_toolbox.renderers.ms_office",
}

type EntryPointIterable = Iterable[metadata.EntryPoint]


class RendererSelectionError(LookupError):
    """Raised when selecting a PPTX renderer fails."""


def register(renderer_cls: type[BasePptxRenderer]) -> type[BasePptxRenderer]:
    """Register ``renderer_cls`` under its ``name`` attribute."""
    name = getattr(renderer_cls, "name", "")
    if not isinstance(name, str) or not name.strip():
        msg = (
            f"Renderer class {renderer_cls.__name__} must define a non-empty 'name'"
            " attribute."
        )
        raise ValueError(msg)

    key = name.strip().lower()
    existing = _REGISTRY.get(key)
    if existing is not None and existing is not renderer_cls:
        msg = (
            f"Renderer '{name}' is already registered with {existing.__module__}."
            f"{existing.__name__}"
        )
        raise ValueError(msg)

    _REGISTRY[key] = renderer_cls
    return renderer_cls


def available() -> tuple[str, ...]:
    """Return registered renderer names in registration order."""
    _load_entry_points()
    for name in _BUILTIN_MODULES:
        _ensure_builtin_registered(name)
    return tuple(_REGISTRY.keys())


def available_renderers() -> list[str]:
    """Return renderer names that can handle conversions right now."""
    _load_entry_points()
    for name in _BUILTIN_MODULES:
        _ensure_builtin_registered(name)

    names: list[str] = []
    for key, renderer_cls in _REGISTRY.items():
        _instance, can_handle = _assess_renderer(renderer_cls)
        if can_handle:
            names.append(key)
    return names


def _load_entry_points() -> None:  # noqa: PLR0912  # pdf-toolbox: handles diverse entry point backends and failure modes | issue:-
    """Load PPTX renderer entry points once."""
    if _ENTRY_POINT_STATE["loaded"]:
        return
    _ENTRY_POINT_STATE["loaded"] = True

    try:
        entry_points = metadata.entry_points()
    except Exception as exc:  # pragma: no cover  # pdf-toolbox: entry point discovery may fail when metadata backend is absent | issue:-
        logger.debug("pptx renderer entry point discovery failed: %s", exc)
        return

    if hasattr(entry_points, "select"):
        group = cast(
            EntryPointIterable,
            entry_points.select(group=_ENTRY_POINT_GROUP),
        )
    else:  # pragma: no cover  # pdf-toolbox: compatibility shim for older importlib.metadata implementations | issue:-
        legacy_points = cast(Mapping[str, EntryPointIterable], entry_points)
        group = legacy_points.get(_ENTRY_POINT_GROUP, ())

    for entry in group:
        try:
            loaded = entry.load()
        except Exception as exc:  # pragma: no cover  # pdf-toolbox: plugin entry point import may fail due to third-party issues | issue:-
            logger.warning(
                "pptx renderer entry point '%s' failed to load: %s",
                getattr(entry, "name", "<unknown>"),
                exc,
            )
            continue

        renderer_cls: type[BasePptxRenderer] | None = None
        if isinstance(loaded, type) and issubclass(loaded, BasePptxRenderer):
            renderer_cls = loaded
        elif isinstance(loaded, BasePptxRenderer):
            renderer_cls = loaded.__class__
        elif isinstance(loaded, str):
            module_name, _, attr = loaded.partition(":")
            if module_name:
                try:
                    module = importlib.import_module(module_name)
                except Exception as exc:  # pragma: no cover  # pdf-toolbox: entry point may reference unavailable module | issue:-
                    logger.warning(
                        "pptx renderer entry point '%s' could not import %s: %s",
                        getattr(entry, "name", "<unknown>"),
                        module_name,
                        exc,
                    )
                    continue
                renderer_cls = getattr(module, attr or "", None)
                if not isinstance(renderer_cls, type) or not issubclass(
                    renderer_cls,
                    BasePptxRenderer,
                ):
                    renderer_cls = None

        if renderer_cls is None:
            logger.warning(
                "pptx renderer entry point '%s' did not expose a renderer class",
                getattr(entry, "name", "<unknown>"),
            )
            continue
        try:
            register(renderer_cls)
        except ValueError as exc:
            logger.debug("pptx renderer registration skipped: %s", exc)


def _ensure_builtin_registered(name: str) -> None:
    """Import built-in renderers on demand."""
    key = name.strip().lower()
    if not key or key in _REGISTRY:
        return
    module_name = _BUILTIN_MODULES.get(key)
    if not module_name:
        return
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover  # pdf-toolbox: builtin providers may be unavailable on this platform | issue:-
        logger.debug("pptx renderer '%s' import failed: %s", key, exc)


def _selection_error(choice: PptxRendererChoice) -> RendererSelectionError:
    """Create an informative error for missing renderers."""
    available = [name for name in _REGISTRY if name != "null"]
    if choice == "auto":
        detail = "No PPTX renderer satisfied auto-selection."
    elif choice == "none":
        detail = "The null PPTX renderer is not registered."
    else:
        detail = f"No PPTX renderer named '{choice}'."
    if available:
        readable = ", ".join(sorted(available))
        detail += f" Available providers: {readable}."
    else:
        detail += " No providers are registered."
    return RendererSelectionError(detail)


def _assess_renderer(  # noqa: PLR0911  # pdf-toolbox: evaluation flow returns early for availability outcomes | issue:-
    renderer_cls: type[BasePptxRenderer],
) -> tuple[BasePptxRenderer | None, bool]:
    """Return an instance and whether ``renderer_cls`` can handle rendering."""
    instance: BasePptxRenderer | None = None

    def _get_instance() -> BasePptxRenderer | None:
        nonlocal instance
        if instance is not None:
            return instance
        try:
            instance = renderer_cls()
        except Exception as exc:
            logger.info(
                "pptx renderer %s failed to initialise: %s",
                getattr(renderer_cls, "name", renderer_cls.__name__),
                exc,
            )
            return None
        return instance

    can_handle: Any | None = getattr(renderer_cls, "can_handle", None)
    if can_handle is None:
        inst = _get_instance()
        return inst, inst is not None

    try:
        available = bool(can_handle())
    except TypeError:
        inst = _get_instance()
        if inst is None:
            return None, False
        method = getattr(inst, "can_handle", None)
        if not callable(method):
            return inst, True
        try:
            return inst, bool(method())
        except Exception as exc:
            logger.info(
                "pptx renderer %s.can_handle() failed: %s",
                getattr(renderer_cls, "name", renderer_cls.__name__),
                exc,
            )
            return None, False
    except Exception as exc:
        logger.info(
            "pptx renderer %s.can_handle() failed: %s",
            getattr(renderer_cls, "name", renderer_cls.__name__),
            exc,
        )
        return None, False
    else:
        if not available:
            return None, False
        inst = _get_instance()
        return inst, inst is not None


def _resolve_renderer(name: str) -> BasePptxRenderer | None:
    """Return an instantiated renderer for ``name`` when available."""
    renderer_cls = _REGISTRY.get(name)
    if renderer_cls is None:
        return None
    instance, available = _assess_renderer(renderer_cls)
    if not available:
        return None
    return instance


def select(name: str) -> BasePptxRenderer | None:
    """Return an instantiated renderer for ``name`` or ``None`` when missing."""
    lookup = (name or "").strip().lower()
    if not lookup or lookup == "none":
        return None

    _load_entry_points()

    if lookup == "auto":
        for candidate in _AUTO_PRIORITY:
            _ensure_builtin_registered(candidate)
            renderer = _resolve_renderer(candidate)
            if renderer is not None:
                return renderer
        return None

    _ensure_builtin_registered(lookup)
    return _resolve_renderer(lookup)


def ensure(name: str | None = None) -> BasePptxRenderer:
    """Return a renderer instance or raise if selection fails."""
    cfg: dict[str, object] | None = None
    if name is not None:
        cfg = {"pptx_renderer": name}
    choice = get_pptx_renderer_choice(cfg)
    renderer = select(choice)
    if renderer is None:
        raise _selection_error(choice)
    return renderer


@contextmanager
def convert_pptx_to_pdf(input_pptx: str) -> Iterator[str]:
    """Yield a temporary PDF converted from ``input_pptx``."""
    renderer = ensure()
    stem = Path(input_pptx).stem or "presentation"
    with tempfile.TemporaryDirectory(prefix="pdf-toolbox-pptx-") as tmp_dir:
        out_path = Path(tmp_dir) / f"{stem}.pdf"
        pdf_path = renderer.to_pdf(input_pptx, output_path=str(out_path))
        yield pdf_path


__all__ = [
    "RendererSelectionError",
    "available",
    "available_renderers",
    "convert_pptx_to_pdf",
    "ensure",
    "register",
    "select",
]
