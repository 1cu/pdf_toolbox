"""Runtime registry for PPTX rendering providers."""

from __future__ import annotations

import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from pdf_toolbox.config import PptxRendererChoice, get_pptx_renderer_choice
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.utils import logger

_REGISTRY: dict[str, type[BasePptxRenderer]] = {}
_AUTO_PRIORITY = ("lightweight", "ms_office")


class RendererSelectionError(LookupError):
    """Raised when selecting a PPTX renderer fails."""


def register[RendererT: BasePptxRenderer](
    renderer_cls: type[RendererT],
) -> type[RendererT]:
    """Register ``renderer_cls`` under its ``name`` attribute.

    Args:
        renderer_cls: Subclass that implements the renderer interface.

    Returns:
        The ``renderer_cls`` argument to support decorator usage.

    Raises:
        ValueError: If ``renderer_cls`` does not declare a non-empty ``name``
            attribute or if the name is already registered with a different
            class.
    """
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
    return tuple(_REGISTRY.keys())


def _iter_auto_candidates() -> Iterable[type[BasePptxRenderer]]:
    """Yield renderer classes in the order considered for ``auto`` selection."""
    yielded: set[str] = set()
    for preferred in _AUTO_PRIORITY:
        renderer_cls = _REGISTRY.get(preferred)
        if renderer_cls is not None:
            yielded.add(preferred)
            yield renderer_cls
    for name, renderer_cls in _REGISTRY.items():
        if name == "null" or name in yielded:
            continue
        yield renderer_cls


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


def select(
    name: str | None = None,
    *,
    strict: bool = False,
) -> type[BasePptxRenderer] | None:
    """Return the renderer class matching ``name`` or ``auto``.

    Args:
        name: Renderer identifier or the special value ``"auto"``. When omitted
            the persisted configuration is inspected.
        strict: Whether to raise :class:`RendererSelectionError` when no
            renderer matches the request.

    Returns:
        A renderer class when a match is found, otherwise ``None``. When
        ``name`` resolves to ``"auto"`` the first non-``null`` renderer is
        returned if available. The ``null`` renderer is used as a fallback when
        registered.
    """
    cfg: dict[str, object] | None = None
    if name is not None:
        cfg = {"pptx_renderer": name}
    choice = get_pptx_renderer_choice(cfg)

    if choice == "none":
        renderer_cls = _REGISTRY.get("null")
        if renderer_cls is None and strict:
            raise _selection_error(choice)
        return renderer_cls

    if choice == "auto":
        for candidate in _iter_auto_candidates():
            probe = getattr(candidate, "probe", None)
            if callable(probe):
                try:
                    available = probe()
                except Exception as exc:
                    renderer_name = getattr(candidate, "name", candidate.__name__)
                    logger.warning(
                        "Probe for PPTX renderer %s failed: %s",
                        renderer_name,
                        exc,
                        exc_info=exc,
                    )
                    available = False
                if not available:
                    continue

            return candidate
        renderer_cls = _REGISTRY.get("null")
        if renderer_cls is None and strict:
            raise _selection_error(choice)
        return renderer_cls

    renderer_cls = _REGISTRY.get(choice)
    if renderer_cls is None and strict:
        raise _selection_error(choice)
    return renderer_cls


def ensure(name: str | None = None) -> type[BasePptxRenderer]:
    """Return a renderer class or raise if selection fails."""
    renderer_cls = select(name, strict=True)
    if (
        renderer_cls is None
    ):  # pragma: no cover  # pdf-toolbox: unreachable once select(strict=True) succeeds | issue:-
        raise _selection_error(get_pptx_renderer_choice({"pptx_renderer": name}))
    return renderer_cls


@contextmanager
def convert_pptx_to_pdf(input_pptx: str) -> Iterator[str]:
    """Yield a temporary PDF converted from ``input_pptx``.

    The configured PPTX renderer is instantiated via the registry and asked to
    render ``input_pptx`` into a PDF within a temporary directory. The yielded
    path remains valid for the duration of the context manager and is removed
    afterwards to avoid leaking intermediate artefacts.
    """
    renderer_cls = ensure()
    renderer = renderer_cls()
    stem = Path(input_pptx).stem or "presentation"
    with tempfile.TemporaryDirectory(prefix="pdf-toolbox-pptx-") as tmp_dir:
        out_path = Path(tmp_dir) / f"{stem}.pdf"
        pdf_path = renderer.to_pdf(input_pptx, output_path=str(out_path))
        yield pdf_path


__all__ = [
    "RendererSelectionError",
    "available",
    "convert_pptx_to_pdf",
    "ensure",
    "register",
    "select",
]
