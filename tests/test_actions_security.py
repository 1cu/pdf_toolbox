from __future__ import annotations

import pytest

from pdf_toolbox import actions


def test_register_module_rejects_foreign():
    msg = "module outside allowed packages"
    with pytest.raises(ValueError, match=msg):
        actions._register_module("json")
