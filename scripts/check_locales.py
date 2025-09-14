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
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "src" / "pdf_toolbox" / "locales"

ERR_OBJECT = "{path} must be an object"
ERR_MISSING = "{path} must define object '{key}'"
ERR_SNAKE = "{path}:{group} key '{key}' must be snake_case"
ERR_STRING = "{path}:{group} key '{key}' must map to string"


def load_locale(lang: str) -> dict:
    """Load and minimally validate a locale JSON by language code."""
    p = LOCALES / f"{lang}.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(ERR_OBJECT.format(path=p))
    for k in ("strings", "labels"):
        if k not in data or not isinstance(data[k], dict):
            raise SystemExit(ERR_MISSING.format(path=p, key=k))
    snake = re.compile(r"^[a-z0-9_]+$")
    for group in ("strings", "labels"):
        for key, val in data[group].items():
            if not snake.match(key):
                raise SystemExit(ERR_SNAKE.format(path=p, group=group, key=key))
            if not isinstance(val, str):
                raise SystemExit(ERR_STRING.format(path=p, group=group, key=key))
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
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    locales = {p.stem: load_locale(p.stem) for p in LOCALES.glob("*.json")}
    if not locales:
        logging.error("no locales found")
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
                    logging.error("%s.json missing %s keys: %s", lang, group, missing)
                if extra:
                    logging.error("%s.json has extra %s keys: %s", lang, group, extra)
                ok = False
    for lang, data in locales.items():
        keys = set(data["strings"].keys())
        if keys != ref_strings:
            extra = sorted(keys - ref_strings)
            missing = sorted(ref_strings - keys)
            if extra:
                logging.error("%s.json obsolete string keys: %s", lang, extra)
            if missing:
                logging.error("%s.json missing string keys: %s", lang, missing)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
