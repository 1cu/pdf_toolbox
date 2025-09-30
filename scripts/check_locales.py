#!/usr/bin/env python3
"""Validate locale JSON files for structure and completeness.

Checks:
- JSON parses and contains objects "strings" and "labels"
- keys for both maps use lowercase letters, numbers, underscores, or dots
- all locale files share identical key sets
- No obsolete keys present (exact match with referenced keys in source)
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "src" / "pdf_toolbox" / "locales"

ERR_OBJECT = "{path} must be an object"
ERR_MISSING = "{path} must define object '{key}'"
ERR_KEY_FORMAT = (
    "{path}:{group} key '{key}' must use lowercase letters, numbers, underscores, or dots"
)
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
    key_pattern = re.compile(r"^[a-z0-9_.]+$")
    for group in ("strings", "labels"):
        for key, val in data[group].items():
            if not key_pattern.match(key):
                raise SystemExit(ERR_KEY_FORMAT.format(path=p, group=group, key=key))
            if not isinstance(val, str):
                raise SystemExit(ERR_STRING.format(path=p, group=group, key=key))
    return data


def referenced_keys() -> tuple[set[str], set[str]]:
    """Return (string_keys, label_keys) used in source by scanning tr()/label()."""
    src = ROOT / "src"
    string_keys: set[str] = set()
    label_keys: set[str] = set()
    tr_re = re.compile(r"\btr\(\"([a-z0-9_.]+)\"")
    lab_re = re.compile(r"\blabel\(\"([a-z0-9_]+)\"\)")
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        string_keys.update(tr_re.findall(text))
        label_keys.update(lab_re.findall(text))
    sys.path.insert(0, str(src))
    try:
        actions_mod = importlib.import_module("pdf_toolbox.actions")
        actions_mod._registry.clear()
        actions_mod._auto_discover.cache_clear()
        for name in list(sys.modules):
            if name.startswith("pdf_toolbox.actions") and name != "pdf_toolbox.actions":
                sys.modules.pop(name)
        for act in actions_mod.list_actions():
            string_keys.add(act.key)
            for param in act.form_params:
                label_keys.add(param.name)
    finally:
        sys.path.remove(str(src))
    return string_keys, label_keys


def _load_all_locales() -> dict[str, dict]:
    """Return a mapping of language code to loaded locale data."""
    return {p.stem: load_locale(p.stem) for p in LOCALES.glob("*.json")}


def _validate_key_sets(locales: dict[str, dict]) -> bool:
    """Ensure each locale matches the base key sets for strings and labels."""
    ok = True
    base_lang, base_data = next(iter(locales.items()))
    for group in ("strings", "labels"):
        base_keys = set(base_data[group].keys())
        for lang, data in locales.items():
            if lang == base_lang:
                continue
            keys = set(data[group].keys())
            if keys != base_keys:
                _log_locale_diff(lang, group, base_keys, keys)
                ok = False
    return ok


def _validate_referenced_keys(locales: dict[str, dict], group: str, ref_keys: set[str]) -> bool:
    """Validate that each locale's ``group`` keys equal the referenced set."""
    ok = True
    for lang, data in locales.items():
        keys = set(data[group].keys())
        if keys == ref_keys:
            continue
        extra = sorted(keys - ref_keys)
        missing = sorted(ref_keys - keys)
        if extra:
            logging.error("%s.json obsolete %s keys: %s", lang, group, extra)
        if missing:
            logging.error("%s.json missing %s keys: %s", lang, group, missing)
        ok = False
    return ok


def _log_locale_diff(
    lang: str,
    group: str,
    base_keys: set[str],
    keys: set[str],
) -> None:
    """Log differences between base locale keys and ``lang`` keys."""
    missing = sorted(base_keys - keys)
    extra = sorted(keys - base_keys)
    if missing:
        logging.error("%s.json missing %s keys: %s", lang, group, missing)
    if extra:
        logging.error("%s.json has extra %s keys: %s", lang, group, extra)


def main() -> int:
    """Validate locale files and report issues suitable for CI/pre-commit.

    Returns 0 on success; non-zero on validation error.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    locales = _load_all_locales()
    if not locales:
        logging.error("no locales found")
        return 1
    ok = _validate_key_sets(locales)
    ref_strings, ref_labels = referenced_keys()
    if not _validate_referenced_keys(locales, "strings", ref_strings):
        ok = False
    if not _validate_referenced_keys(locales, "labels", ref_labels):
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
