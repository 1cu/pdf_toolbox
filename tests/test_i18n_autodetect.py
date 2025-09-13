from __future__ import annotations

from pdf_toolbox import i18n


def test_set_language_none_autodetect(monkeypatch):
    monkeypatch.setattr(i18n.locale, "getlocale", lambda *_, **__: ("de_DE", "UTF-8"))
    monkeypatch.setattr(
        i18n.locale, "getdefaultlocale", lambda *_, **__: ("de_DE", "UTF-8")
    )
    i18n.set_language(None)
    try:
        assert i18n.tr("about") == "Über"
        assert i18n.label("input_pdf") == "Eingabe PDF"
    finally:
        i18n.set_language("en")
