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


def _iter_entry_points() -> Iterator[metadata.EntryPoint]:
    """Yield configured entry points while handling discovery errors."""
    try:
        collection = metadata.entry_points()
    except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: metadata backends can raise arbitrary errors; degrade to no plugins | issue:-
        logger.debug("pptx renderer entry point discovery failed: %s", exc)
        return iter(())

    if hasattr(collection, "select"):
        selected = cast(
            EntryPointIterable,
            collection.select(group=_ENTRY_POINT_GROUP),
        )
        return iter(selected)

    legacy_points = cast(Mapping[str, EntryPointIterable], collection)
    return iter(legacy_points.get(_ENTRY_POINT_GROUP, ()))


def _load_renderer_from_entry(
    entry: metadata.EntryPoint,
) -> type[BasePptxRenderer] | None:
    """Return a renderer class exposed by ``entry`` when available."""
    name = getattr(entry, "name", "<unknown>")
    renderer_cls: type[BasePptxRenderer] | None = None
    try:
        payload = entry.load()
    except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: plugin entry point import may fail arbitrarily; degrade to warning | issue:-
        logger.warning(
            "pptx renderer entry point '%s' failed to load: %s",
            name,
            exc,
        )
        return None

    if isinstance(payload, type) and issubclass(payload, BasePptxRenderer):
        renderer_cls = payload
    elif isinstance(payload, BasePptxRenderer):
        renderer_cls = payload.__class__
    elif isinstance(payload, str):
        module_name, _, attr = payload.partition(":")
        if not module_name:
            renderer_cls = None
        else:
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: plugin modules may be missing or broken; degrade to warning | issue:-
                logger.warning(
                    "pptx renderer entry point '%s' could not import %s: %s",
                    name,
                    module_name,
                    exc,
                )
            else:
                candidate = getattr(module, attr or "", None)
                if isinstance(candidate, type) and issubclass(
                    candidate, BasePptxRenderer
                ):
                    renderer_cls = candidate

    if renderer_cls is None:
        logger.warning(
            "pptx renderer entry point '%s' did not expose a renderer class",
            name,
        )

    return renderer_cls


def _load_entry_points() -> None:
    """Load PPTX renderer entry points once."""
def _load_entry_points() -> None:
    """Load PPTX renderer entry points once."""
    if _ENTRY_POINT_STATE["loaded"]:
        return

    for entry in _iter_entry_points():
        renderer_cls = _load_renderer_from_entry(entry)
        if renderer_cls is None:
            continue
        try:
            register(renderer_cls)
        except ValueError as exc:
            logger.debug("pptx renderer registration skipped: %s", exc)
    _ENTRY_POINT_STATE["loaded"] = True
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
    except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: builtin providers rely on optional platform modules; degrade to debug | issue:-
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


def _renderer_display_name(renderer_cls: type[BasePptxRenderer]) -> str:
    """Return a readable identifier for ``renderer_cls``."""
    return getattr(renderer_cls, "name", renderer_cls.__name__)


def _safe_instantiate_renderer(
    renderer_cls: type[BasePptxRenderer],
) -> BasePptxRenderer | None:
    """Return an instance of ``renderer_cls`` while logging failures."""
    try:
        return renderer_cls()
    except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: renderer constructors may fail arbitrarily; treat as unavailable | issue:-
        logger.info(
            "pptx renderer %s failed to initialise: %s",
            _renderer_display_name(renderer_cls),
            exc,
        )
        return None


def _ensure_instance(
    renderer_cls: type[BasePptxRenderer],
    instance: BasePptxRenderer | None,
) -> BasePptxRenderer | None:
    """Return ``instance`` or try instantiating ``renderer_cls``."""
    if instance is not None:
        return instance
    return _safe_instantiate_renderer(renderer_cls)


def _log_can_handle_failure(
    renderer_cls: type[BasePptxRenderer],
    exc: Exception,
) -> None:
    """Log ``exc`` raised by a renderer's ``can_handle`` implementation."""
    logger.info(
        "pptx renderer %s.can_handle() failed: %s",
        _renderer_display_name(renderer_cls),
        exc,
    )


def _evaluate_instance_can_handle(
    renderer_cls: type[BasePptxRenderer],
    instance: BasePptxRenderer,
) -> bool:
    """Return ``True`` when ``instance.can_handle`` signals availability."""
    method = getattr(instance, "can_handle", None)
    if not callable(method):
        return True
    try:
        return bool(method())
    except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: plugin can_handle implementations may fail; treat as unavailable | issue:-
        _log_can_handle_failure(renderer_cls, exc)
        return False


def _evaluate_can_handle(
    renderer_cls: type[BasePptxRenderer],
    candidate: Any,
    instance: BasePptxRenderer | None,
) -> tuple[bool, BasePptxRenderer | None]:
    """Return whether ``candidate`` signals availability for ``renderer_cls``."""
    try:
        available = bool(candidate())
    except TypeError:
        instance = _ensure_instance(renderer_cls, instance)
        if instance is None:
            return False, None
        available = _evaluate_instance_can_handle(renderer_cls, instance)
    except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: plugin can_handle implementations may fail; treat as unavailable | issue:-
        _log_can_handle_failure(renderer_cls, exc)
        return False, instance
    else:
        if not available:
            return False, instance
    return available, instance


def _assess_renderer(
    renderer_cls: type[BasePptxRenderer],
) -> tuple[BasePptxRenderer | None, bool]:
    """Return an instance and whether ``renderer_cls`` can handle rendering."""
    instance: BasePptxRenderer | None = None

    candidate: Any | None = getattr(renderer_cls, "can_handle", None)
    if candidate is None:
        instance = _ensure_instance(renderer_cls, instance)
        if instance is None:
            return None, False
        return instance, True

    available, instance = _evaluate_can_handle(renderer_cls, candidate, instance)
    if not available:
        return None, False

    instance = _ensure_instance(renderer_cls, instance)
    if instance is None:
        return None, False
    return instance, True


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
