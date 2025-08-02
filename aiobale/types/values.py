from pydantic import Field
from typing import TYPE_CHECKING, List

from .base import BaleObject
from .int_bool import IntBool


class StringValue(BaleObject):
    """
    Wrapper class for a string value.

    This is used to represent string data with a consistent structure,
    potentially allowing for extension or metadata in the future.
    """

    value: str = Field(..., alias="1")
    """The wrapped string value."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            value: str,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(value=value, **__pydantic_kwargs)


class IntValue(BaleObject):
    """
    Wrapper class for an integer value.

    Provides a consistent container for integer fields in the protocol.
    """

    value: int = Field(..., alias="1")
    """The wrapped integer value."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            value: int,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(value=value, **__pydantic_kwargs)


class BoolValue(BaleObject):
    """
    Wrapper class for a boolean value represented via `IntBool`.

    This ensures booleans are handled consistently as integers (0/1).
    """

    value: IntBool = Field(..., alias="1")
    """The wrapped boolean value as an integer (0 or 1)."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            value: IntBool,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(value=value, **__pydantic_kwargs)


class BytesValue(BaleObject):
    """
    Wrapper class for bytes data.

    Useful for handling raw binary data with a consistent interface.
    """

    value: bytes = Field(..., alias="1")
    """The wrapped bytes value."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            value: bytes,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(value=value, **__pydantic_kwargs)


class IntListValue(BaleObject):
    """
    Wrapper class for list data.
    """

    value: List[int] = Field(..., alias="1")
    """The wrapped int values."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            value: List[int],
            **__pydantic_kwargs
        ) -> None:
            super().__init__(value=value, **__pydantic_kwargs)
