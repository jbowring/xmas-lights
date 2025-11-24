from typing import Any


# noinspection PyPep8Naming
class ws:
    WS2811_STRIP_RGB: int


class PixelStrip:
    num: int
    size: int

    def __init__(self, num: int, pin: int, *args: Any, **kwargs: Any) -> None: ...

    def begin(self) -> None: ...

    def show(self) -> None: ...

    # noinspection PyPep8Naming
    def setPixelColor(self, n: int, color: int) -> None: ...

    # noinspection PyPep8Naming
    def numPixels(self) -> int: ...

    def __setitem__(self, index: int, value: int) -> None: ...

    def __getitem__(self, index: int) -> int: ...


# noinspection PyPep8Naming
def Color(red: int, green: int, blue: int, white: int = 0) -> int: ...
