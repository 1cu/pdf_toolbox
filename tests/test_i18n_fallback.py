from __future__ import annotations

from pdf_toolbox import i18n


def test_unknown_language_falls_back(monkeypatch):
    monkeypatch.setattr(i18n, "autodetect", lambda: "en")
    i18n.set_language("es_ES")
    try:
        assert i18n.tr("about") == "About"
    finally:
        i18n.set_language("en")
