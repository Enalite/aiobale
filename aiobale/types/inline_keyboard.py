from typing import List, Optional, TYPE_CHECKING
from pydantic import Field, model_serializer, model_validator

from .base import BaleObject


class InlineKeyboardButton(BaleObject):
    """
    Represents a button within an inline keyboard.
    """

    text: str = Field(..., alias="1")
    """Label text displayed on the button."""

    url: Optional[str] = Field(None, alias="2")
    """URL to be opened when the button is pressed."""

    callback_data: Optional[str] = Field(None, alias="3")
    """Data sent back to the bot when the button is pressed."""

    copy_text: Optional[str] = Field(None, alias="9")
    """Text to be copied to the clipboard when the button is pressed."""

    if TYPE_CHECKING:
        # This __init__ is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            text: str,
            url: Optional[str] = None,
            callback_data: Optional[str] = None,
            copy_text: Optional[str] = None,
            **__pydantic_kwargs,
        ) -> None:
            super().__init__(
                text=text,
                url=url,
                callback_data=callback_data,
                copy_text=copy_text,
                **__pydantic_kwargs,
            )

    @model_validator(mode="before")
    @classmethod
    def validate_keyboard(cls, data):
        """
        Extracts nested field values from the serialized form
        into the expected flat model structure before validation.
        """
        if isinstance(data, dict) and "1" in data:
            for i in ("2", "3", "9"):
                if i not in data:
                    continue
                val = data[i]
                # Optional scalars arrive wrapped as {"1": value}; an absent one
                # arrives as {}. Unwrap to the value (or None), or keep as-is if
                # already unwrapped.
                if isinstance(val, dict):
                    data[i] = val.get("1")
        return data

    @model_serializer(mode="wrap")
    def ser(self, nxt, info):
        """
        Serializes the model into the API's nested alias structure.
        """
        if not info.by_alias:
            return nxt(self)

        out = nxt(self)
        for i in ("2", "3", "9"):
            if i not in out:
                continue
            out[i] = {"1": out[i]}
        return out


class InlineKeyboardMarkup(BaleObject):
    """
    Represents the entire inline keyboard layout for a message.
    """

    inline_keyboard: List[List[InlineKeyboardButton]] = Field(
        default_factory=list, alias="1"
    )
    """Two-dimensional array of inline keyboard button rows."""

    if TYPE_CHECKING:
        # This __init__ is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            inline_keyboard: List[List[InlineKeyboardButton]],
            **__pydantic_kwargs,
        ) -> None:
            super().__init__(inline_keyboard=inline_keyboard, **__pydantic_kwargs)

    @model_validator(mode="before")
    @classmethod
    def validate_keyboard(cls, data):
        """
        Converts the raw serialized button structure from the API
        into a list of InlineKeyboardButton rows before validation.
        """
        if isinstance(data, dict) and "1" in data and isinstance(data["1"], (list, dict)):
            raw = data["1"]
            # A single row may arrive as a dict instead of a one-element list.
            raw_buttons = raw if isinstance(raw, list) else [raw]

            keyboard_rows = []
            for row in raw_buttons:
                if isinstance(row, dict) and "1" in row:
                    buttons = row["1"]
                    # A row may hold a single button (dict) or several buttons (list).
                    if isinstance(buttons, list):
                        btns = [InlineKeyboardButton.model_validate(b) for b in buttons]
                    else:
                        btns = [InlineKeyboardButton.model_validate(buttons)]
                    keyboard_rows.append(btns)
                else:
                    pass

            return {"1": keyboard_rows}
        return data

    @model_serializer(mode="wrap")
    def ser(self, nxt, info):
        """
        Serializes the inline keyboard into the API's nested alias structure.
        """
        if not info.by_alias:
            return nxt(self)

        out = []
        for row in self.inline_keyboard:
            buttons_serialized = [
                btn.model_dump(by_alias=True, exclude_none=True) for btn in row
            ]
            out.append({"1": buttons_serialized})
        return {"1": out}
