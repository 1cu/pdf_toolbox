"""Compatibility wrapper for :mod:`pdf_toolbox.builtin.images`."""

from pdf_toolbox.builtin.images import *  # noqa: F403

if __name__ == "__main__":  # pragma: no cover - CLI passthrough
    import runpy

    runpy.run_module("pdf_toolbox.builtin.images", run_name="__main__")
