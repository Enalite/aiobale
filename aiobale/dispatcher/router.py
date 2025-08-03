from collections import defaultdict
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Union,
    Type,
)

from .event.handler import Handler, FilterObject, CallbackType
from .event.observer import EventObserver


class Router:
    """
    A class for managing and dispatching event handlers based on event types.
    The `Router` class provides a mechanism to register, organize, and execute
    handlers for various event types. It allows developers to define custom
    event types and associate them with specific callback functions. This is
    particularly useful in event-driven architectures where different parts of
    the system need to respond to specific events.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self.name: str = name or hex(id(self))
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)
        self._observer = EventObserver()

        self._register_default_event_types()

        self.message = self._observer.get_decorator("message")
        self.message_deleted = self._observer.get_decorator("message_deleted")
        self.chat_deleted = self._observer.get_decorator("chat_deleted")
        self.chat_cleared = self._observer.get_decorator("chat_cleared")
        self.username_changed = self._observer.get_decorator("username_changed")
        self.message_sent = self._observer.get_decorator("message_sent")
        self.message_edited = self._observer.get_decorator("message_edited")
        self.about_changed = self._observer.get_decorator("about_changed")
        self.user_blocked = self._observer.get_decorator("user_blocked")
        self.user_unblocked = self._observer.get_decorator("user_unblocked")
        self.group_message_pinned = self._observer.get_decorator("group_message_pinned")
        self.group_pin_removed = self._observer.get_decorator("group_pin_removed")

    def _register_default_event_types(self) -> None:
        for event_type in (
            "message",
            "message_deleted",
            "chat_cleared",
            "chat_deleted",
            "username_changed",
            "message_sent",
            "message_edited",
            "about_changed",
            "user_blocked",
            "user_unblocked",
            "group_message_pinned",
            "group_pin_removed",
        ):
            self._observer.register(event_type, self._make_event_decorator(event_type))

    def _make_event_decorator(
        self, event_type: str
    ) -> Callable[..., Callable[..., Coroutine[Any, Any, Any]]]:
        def decorator(*filters: Callable[..., Union[bool, Awaitable[bool]]]):
            return self.register(event_type, *filters)

        return decorator

    def add_event_type(self, event_type: str) -> None:
        self._observer.register(event_type, self._make_event_decorator(event_type))

    def register(
        self,
        event_type: str,
        *filters: CallbackType,
    ) -> Callable[[CallbackType], CallbackType]:
        def decorator(func: CallbackType) -> CallbackType:
            handler = Handler(
                event_type=event_type,
                callback=func,
                filters=[FilterObject(filter_) for filter_ in filters],
            )
            self._handlers[event_type].append(handler)
            return func

        return decorator

    def get_handlers(self, event_type: str) -> List[Handler]:
        return self._handlers.get(event_type, [])

    def available_event_types(self) -> List[str]:
        return list(self._handlers.keys())

    def all_handlers(self) -> Dict[str, List[Handler]]:
        return self._handlers

    def handler_count(self) -> int:
        return sum(len(handlers) for handlers in self._handlers.values())
