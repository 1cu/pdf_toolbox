"""Builtin action modules for pdf_toolbox.

Importing this package ensures that all builtin action modules are loaded and
registered. Some execution environments (notably macOS on CI or frozen
executables) do not allow :func:`pkgutil.walk_packages` to enumerate modules
inside the package.  Eagerly importing the known module list guarantees that
``pdf_toolbox.actions`` sees every builtin action even when discovery fails.
"""

from contextlib import suppress
from importlib import import_module

__all__ = [
    "docx",
    "extract",
    "images",
    "optimise",
    "repair",
    "unlock",
]

for _name in __all__:
    with suppress(Exception):  # pragma: no cover - optional dependencies
        import_module(f"{__name__}.{_name}")
