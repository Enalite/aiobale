import asyncio
import contextvars
from functools import partial
import inspect
from dataclasses import dataclass, field
from magic_filter.magic import MagicFilter as OriginalMagicFilter
from typing import Awaitable, Callable, Optional, Any, List, ParamSpec, TypeVar, Union

from ...filters.base import Filter
from ...utils.magic_filter import MagicFilter

P = ParamSpec('P')
R = TypeVar('R')

CallbackType = Callable[P, Union[R, Awaitable[R]]]


@dataclass
class CallableObject:
    callback: CallbackType
    awaitable: bool = field(init=False)

    def __post_init__(self) -> None:
        callback = inspect.unwrap(self.callback)
        self.awaitable = inspect.isawaitable(callback) or inspect.iscoroutinefunction(
            callback
        )

    async def call(self, *args: Any, **kwargs: Any) -> Any:
        wrapped = partial(self.callback, *args, **kwargs)
        if self.awaitable:
            return await wrapped()

        loop = asyncio.get_event_loop()
        context = contextvars.copy_context()
        wrapped = partial(context.run, wrapped)
        return await loop.run_in_executor(None, wrapped)


@dataclass
class FilterObject(CallableObject):
    magic: Optional[MagicFilter] = None

    def __post_init__(self) -> None:
        if isinstance(self.callback, OriginalMagicFilter):
            # MagicFilter instance is callable but generates
            # only "CallOperation" instead of applying the filter
            self.magic = self.callback
            self.callback = self.callback.resolve

        super(FilterObject, self).__post_init__()

        if isinstance(self.callback, Filter):
            self.awaitable = True


@dataclass
class Handler(CallableObject):
    """
    A class that represents an event handler with associated filters and a callback.
    """

    event_type: str
    filters: Optional[List[FilterObject]] = None

    async def check(self, *args: Any, **kwargs: Any) -> bool:
        if not self.filters:
            return True
        for event_filter in self.filters:
            check = await event_filter.call(*args, **kwargs)
            if not check:
                return False
        return True
