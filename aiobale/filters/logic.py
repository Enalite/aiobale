from abc import ABC
from typing import TYPE_CHECKING, Any, Callable, Dict, Union

from .base import Filter

if TYPE_CHECKING:
    from ..dispatcher.event.handler import FilterObject

CallbackType = Callable[..., Any]


class _LogicFilter(Filter, ABC):
    """
    Abstract base class for logical filter combinators.

    All logical filter types (AND, OR, NOT) inherit from this class.
    """
    pass


class _InvertFilter(_LogicFilter):
    """
    Inverts the result of a filter (logical NOT).

    Args:
        target (FilterObject): The filter to invert.

    Examples:
        .. code:: python
        
            @router.message(invert_f(IsText()))
            async def handle_non_text(msg: Message):
                ...
    """

    __slots__ = ("target",)

    def __init__(self, target: "FilterObject") -> None:
        self.target = target

    async def __call__(self, *args: Any, **kwargs: Any) -> Union[bool, Dict[str, Any]]:
        return not bool(await self.target.call(*args, **kwargs))


class _AndFilter(_LogicFilter):
    """
    Combines multiple filters using logical AND.

    Returns True only if all filters return True.
    If any filter returns a dict, all dicts are merged into the final result.

    Args:
        *targets (FilterObject): Filters to combine.

    Examples:
        .. code:: python
        
            @router.message(and_f(IsText(), IsDocument()))
            async def handle_text_document(msg: Message):
                ...
    """

    __slots__ = ("targets",)

    def __init__(self, *targets: "FilterObject") -> None:
        self.targets = targets

    async def __call__(self, *args: Any, **kwargs: Any) -> Union[bool, Dict[str, Any]]:
        final_result = {}

        for target in self.targets:
            result = await target.call(*args, **kwargs)
            if not result:
                return False
            if isinstance(result, dict):
                final_result.update(result)

        if final_result:
            return final_result
        return True


class _OrFilter(_LogicFilter):
    """
    Combines multiple filters using logical OR.

    Returns True if any of the filters return True.
    If any filter returns a dict, it will be immediately returned.

    Args:
        *targets (FilterObject): Filters to combine.

    Examples:
        .. code:: python
        
            @router.message(or_f(IsGift(), IsDocument()))
            async def handle_gift_or_document(msg: Message):
                ...
    """

    __slots__ = ("targets",)

    def __init__(self, *targets: "FilterObject") -> None:
        self.targets = targets

    async def __call__(self, *args: Any, **kwargs: Any) -> Union[bool, Dict[str, Any]]:
        for target in self.targets:
            result = await target.call(*args, **kwargs)
            if not result:
                continue
            if isinstance(result, dict):
                return result
            return bool(result)
        return False


def and_f(*targets: CallbackType) -> _AndFilter:
    """
    Helper to combine filters with logical AND.

    Args:
        *targets (CallbackType): Callable filters to combine.

    Returns:
        _AndFilter: A combined filter object.
    """
    from ..dispatcher.event.handler import FilterObject

    return _AndFilter(*(FilterObject(target) for target in targets))


def or_f(*targets: CallbackType) -> _OrFilter:
    """
    Helper to combine filters with logical OR.

    Args:
        *targets (CallbackType): Callable filters to combine.

    Returns:
        _OrFilter: A combined filter object.
    """
    from ..dispatcher.event.handler import FilterObject

    return _OrFilter(*(FilterObject(target) for target in targets))


def invert_f(target: CallbackType) -> _InvertFilter:
    """
    Helper to invert a filter's result (logical NOT).

    Args:
        target (CallbackType): Callable filter to invert.

    Returns:
        _InvertFilter: An inverted filter object.
    """
    from ..dispatcher.event.handler import FilterObject

    return _InvertFilter(FilterObject(target))
