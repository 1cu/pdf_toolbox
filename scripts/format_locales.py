#!/usr/bin/env python3
"""Format locale JSON files with stable ordering and indentation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "src" / "pdf_toolbox" / "locales"


def format_file(path: Path) -> None:
    """Format a single locale JSON file with stable indentation and key order."""
    data = json.loads(path.read_text(encoding="utf-8"))
    # Sort keys within nested dicts
    if isinstance(data, dict):
        for k in ("strings", "labels"):
            if isinstance(data.get(k), dict):
                data[k] = {kk: data[k][kk] for kk in sorted(data[k])}
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Format all locale JSON files under src/pdf_toolbox/locales/.

    Returns 0 on success.
    """
    for p in sorted(LOCALES.glob("*.json")):
        format_file(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
