"""Ensure no relative imports appear in the source tree."""

from __future__ import annotations

import ast
from pathlib import Path


def test_no_relative_imports() -> None:
    src_dir = Path(__file__).resolve().parents[1] / "src" / "pdf_toolbox"
    for path in src_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level != 0:
                msg = f"Relative import found in {path} on line {node.lineno}"
                raise AssertionError(msg)
