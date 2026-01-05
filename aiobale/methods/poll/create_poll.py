from pydantic import Field
from typing import Any, TYPE_CHECKING

from ...types import Peer, PollMessage
from ...types.responses import DefaultResponse
from ...enums import Services
from ..base import BaleMethod


class CreatePoll(BaleMethod):
    """
    Creates a new poll in a chat.

    Returns:
        aiobale.types.responses.DefaultResponse: The response containing the created poll ID and status.
    """

    __service__ = Services.POLL.value
    __method__ = "CreatePoll"

    __returning__ = DefaultResponse

    poll: PollMessage = Field(..., alias="1")
    """
    The poll containing the question, options, and settings.
    """

    peer: Peer = Field(..., alias="3")
    """
    The peer (chat or user) where the poll will be created.
    """

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            poll: PollMessage,
            peer: Peer,
            **__pydantic_kwargs: Any
        ) -> None:
            super().__init__(
                poll=poll,
                peer=peer,
                **__pydantic_kwargs
            )
