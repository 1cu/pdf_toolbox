from __future__ import annotations

"""Common utilities for PDF toolbox modules."""

from pathlib import Path
import importlib
import logging
from typing import Iterable

import fitz  # type: ignore


REQUIRED_LIBS: Iterable[str] = (
    "fitz",
    "PIL.Image",
    "docx",
    "win32com.client",
)


def ensure_libs() -> None:
    """Ensure optional runtime libraries are importable.

    Raises a ``RuntimeError`` if a library is missing so callers can
    present a helpful message to the user.
    """

    missing: list[str] = []
    for mod in REQUIRED_LIBS:
        try:
            importlib.import_module(mod)
        except Exception:  # pragma: no cover - best effort
            missing.append(mod)
    if missing:
        raise RuntimeError(
            "Missing required libraries: " + ", ".join(missing)
        )


def sane_output_dir(base_path: str | Path, out_dir: str | Path | None) -> Path:
    """Return a Path for output files.

    If ``out_dir`` is ``None`` the directory of ``base_path`` is returned.
    The directory is created if it does not yet exist.
    """

    base = Path(base_path)
    target = Path(out_dir) if out_dir else base.parent
    target.mkdir(parents=True, exist_ok=True)
    return target


def update_metadata(fitz_doc: fitz.Document, note: str | None = None) -> None:
    """Update metadata with a custom note."""

    metadata = dict(fitz_doc.metadata or {})
    if note:
        metadata["subject"] = metadata.get("subject", "") + note
    metadata.setdefault("producer", "pdf_toolbox")
    metadata.setdefault("author", "Jens Bergmann")
    fitz_doc.set_metadata(metadata)


__all__ = ["ensure_libs", "sane_output_dir", "update_metadata"]
