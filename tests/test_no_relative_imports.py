"""Ensure no relative imports appear in the source tree."""

from __future__ import annotations

import ast
from math import ceil
from pathlib import Path

import pytest


def _python_sources() -> list[Path]:
    src_dir = Path(__file__).resolve().parents[1] / "src" / "pdf_toolbox"
    return sorted(src_dir.rglob("*.py"))


_PY_FILES = _python_sources()
_GROUPS = 8
_CHUNK_SIZE = max(1, ceil(len(_PY_FILES) / _GROUPS))
_FILE_GROUPS = [
    _PY_FILES[index : index + _CHUNK_SIZE] for index in range(0, len(_PY_FILES), _CHUNK_SIZE)
]
if not _FILE_GROUPS:
    _FILE_GROUPS = [[]]


@pytest.mark.parametrize(
    "paths",
    _FILE_GROUPS,
    ids=lambda paths: paths[0].stem if paths else "empty",
)
def test_no_relative_imports(paths: list[Path]) -> None:
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level != 0:
                msg = f"Relative import found in {path} on line {node.lineno}"
                raise AssertionError(msg)
