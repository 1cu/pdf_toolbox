"""Runtime registry for PPTX rendering providers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from pdf_toolbox.renderers.pptx_base import BasePptxRenderer

RendererT = TypeVar("RendererT", bound=BasePptxRenderer)

_REGISTRY: dict[str, type[BasePptxRenderer]] = {}


def register(renderer_cls: type[RendererT]) -> type[RendererT]:
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
    for name, renderer_cls in _REGISTRY.items():
        if name != "null":
            yield renderer_cls


def select(name: str) -> type[BasePptxRenderer] | None:
    """Return the renderer class matching ``name`` or ``auto``.

    Args:
        name: Renderer identifier or the special value ``"auto"``.

    Returns:
        A renderer class when a match is found, otherwise ``None``. When
        ``name`` is ``"auto"`` the first non-``null`` renderer is returned if
        available. The ``null`` renderer is used as a fallback when registered.
    """

    key = (name or "").strip().lower()
    if not key:
        return None

    if key == "auto":
        for candidate in _iter_auto_candidates():
            return candidate
        return _REGISTRY.get("null")

    return _REGISTRY.get(key)


__all__ = ["available", "register", "select"]
