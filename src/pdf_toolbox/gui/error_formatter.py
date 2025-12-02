"""Error message formatting for GUI display."""

from __future__ import annotations

from pdf_toolbox.i18n import tr
from pdf_toolbox.renderers.pptx import (
    PptxProviderUnavailableError,
    PptxRenderingError,
)

_PPTX_ERROR_KEYS_BY_CODE = {
    "backend_crashed": "pptx_backend_crashed",
    "conflicting_options": "pptx_conflicting_options",
    "corrupt": "pptx_corrupt",
    "empty_selection": "pptx_empty_selection",
    "invalid_range": "pptx_invalid_range",
    "permission_denied": "pptx_permission_denied",
    "resource_limits_exceeded": "pptx_resource_limits",
    "timeout": "pptx_timeout",
    "unavailable": "pptx_unavailable",
    "unsupported_option": "pptx_unsupported_option",
}


class ErrorFormatter:
    """Format error messages for user-friendly GUI display."""

    @staticmethod
    def format(error: object) -> str:
        """Return a translated, user-friendly message for ``error``."""
        if isinstance(error, BaseException):
            return ErrorFormatter._format_exception(error)
        return str(error)

    @staticmethod
    def _format_exception(error: BaseException) -> str:
        """Translate PPTX errors while preserving diagnostic detail."""
        if isinstance(error, PptxProviderUnavailableError):
            return tr("pptx.no_provider")
        if isinstance(error, PptxRenderingError):
            code = (error.code or "").lower()
            key = _PPTX_ERROR_KEYS_BY_CODE.get(code, "pptx_error_unknown")
            base = tr(key)
            extras: list[str] = []
            if error.detail:
                extras.append(str(error.detail))
            raw = str(error)
            if raw and raw.lower() != code and raw != base:
                extras.append(raw)
            filtered: list[str] = []
            for item in extras:
                if item and item not in filtered:
                    filtered.append(item)
            if filtered:
                return base + "\n" + "\n".join(filtered)
            return base
        return str(error)


__all__ = ["ErrorFormatter"]
