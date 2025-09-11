#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import xml.etree.ElementTree as ET

THRESHOLD = 0.95
EXCLUDE_SUFFIXES = ("pdf_toolbox/gui.py",)


def main() -> int:
    xml_file = Path("coverage.xml")
    if not xml_file.exists():
        print("coverage.xml not found. Run tests first.", file=sys.stderr)
        return 1
    tree = ET.parse(xml_file)
    root = tree.getroot()
    failures: list[tuple[str, float]] = []
    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        if not filename:
            continue
        if any(filename.endswith(s) for s in EXCLUDE_SUFFIXES):
            continue
        rate = float(cls.get("line-rate", "0"))
        if rate < THRESHOLD:
            failures.append((filename, rate))
    if failures:
        for fn, rate in failures:
            print(f"{fn} has {rate * 100:.2f}% coverage, below {THRESHOLD * 100:.0f}%")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
