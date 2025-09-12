#!/usr/bin/env python3
"""Retrieve the project version from ``pyproject.toml``."""

from __future__ import annotations

import pathlib
import tomllib


def main() -> None:
    """Print the version defined in ``pyproject.toml``."""
    pyproject = pathlib.Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text())
    print(data["project"]["version"])


if __name__ == "__main__":
    main()
