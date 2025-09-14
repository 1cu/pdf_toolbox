#!/usr/bin/env python3
"""Verify that linter and coverage suppressions are documented."""

from __future__ import annotations

import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COVERAGE_RE = re.compile(
    r"#\s*(pragma:\s*no\s*cover|coverage:\s*ignore|pragma:\s*nocover|pragma:\s*exclude\s*from\s*coverage)(.*)",
    re.IGNORECASE,
)


def gather_lint_exceptions() -> set[str]:
    """Return ``file:line`` entries for suppressed linter warnings."""
    paths: list[Path] = []
    for folder in ("src", "scripts", "tests"):
        base = ROOT / folder
        if base.exists():
            paths.extend(base.rglob("*.py"))

    found: set[str] = set()
    for path in paths:
        with tokenize.open(path) as fh:
            for tok_type, tok_string, (lineno, _), _, _ in tokenize.generate_tokens(
                fh.readline
            ):
                if tok_type == tokenize.COMMENT and (
                    "noqa" in tok_string
                    or "nosec" in tok_string
                    or "type: ignore" in tok_string
                ):
                    rel = path.relative_to(ROOT).as_posix()
                    found.add(f"{rel}:{lineno}")
    return found


def gather_coverage_exceptions() -> tuple[set[str], list[str], list[str]]:
    """Return coverage suppression info.

    Returns:
        A tuple of ``(found, missing_justification, block_wide)`` where
        ``found`` is a ``file:line`` set of exclusions, ``missing_justification``
        lists lines lacking inline rationale, and ``block_wide`` lists comment-only
        lines that disable coverage for a block or entire file.
    """
    paths: list[Path] = []
    for folder in ("src", "scripts", "tests"):
        base = ROOT / folder
        if base.exists():
            paths.extend(base.rglob("*.py"))

    found: set[str] = set()
    missing_just: list[str] = []
    block_wide: list[str] = []
    for path in paths:
        lines = path.read_text(encoding="utf8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            match = COVERAGE_RE.search(line)
            if not match:
                continue
            rel = path.relative_to(ROOT).as_posix()
            key = f"{rel}:{lineno}"
            found.add(key)
            rule = re.sub(r"\s+", " ", match.group(1).strip().lower())
            rest = match.group(2).strip()
            if not rest:
                context = line.strip()
                missing_just.append(f"{key} ({rule}) {context}")
            before_hash = line.split("#", 1)[0]
            if not before_hash.strip():
                context = line.strip()
                block_wide.append(f"{key} ({rule}) {context}")
    return found, missing_just, block_wide


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
    lint_ex = gather_lint_exceptions()
    cov_ex, missing_just, block_wide = gather_coverage_exceptions()
    documented = documented_exceptions()
    found = lint_ex | cov_ex
    missing = sorted(found - documented)
    extra = sorted(documented - found)

    exit_code = 0
    if missing:
        sys.stderr.write("Missing entries in DEVELOPMENT.md:\n")
        for item in missing:
            sys.stderr.write(f"  {item}\n")
        exit_code = 1
    if extra:
        sys.stderr.write("Stale entries in DEVELOPMENT.md:\n")
        for item in extra:
            sys.stderr.write(f"  {item}\n")
        exit_code = 1
    if missing_just:
        sys.stderr.write("Coverage exclusions without justification:\n")
        for item in missing_just:
            sys.stderr.write(f"  {item}\n")
        exit_code = 1
    if block_wide:
        sys.stderr.write("File or block coverage exclusions:\n")
        for item in block_wide:
            sys.stderr.write(f"  {item}\n")
        exit_code = 1

    if exit_code == 0:
        sys.stdout.write("All lint and coverage exceptions documented.\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
