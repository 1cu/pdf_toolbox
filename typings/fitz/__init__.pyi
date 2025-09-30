from __future__ import annotations

from collections.abc import Mapping, Sequence
from os import PathLike
from types import TracebackType
from typing import Any, overload

class Matrix:
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self, other: Matrix, /) -> None: ...
    @overload
    def __init__(self, components: Sequence[float], /) -> None: ...
    @overload
    def __init__(self, angle: float, /) -> None: ...
    @overload
    def __init__(self, zoom_x: float, zoom_y: float, /) -> None: ...
    @overload
    def __init__(self, shear_x: float, shear_y: float, scale: float, /) -> None: ...
    @overload
    def __init__(
        self,
        a: float,
        b: float,
        c: float,
        d: float,
        e: float,
        f: float,
        /,
    ) -> None: ...  # pdf-toolbox: PyMuPDF signature requires six components | issue:-

class Rect:
    width: float
    height: float

    def __init__(
        self,
        x0: float = ...,
        y0: float = ...,
        x1: float = ...,
        y1: float = ...,
    ) -> None: ...

class Colorspace:
    n: int

csRGB: Colorspace  # noqa: N816  # pdf-toolbox: preserve PyMuPDF constant casing | issue:-

class Pixmap:
    width: int
    height: int
    alpha: int
    samples: bytes
    colorspace: Colorspace | None

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class Page:
    rect: Rect
    number: int

    def get_pixmap(
        self, matrix: Matrix | None = ..., alpha: bool = ..., **kwargs: Any
    ) -> Pixmap: ...
    def get_svg_image(self, matrix: Matrix | None = ..., **kwargs: Any) -> str: ...
    def get_images(self, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]: ...
    def get_drawings(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]: ...
    def get_text(self, option: str = ..., *args: Any, **kwargs: Any) -> str: ...
    def insert_text(self, position: tuple[float, float], text: str, **kwargs: Any) -> None: ...
    def insert_image(
        self,
        rect: Rect,
        *,
        filename: str | None = ...,
        stream: bytes | None = ...,
        **kwargs: Any,
    ) -> None: ...

class Document:
    page_count: int
    metadata: dict[str, Any] | None
    needs_pass: bool
    name: str

    def __enter__(self) -> Document: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    def close(self) -> None: ...
    def save(self, filename: str | PathLike[str], **kwargs: Any) -> None: ...
    def insert_pdf(
        self,
        doc: Document,
        *,
        from_page: int | None = ...,
        to_page: int | None = ...,
        **kwargs: Any,
    ) -> None: ...
    def set_metadata(self, metadata: Mapping[str, Any]) -> None: ...
    def authenticate(self, password: str) -> bool: ...
    def load_page(self, index: int) -> Page: ...
    def new_page(self, *args: Any, **kwargs: Any) -> Page: ...

PDF_ENCRYPT_NONE: int
PDF_ENCRYPT_AES_256: int

def open(*args: Any, **kwargs: Any) -> Document: ...  # noqa: A001  # pdf-toolbox: stub matches PyMuPDF API | issue:-
def configure_zapf_dingbats(check: bool) -> None: ...
def Touch(  # noqa: N802  # pdf-toolbox: upstream camelCase API | issue:-
    doc: Document,
    *,
    warnings: bool = ...,
) -> None: ...
