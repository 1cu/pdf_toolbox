"""Configuration helpers shared across modules."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal

from pdf_toolbox import utils

CONFIG_PATH = utils.CONFIG_FILE
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

KnownPptxRenderer = Literal[
    "auto",
    "none",
    "ms_office",
    "http_office",
    "lightweight",
]
PptxRendererChoice = str

_PPTX_RENDERER_KEY = "pptx_renderer"
_PPTX_RENDERER_DEFAULT: KnownPptxRenderer = "auto"
_PPTX_RENDERER_ALIASES: dict[str, KnownPptxRenderer] = {
    "auto": "auto",
    "none": "none",
    "null": "none",
    "ms_office": "ms_office",
    "http_office": "http_office",
    "lightweight": "lightweight",
}

DEFAULT_CONFIG = {
    "last_open_dir": str(Path.home()),
    "last_save_dir": str(Path.home()),
    "jpeg_quality": "High (95)",
    "opt_quality": "default",
    "opt_compress_images": False,
    "split_pages": 1,
    "log_level": "INFO",
    "language": "system",
    _PPTX_RENDERER_KEY: _PPTX_RENDERER_DEFAULT,
    "http_office": {},
}


def _normalise_pptx_renderer(value: Any) -> PptxRendererChoice:
    """Return a canonical renderer choice for ``value``."""
    if value is None:
        return "none"
    if isinstance(value, str):
        key = value.strip().lower()
        if not key:
            return _PPTX_RENDERER_DEFAULT
        alias = _PPTX_RENDERER_ALIASES.get(key)
        if alias:
            return alias
        return key
    return _PPTX_RENDERER_DEFAULT


def load_config_at(path: Path) -> dict:
    """Load configuration from a specific path."""
    cfg = DEFAULT_CONFIG.copy()
    if path.exists():
        with suppress(Exception):
            cfg.update(json.loads(path.read_text()))
    cfg[_PPTX_RENDERER_KEY] = _normalise_pptx_renderer(cfg.get(_PPTX_RENDERER_KEY))
    return cfg


def save_config_at(path: Path, cfg: dict) -> None:
    """Persist configuration to a specific path."""
    data = dict(cfg)
    if _PPTX_RENDERER_KEY in data:
        data[_PPTX_RENDERER_KEY] = _normalise_pptx_renderer(data[_PPTX_RENDERER_KEY])
    path.write_text(json.dumps(data, indent=2))


def load_config() -> dict:
    """Load configuration using :data:`CONFIG_PATH`."""
    return load_config_at(CONFIG_PATH)


def save_config(cfg: dict) -> None:
    """Persist configuration using :data:`CONFIG_PATH`."""
    save_config_at(CONFIG_PATH, cfg)


def get_pptx_renderer_choice(
    cfg: Mapping[str, object] | None = None,
) -> PptxRendererChoice:
    """Return the configured PPTX renderer choice.

    Args:
        cfg: Optional configuration mapping. When omitted the persisted config
            is loaded via :func:`load_config`.

    Returns:
        The normalised renderer identifier declared in the configuration.
    """
    source = cfg if cfg is not None else load_config()
    if _PPTX_RENDERER_KEY not in source:
        return _PPTX_RENDERER_DEFAULT
    value = source.get(_PPTX_RENDERER_KEY)
    return _normalise_pptx_renderer(value)


__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "PptxRendererChoice",
    "get_pptx_renderer_choice",
    "load_config",
    "load_config_at",
    "save_config",
    "save_config_at",
]
