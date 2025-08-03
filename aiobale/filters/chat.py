from typing import Any

from .base import Filter
from ..types import Message
from ..enums import ChatType


class IsGroupOrChannel(Filter):
    def __init__(self):
        pass

    async def __call__(self, event: Any) -> bool:
        # Check if the event is a Message instance
        if not isinstance(event, Message):
            return False

        return event.chat.type in (
            ChatType.GROUP,
            ChatType.SUPRER_GROUP,
            ChatType.CHANNEL,
        )


class IsPrivate(Filter):
    def __init__(self):
        pass

    async def __call__(self, event: Any) -> bool:
        # Check if the event is a Message instance
        if not isinstance(event, Message):
            return False

        return event.chat.type in (
            ChatType.PRIVATE,
            ChatType.BOT
        )


class ChatTypeFilter(Filter):
    def __init__(self, chat_type: ChatType):
        self.chat_type = chat_type

    async def __call__(self, event: Any) -> bool:
        # Check if the event is a Message instance
        if not isinstance(event, Message):
            return False

        return event.chat.type == self.chat_type
