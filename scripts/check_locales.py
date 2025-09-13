#!/usr/bin/env python3
"""Validate locale JSON files for structure and completeness.

Checks:
- JSON parses and contains objects "strings" and "labels"
- keys for both maps are snake_case (a-z0-9_)
- all locale files share identical key sets
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
    string_keys: set[str] = set()
    label_keys: set[str] = set()
    tr_re = re.compile(r"\btr\(\"([a-z0-9_]+)\"")
    lab_re = re.compile(r"\blabel\(\"([a-z0-9_]+)\"\)")
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        string_keys.update(tr_re.findall(text))
        label_keys.update(lab_re.findall(text))
    sys.path.insert(0, str(src))
    try:
        from pdf_toolbox import actions as actions_mod  # noqa: PLC0415

        actions_mod._registry.clear()
        actions_mod._discovered = False
        for name in list(sys.modules):
            if name.startswith("pdf_toolbox.builtin"):
                sys.modules.pop(name)
        from pdf_toolbox.actions import list_actions  # noqa: PLC0415

        for act in list_actions():
            string_keys.add(act.key)
    finally:
        sys.path.remove(str(src))
    return string_keys, label_keys


def main() -> int:
    """Validate locale files and report issues suitable for CI/pre-commit.

    Returns 0 on success; non-zero on validation error.
    """
    locales = {p.stem: load_locale(p.stem) for p in LOCALES.glob("*.json")}
    if not locales:
        print("no locales found")
        return 1
    ok = True
    ref_strings, _ = referenced_keys()
    first = next(iter(locales.values()))
    for group in ("strings", "labels"):
        base = set(first[group].keys())
        for lang, data in locales.items():
            keys = set(data[group].keys())
            if keys != base:
                missing = sorted(base - keys)
                extra = sorted(keys - base)
                if missing:
                    print(f"{lang}.json missing {group} keys: {missing}")
                if extra:
                    print(f"{lang}.json has extra {group} keys: {extra}")
                ok = False
    for lang, data in locales.items():
        keys = set(data["strings"].keys())
        if keys != ref_strings:
            extra = sorted(keys - ref_strings)
            missing = sorted(ref_strings - keys)
            if extra:
                print(f"{lang}.json obsolete string keys: {extra}")
            if missing:
                print(f"{lang}.json missing string keys: {missing}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
