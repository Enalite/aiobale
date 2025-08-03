import re
from typing import Pattern, Union, Any

from .base import Filter
from ..types import Message


class RegexFilter(Filter):
    def __init__(self, pattern: Union[str, Pattern[str]]):
        if isinstance(pattern, str):
            self.pattern = re.compile(pattern)
        else:
            self.pattern = pattern

    async def __call__(self, event: Any) -> bool:
        # Check if the event is a Message instance
        if not isinstance(event, Message):
            return False

        text = event.text or ""
        return bool(self.pattern.search(text))
