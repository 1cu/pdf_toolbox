"""PDF toolbox package providing various PDF utilities."""

import sys

sys.set_int_max_str_digits(0)

from pdf_toolbox.utils import (
    ensure_libs,
    parse_page_spec,
    sane_output_dir,
    update_metadata,
)

__all__ = ["ensure_libs", "parse_page_spec", "sane_output_dir", "update_metadata"]
