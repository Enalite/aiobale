from pydantic import Field, model_validator
from typing import TYPE_CHECKING, Any, Dict, List

from ...types import Peer, IntValue, IntListValue
from ...types.responses import DefaultResponse
from ...enums import Services
from ..base import BaleMethod


class DeleteMessage(BaleMethod):
    """
    Deletes specified messages from a chat or user.

    Returns:
        aiobale.types.responses.DefaultResponse: The response indicating the success or failure of the operation.
    """

    __service__ = Services.MESSAGING.value
    __method__ = "DeleteMessage"

    __returning__ = DefaultResponse

    peer: Peer = Field(..., alias="1")
    """
    The peer (chat or user) from which the messages are being deleted.
    """

    message_ids: List[int] = Field(..., alias="2")
    """
    Encoded list of message identifiers to be deleted.
    """

    dates: IntListValue = Field(..., alias="3")
    """
    Encoded list of timestamps corresponding to the messages being deleted.
    """

    just_me: IntValue = Field(..., alias="4")
    """
    Indicates whether the deletion is only for the current user (1 for true, 0 for false).
    """

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            peer: Peer,
            message_ids: List[int],
            dates: List[int],
            just_me: IntValue,
            **__pydantic_kwargs: Any
        ) -> None:
            super().__init__(
                peer=peer,
                message_ids=message_ids,
                dates=dates,
                just_me=just_me,
                **__pydantic_kwargs
            )

    @model_validator(mode="before")
    @classmethod
    def _fix_lists(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if "dates" in data:
            data["dates"] = IntListValue(value=data["dates"])

        return data
