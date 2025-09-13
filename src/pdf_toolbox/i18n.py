"""JSON-backed i18n helper for English and German.

Loads translations from ``pdf_toolbox/locales/<lang>.json``. Supports two maps:

- ``strings``: general UI strings
- ``labels``: field/parameter label overrides

Use ``tr(key)`` for UI strings and ``label(name)`` to resolve parameter labels.
"""

from __future__ import annotations

import json
import locale
from contextlib import suppress
from importlib import resources
from typing import Any

_LC_MESSAGES: int = getattr(locale, "LC_MESSAGES", locale.LC_CTYPE)

_LANG = "en"
_CACHE: dict[str, dict] = {}


def set_language(lang: str | None) -> None:
    """Set current UI language to 'en', 'de', or system default."""
    global _LANG  # noqa: PLW0603
    if not lang:
        _LANG = autodetect()
        return
    low = lang.lower()
    if low.startswith("de"):
        _LANG = "de"
    elif low.startswith("en"):
        _LANG = "en"
    else:
        _LANG = autodetect()


def autodetect() -> str:  # pragma: no cover - env-dependent
    """Return language code inferred from the OS locale."""
    lang = ""
    with suppress(Exception):
        lang = (locale.getlocale(_LC_MESSAGES)[0] or "").lower()
    if not lang:
        with suppress(Exception):
            lang = (locale.getdefaultlocale()[0] or "").lower()
    if isinstance(lang, str) and lang.startswith("de"):
        return "de"
    return "en"


def _load(lang: str) -> dict:
    if lang in _CACHE:
        return _CACHE[lang]
    filename = f"{lang}.json"
    try:
        data = json.loads(
            resources.files("pdf_toolbox.locales")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
    except Exception:  # pragma: no cover - defensive
        data = {"strings": {}, "labels": {}}
    _CACHE[lang] = data
    return data


def tr(key: str, **kwargs: Any) -> str:
    """Translate a UI string by key using current language."""
    lang = _LANG or autodetect()
    data = _load(lang)
    s = data.get("strings", {}).get(key, key)
    try:
        return s.format(**kwargs)
    except Exception:  # pragma: no cover - defensive
        return s


def label(name: str) -> str:
    """Translate a parameter/field label by its canonical name."""
    lang = _LANG or autodetect()
    data = _load(lang)
    return data.get("labels", {}).get(name, name)


__all__ = ["autodetect", "label", "set_language", "tr"]
