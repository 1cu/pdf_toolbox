"""PDF toolbox package providing various PDF utilities."""

import sys

sys.set_int_max_str_digits(0)

from pdf_toolbox.utils import (
    configure_logging,
    ensure_libs,
    logger,
    parse_page_spec,
    sane_output_dir,
    update_metadata,
)

__all__ = [
    "configure_logging",
    "ensure_libs",
    "logger",
    "parse_page_spec",
    "sane_output_dir",
    "update_metadata",
]
