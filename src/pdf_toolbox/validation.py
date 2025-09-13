"""Validation helpers for inputs and configuration."""

from __future__ import annotations

from pathlib import Path


def validate_pdf_path(path: str | Path) -> Path:
    """Validate and sanitize a PDF file path.

    Returns a ``Path`` object if valid, otherwise raises a descriptive
    exception.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if p.is_dir():
        raise IsADirectoryError(f"Expected a file, got directory: {path}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"File must be a PDF: {path}")
    return p


def validate_config(config: dict) -> dict:
    """Validate configuration values and return them unchanged.

    The configuration must include ``author`` and ``email`` fields.
    """
    required = ("author", "email")
    for key in required:
        val = (config or {}).get(key)
        if not val:
            raise ValueError(f"Missing required config field: {key}")
    return config


__all__ = ["validate_config", "validate_pdf_path"]
