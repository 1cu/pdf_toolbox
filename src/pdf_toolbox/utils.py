from __future__ import annotations

"""Common utilities for PDF toolbox modules."""

from pathlib import Path
import importlib
import json
import sys
from typing import Iterable, List

import fitz  # type: ignore


REQUIRED_LIBS: Iterable[str] = (
    "fitz",
    "PIL.Image",
    "docx",
    "win32com.client",
)


CONFIG_FILE = Path(__file__).resolve().parent.parent / "pdf_toolbox_config.json"


def _load_author_info() -> tuple[str, str]:
    """Return configured author information.

    The configuration must provide ``author`` and ``email`` fields in
    ``pdf_toolbox_config.json``. A ``RuntimeError`` is raised if the configuration
    is missing or incomplete.
    """

    try:
        data = json.loads(CONFIG_FILE.read_text())
        author = data["author"]
        email = data["email"]
    except Exception as exc:  # pragma: no cover - best effort
        raise RuntimeError(
            "pdf_toolbox_config.json must define 'author' and 'email'"
        ) from exc
    return author, email


def ensure_libs() -> None:
    """Ensure optional runtime libraries are importable.

    Raises a ``RuntimeError`` if a library is missing so callers can
    present a helpful message to the user.
    """

    missing: list[str] = []
    for mod in REQUIRED_LIBS:
        if mod == "win32com.client" and sys.platform != "win32":
            continue
        try:
            importlib.import_module(mod)
        except Exception:  # pragma: no cover - best effort
            missing.append(mod)
    if missing:
        raise RuntimeError("Missing required libraries: " + ", ".join(missing))


def parse_page_spec(spec: str | None, total: int) -> List[int]:
    """Parse a page/slide specification into a list of 1-based numbers.

    ``spec`` follows a simple syntax with comma-separated parts. Each part may
    be a single number (``"5"``), a range like ``"3-7"``, an open-ended range
    such as ``"2-"`` or ``"-4"``, or any combination thereof
    (e.g. ``"1,5,6"``). ``None`` or an empty string selects all pages.

    A ``ValueError`` is raised if the specification is invalid or references
    pages outside ``1..total``.
    """

    if not spec:
        return list(range(1, total + 1))

    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start = int(start_s) if start_s else 1
                end = int(end_s) if end_s else total
            except ValueError as exc:
                raise ValueError("Invalid page specification") from exc
            if start < 1 or end > total:
                raise ValueError(f"page {start}-{end} out of range 1..{total}")
            if end < start:
                raise ValueError("end must be greater than or equal to start")
            pages.update(range(start, end + 1))
        else:
            try:
                page = int(part)
            except ValueError as exc:
                raise ValueError("Invalid page specification") from exc
            if page < 1 or page > total:
                raise ValueError(f"page {page} out of range 1..{total}")
            pages.add(page)
    return sorted(pages)


def sane_output_dir(base_path: str | Path, out_dir: str | Path | None) -> Path:
    """Return a Path for output files.

    If ``out_dir`` is ``None`` the directory of ``base_path`` is returned.
    The directory is created if it does not yet exist.
    """

    base = Path(base_path)
    target = Path(out_dir) if out_dir else base.parent
    if target.suffix:
        raise ValueError(f"Output directory must be a directory, not a file: {out_dir}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def update_metadata(fitz_doc: fitz.Document, note: str | None = None) -> None:
    """Update metadata with a custom note."""

    metadata = dict(fitz_doc.metadata or {})
    if note:
        existing_subject = metadata.get("subject") or ""
        metadata["subject"] = existing_subject + note
    metadata.setdefault("producer", "pdf_toolbox")
    author, _email = _load_author_info()
    metadata["author"] = metadata.get("author") or author
    fitz_doc.set_metadata(metadata)


__all__ = ["ensure_libs", "sane_output_dir", "update_metadata", "parse_page_spec"]
