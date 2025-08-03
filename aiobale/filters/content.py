from typing import Any
from .base import Filter
from ..types import Message


class IsText(Filter):
    """
    Filter to check if the message contains text content.

    This filter returns True if the incoming event is a Message and has a non-empty text field.

    Examples:
        .. code:: python
        
            @router.message(IsText())
            async def handler(msg: Message):
                ...

    Returns:
        bool: True if the message has text, False otherwise.
    """

    async def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message):
            return False

        return event.text is not None


class IsDocument(Filter):
    """
    Filter to check if the message contains a document.

    This filter returns True if the incoming event is a Message and has a document attached.

    Examples:
        .. code:: python
            @router.message(IsDocument())
            async def handler(msg: Message):
                ...

    Returns:
        bool: True if the message has a document, False otherwise.
    """

    async def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message):
            return False

        return event.document is not None


class IsGift(Filter):
    """
    Filter to check if the message contains a gift packet.

    This filter returns True if the incoming event is a Message and has a gift field.

    Examples:
        .. code:: python
            @router.message(IsGift())
            async def handler(msg: Message):
                ...

    Returns:
        bool: True if the message has a gift, False otherwise.
    """

    async def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message):
            return False

        return event.gift is not None
