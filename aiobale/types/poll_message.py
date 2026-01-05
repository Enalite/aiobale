from typing import List, TYPE_CHECKING
from pydantic import Field

from ..enums import PollType
from .base import BaleObject
from .poll_option import PollOption


class PollMessage(BaleObject):
    """
    Represents a poll message in a chat.

    This class encapsulates all the information needed to create
    or display a poll, including the question, options, settings,
    and poll metadata.
    """

    question: str = Field(..., alias="1")
    """The question or topic of the poll."""

    options: List[PollOption] = Field(..., alias="2")
    """The available choices for the poll participants."""

    is_anonymous: bool = Field(True, alias="3")
    """
    Whether the poll is anonymous.
    If True, voter identities are hidden; if False, voters are visible.
    """

    type: PollType = Field(..., alias="4")
    """The type of the poll (e.g., single-choice or multiple-choice)."""

    if TYPE_CHECKING:
        # This __init__ is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            question: str,
            options: List[PollOption],
            type: PollType,
            is_anonymous: bool = True,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(
                question=question,
                options=options,
                is_anonymous=is_anonymous,
                type=type,
                **__pydantic_kwargs
            )
