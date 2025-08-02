from pydantic import Field, model_validator
from typing import List, TYPE_CHECKING

from .base import BaleObject
from .peer import Peer
from ..utils import decode_list


class SelectedMessages(BaleObject):
    """
    Represents a selection of messages for a specific peer (chat or user).

    Attributes:
    - `peer`: identifies the chat or user these messages belong to.
    - `ids`: list of message IDs, decoded as 64-bit varints.
    - `dates`: list of message dates corresponding to each ID, represented as millisecond timestamps,
       also decoded from a nested varint structure.

    The `fix_fields` validator handles decoding the raw varint-encoded lists received from Bale.
    """

    peer: Peer = Field(..., alias="1")
    """The peer (chat or user) from which the messages are selected."""

    ids: List[int] = Field(..., alias="2")
    """List of message IDs, decoded as 64-bit varints."""

    dates: List[int] = Field(..., alias="3")
    """Corresponding list of message timestamps in milliseconds, decoded from nested varints."""

    @model_validator(mode="before")
    @classmethod
    def fix_fields(cls, data: dict) -> dict:
        """
        Pre-processes incoming raw data to decode message IDs and dates.

        - Decodes field "2" (message IDs) from a list of 64-bit varints.
        - Decodes nested field "3" (dates) from a nested varint list under key "1".
        """
        data["2"] = decode_list(data["2"]) if "2" in data else []
        data["3"] = decode_list(data["3"]["1"]) if "3" in data else []
        return data

    if TYPE_CHECKING:

        def __init__(
            __pydantic__self__,
            *,
            peer: Peer,
            ids: List[int],
            dates: List[int],
            **__pydantic_kwargs,
        ) -> None:
            super().__init__(peer=peer, ids=ids, dates=dates, **__pydantic_kwargs)
