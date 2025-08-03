import re
from typing import Pattern, Union, Any

from .base import Filter
from ..types import Message


class RegexFilter(Filter):
    """
    Filter that matches message texts against a regular expression (regex) pattern.

    Args:
        pattern (str | Pattern[str]): The regex pattern to match. Can be a string or a compiled regex.

    Example:
        .. code:: python
        
            @router.message(RegexFilter(r"hello (\\w+)"))
            async def greet_user(msg: Message):
                ...
    """
    def __init__(self, pattern: Union[str, Pattern[str]]):
        if isinstance(pattern, str):
            self.pattern = re.compile(pattern)
        else:
            self.pattern = pattern

    async def __call__(self, event: Any) -> bool:
        """
        Checks if the given event's text matches the regex pattern.

        Args:
            event (Any): The event to be checked. Expected to be a Message instance.

        Returns:
            bool: True if the message text matches the pattern, False otherwise.
        """
        if not isinstance(event, Message):
            return False

        text = event.text or ""
        return bool(self.pattern.search(text))
