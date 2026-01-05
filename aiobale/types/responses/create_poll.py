from __future__ import annotations

from typing import TYPE_CHECKING
from pydantic import Field

from ..base import BaleObject


class CreatePollResponse(BaleObject):
    """
    Response object representing a newly created poll.

    This class encapsulates the unique identifier of a poll
    that has been successfully created in a chat.
    """

    poll_id: int = Field(..., alias="1")
    """The unique identifier of the created poll."""

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            poll_id: int,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(poll_id=poll_id, **__pydantic_kwargs)
