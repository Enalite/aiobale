from __future__ import annotations

from pydantic import Field, model_validator
from typing import TYPE_CHECKING, Any, Dict, List

from ..utils import decode_list
from .base import BaleObject


class Reaction(BaleObject):
    """
    Represents a reaction on a Bale message or entity.

    This class stores information about which users reacted,
    the emoji used, and the count of reactions.

    Fields correspond to the raw data keys using aliases for parsing
    from Bale's internal protocol.

    The `users` field contains a list of user IDs who reacted.
    The `emojy` field stores the emoji string representing the reaction.
    The `count` field indicates how many times this reaction was made.

    The validator decodes user IDs from a varint-encoded format
    and extracts the count from a nested structure.
    """

    users: List[int] = Field(default_factory=list, alias="1")
    """List of user IDs who applied this reaction.

    These IDs are varint-encoded in the raw data and decoded during validation.
    """

    emojy: str = Field(..., alias="2")
    """The emoji character(s) representing the reaction (e.g., "👍", "❤️")."""

    count: int = Field(..., alias="3")
    """Total number of times this reaction was made.

    Extracted from nested structure in raw data.
    """

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-process incoming raw data before model instantiation.

        Decodes the varint-encoded user list and extracts the count
        from the nested structure.

        Args:
            data (Dict[str, Any]): Raw input dictionary with keys as strings.

        Returns:
            Dict[str, Any]: Cleaned dictionary with decoded and extracted values.
        """
        if "1" in data:
            # Decode varint-encoded list of user IDs
            data["1"] = decode_list(data["1"])

        # Extract integer count from nested dict structure
        data["3"] = data["3"]["1"]

        return data

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            users: List[int] = [],
            emojy: str,
            count: int,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(users=users, emojy=emojy, count=count, **__pydantic_kwargs)
