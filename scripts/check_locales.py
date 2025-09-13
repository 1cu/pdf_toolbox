#!/usr/bin/env python3
"""Validate locale JSON files for structure and completeness.

Checks:
- JSON parses and contains objects "strings" and "labels"
- keys for both maps are snake_case (a-z0-9_)
- en.json and de.json have identical key sets for both maps
- No obsolete keys present (exact match with referenced keys in source)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "src" / "pdf_toolbox" / "locales"


def load_locale(lang: str) -> dict:
    """Load and minimally validate a locale JSON by language code."""
    p = LOCALES / f"{lang}.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{p} must be an object")
    for k in ("strings", "labels"):
        if k not in data or not isinstance(data[k], dict):
            raise SystemExit(f"{p} must define object '{k}'")
    snake = re.compile(r"^[a-z0-9_]+$")
    for group in ("strings", "labels"):
        for key, val in data[group].items():
            if not snake.match(key):
                raise SystemExit(f"{p}:{group} key '{key}' must be snake_case")
            if not isinstance(val, str):
                raise SystemExit(f"{p}:{group} key '{key}' must map to string")
    return data


def referenced_keys() -> tuple[set[str], set[str]]:
    """Return (string_keys, label_keys) used in source by scanning tr()/label()."""
    src = ROOT / "src"
    str_keys: set[str] = set()
    lab_keys: set[str] = set()
    tr_re = re.compile(r"\btr\(\"([a-z0-9_]+)\"")
    lab_re = re.compile(r"\blabel\(\"([a-z0-9_]+)\"\)")
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        str_keys.update(tr_re.findall(text))
        lab_keys.update(lab_re.findall(text))
    return str_keys, lab_keys


def main() -> int:
    """Validate locale files and report issues suitable for CI/pre-commit.

    Returns 0 on success; non-zero on validation error.
    """
    en = load_locale("en")
    de = load_locale("de")
    # enforce identical key sets between locales
    for group in ("strings", "labels"):
        k_en = set(en[group].keys())
        k_de = set(de[group].keys())
        if k_en != k_de:
            missing_en = sorted(k_de - k_en)
            missing_de = sorted(k_en - k_de)
            if missing_en:
                print(f"en.json missing {group} keys: {missing_en}")
            if missing_de:
                print(f"de.json missing {group} keys: {missing_de}")
            return 1

    ref_strings, ref_labels = referenced_keys()
    # no obsolete or missing: exact match
    if set(en["strings"]) != ref_strings:
        extra = sorted(set(en["strings"]) - ref_strings)
        missing = sorted(ref_strings - set(en["strings"]))
        if extra:
            print(f"obsolete string keys in locales: {extra}")
        if missing:
            print(f"missing string keys in locales: {missing}")
        return 1
    # For labels we only require en/de parity; keys are discovered dynamically at runtime
    return 0


if __name__ == "__main__":
    sys.exit(main())
