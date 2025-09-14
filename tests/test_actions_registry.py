from __future__ import annotations

import sys

from pdf_toolbox import actions


def test_only_decorated_actions_listed(tmp_path, monkeypatch):
    mod_path = tmp_path / "dummy_mod.py"
    mod_path.write_text(
        """
from pdf_toolbox.actions import action

@action()
def public():
    return 1

def helper():
    return 2
"""
    )
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.setattr(actions, "_registry", {}, raising=False)
    monkeypatch.setattr(actions, "_auto_discover", lambda: None)
    sys.modules.pop("dummy_mod", None)
    __import__("dummy_mod")
    listed = {a.fqname for a in actions.list_actions()}
    assert "dummy_mod.public" in listed
    assert "dummy_mod.helper" not in listed


def test_hidden_actions_not_listed(tmp_path, monkeypatch):
    mod_path = tmp_path / "dummy_hidden.py"
    mod_path.write_text(
        """
from pdf_toolbox.actions import action

@action(visible=False)
def hidden():
    return 3
"""
    )
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.setattr(actions, "_registry", {}, raising=False)
    monkeypatch.setattr(actions, "_auto_discover", lambda: None)
    sys.modules.pop("dummy_hidden", None)
    __import__("dummy_hidden")
    listed = {a.fqname for a in actions.list_actions()}
    assert "dummy_hidden.hidden" not in listed
