"""Configuration helpers shared across modules."""

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path

from pdf_toolbox import utils

CONFIG_PATH = utils.CONFIG_FILE
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "last_open_dir": str(Path.home()),
    "last_save_dir": str(Path.home()),
    "jpeg_quality": "High (95)",
    "opt_quality": "default",
    "opt_compress_images": False,
    "split_pages": 1,
    "log_level": "INFO",
    "language": "system",
}


def load_config_at(path: Path) -> dict:
    """Load configuration from a specific path."""
    cfg = DEFAULT_CONFIG.copy()
    if path.exists():
        with suppress(Exception):
            cfg.update(json.loads(path.read_text()))
    return cfg


def save_config_at(path: Path, cfg: dict) -> None:
    """Persist configuration to a specific path."""
    path.write_text(json.dumps(cfg, indent=2))


def load_config() -> dict:
    """Load configuration using :data:`CONFIG_PATH`."""
    return load_config_at(CONFIG_PATH)


def save_config(cfg: dict) -> None:
    """Persist configuration using :data:`CONFIG_PATH`."""
    save_config_at(CONFIG_PATH, cfg)


__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "load_config",
    "load_config_at",
    "save_config",
    "save_config_at",
]
