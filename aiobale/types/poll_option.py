from typing import TYPE_CHECKING
from pydantic import Field

from .base import BaleObject


class PollOption(BaleObject):
    """
    Represents a single option in a poll.

    This class encapsulates the information for one choice
    available to participants in a poll.
    """

    id: int = Field(..., alias="1")
    """The unique identifier of the poll option."""

    text: str = Field(..., alias="2")
    """The display text of the option."""

    if TYPE_CHECKING:
        # This __init__ is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            id: int,
            text: str,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(
                id=id,
                text=text,
                **__pydantic_kwargs
            )
