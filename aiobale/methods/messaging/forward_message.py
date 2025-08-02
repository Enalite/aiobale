from pydantic import Field
from typing import TYPE_CHECKING, Any, List

from ...types import Peer, InfoMessage
from ...types.responses import DefaultResponse
from ...enums import Services
from ..base import BaleMethod


class ForwardMessages(BaleMethod):
    """
    Forwards messages from one peer to another.

    Returns:
        aiobale.types.responses.DefaultResponse: The response indicating the success or failure of the operation.
    """

    __service__ = Services.MESSAGING.value
    __method__ = "ForwardMessages"

    __returning__ = DefaultResponse

    peer: Peer = Field(..., alias="1")
    """
    The target peer (chat or user) to which the messages are being forwarded.
    """

    message_ids: List[int] = Field(..., alias="2")
    """
    Encoded list of message identifiers that are being forwarded.
    """

    forwarded_messages: List[InfoMessage] = Field(..., alias="3")
    """
    List of detailed information about the forwarded messages.
    """

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            peer: Peer,
            message_ids: List[int],
            forwarded_messages: List[InfoMessage],
            **__pydantic_kwargs: Any
        ) -> None:
            super().__init__(
                peer=peer,
                message_ids=message_ids,
                forwarded_messages=forwarded_messages,
                **__pydantic_kwargs
            )
