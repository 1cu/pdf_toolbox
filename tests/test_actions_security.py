from __future__ import annotations

import pytest

from pdf_toolbox import actions


def test_register_module_rejects_foreign():
    with pytest.raises(ValueError):
        actions._register_module("json")
