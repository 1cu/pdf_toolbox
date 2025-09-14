#!/usr/bin/env python3
"""Verify that all linter suppressions are documented."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def gather_exceptions() -> set[str]:
    """Return ``file:line`` entries for suppressed linter warnings."""
    paths: list[Path] = []
    for folder in ("src", "scripts", "tests"):
        base = ROOT / folder
        if base.exists():
            paths.extend(base.rglob("*.py"))

    found: set[str] = set()
    for path in paths:
        with path.open(encoding="utf8") as fh:
            for lineno, line in enumerate(fh, 1):
                hash_pos = line.find("#")
                if hash_pos != -1:
                    comment = line[hash_pos:]
                    if (
                        "noqa" in comment
                        or "nosec" in comment
                        or "type: ignore" in comment
                    ):
                        found.add(f"{path.relative_to(ROOT)}:{lineno}")
    return found


def documented_exceptions() -> set[str]:
    """Return ``file:line`` entries listed in ``DEVELOPMENT.md``."""
    content = (ROOT / "DEVELOPMENT.md").read_text(encoding="utf8").splitlines()
    entries: set[str] = set()
    table = False
    for line in content:
        if line.startswith("| File / Line"):
            table = True
            continue
        if table:
            if not line.strip() or not line.startswith("|"):
                break
            if line.startswith("| ---"):
                continue
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if cells and cells[0] and cells[0] != "*(none yet)*":
                entries.add(cells[0])
    return entries


def main() -> int:
    """Exit with 1 if undocumented suppressions are found."""
    code = gather_exceptions()
    documented = documented_exceptions()
    missing = sorted(code - documented)
    extra = sorted(documented - code)

    if missing or extra:
        if missing:
            sys.stderr.write("Missing entries in DEVELOPMENT.md:\n")
            for item in missing:
                sys.stderr.write(f"  {item}\n")
        if extra:
            sys.stderr.write("Stale entries in DEVELOPMENT.md:\n")
            for item in extra:
                sys.stderr.write(f"  {item}\n")
        return 1
    sys.stdout.write("All lint exceptions documented.\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - simple script
    raise SystemExit(main())
