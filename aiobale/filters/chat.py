from typing import Any
from .base import Filter
from ..types import Message
from ..enums import ChatType


class IsGroupOrChannel(Filter):
    """
    Filter to check if the message is from a group or channel chat.

    This filter returns True if the incoming event is a Message and its chat type is
    GROUP, SUPER_GROUP, or CHANNEL.

    Examples:
        .. code:: python
        
            @router.message(IsGroupOrChannel())
            async def handler(msg: Message):
                ...

    Returns:
        bool: True if chat type is group or channel, False otherwise.
    """

    async def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message):
            return False

        return event.chat.type in (
            ChatType.GROUP,
            ChatType.SUPER_GROUP,
            ChatType.CHANNEL,
        )


class IsPrivate(Filter):
    """
    Filter to check if the message is from a private chat.

    This filter returns True if the incoming event is a Message and its chat type is
    PRIVATE or BOT.

    Examples:
        .. code:: python
        
            @router.message(IsPrivate())
            async def handler(msg: Message):
                ...

    Returns:
        bool: True if chat type is private or bot, False otherwise.
    """

    async def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message):
            return False

        return event.chat.type in (
            ChatType.PRIVATE,
            ChatType.BOT,
        )


class ChatTypeFilter(Filter):
    """
    Filter to match messages from a specific chat type.

    Args:
        chat_type (ChatType): The chat type to match (e.g., ChatType.GROUP).

    Examples:
        .. code:: python
        
            @router.message(ChatTypeFilter(ChatType.CHANNEL))
            async def handler(msg: Message):
                ...

    Returns:
        bool: True if the chat type matches the given type, False otherwise.
    """

    def __init__(self, chat_type: ChatType):
        self.chat_type = chat_type

    async def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message):
            return False

        return event.chat.type == self.chat_type
