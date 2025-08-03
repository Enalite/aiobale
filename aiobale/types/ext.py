from pydantic import Field
from typing import Optional, TYPE_CHECKING

from .base import BaleObject


class ExtValue(BaleObject):
    """
    Represents the dynamic value part of an extended key-value structure.
    
    Some extended data fields in Bale can contain values of different types. 
    This class captures those possible types — either a string or a number.
    """

    string: Optional[str] = Field(None, alias="1")
    """A string representation of the value (if applicable)."""

    number: Optional[int] = Field(None, alias="4")
    """A numeric representation of the value (if applicable)."""

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            string: Optional[str] = None,
            number: Optional[int] = None,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(string=string, number=number, **__pydantic_kwargs)


class ExtData(BaleObject):
    """
    Represents an extended data entry with a name and a typed value.

    Used for attaching extra metadata to objects (such as messages or peers) in Bale, 
    where each piece of metadata has a name and a flexible typed value (string or number).
    """

    name: str = Field(..., alias="1")
    """The name or key of the metadata field (e.g., 'sender_type', 'priority')."""

    value: ExtValue = Field(..., alias="2")
    """The value of the metadata field, which may be a string or a number."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            name: str,
            value: ExtValue,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(name=name, value=value, **__pydantic_kwargs)


class ExtKeyValue(BaleObject):
    """
    Represents a simple key-value pair used for basic metadata.

    Unlike `ExtData`, both key and value here are always strings. 
    This structure is often used for headers, tags, or lightweight extensions 
    where typed values are not needed.
    """

    key: str = Field(..., alias="1")
    """The key or identifier of the metadata entry (e.g., 'client', 'version')."""

    value: str = Field("", alias="2")
    """The string value associated with the key."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            key: str,
            value: str = "",
            **__pydantic_kwargs
        ) -> None:
            super().__init__(key=key, value=value, **__pydantic_kwargs)
