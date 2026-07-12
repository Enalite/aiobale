from functools import cached_property
from typing import Any, Optional, Tuple, TYPE_CHECKING
from pydantic import Field

from .base import BaleObject
from .message import Message
from .selected_messages import SelectedMessages
from .chat_data import ChatData
from .info_changed import UsernameChanged, AboutChanged
from .info_message import InfoMessage
from .updated_message import UpdatedMessage
from .block_updates import UserBlocked, UserUnblocked
from .message_updates import GroupPinRemoved, GroupMessagePinned


class Update(BaleObject):
    """
    Represents an update event received from the Bale server.

    Each update corresponds to a different kind of event such as a new message,
    message deletion, user info change, or group event.
    Only one field is expected to be populated per update instance, indicating
    the specific event type.
    """

    message_sent: Optional[InfoMessage] = Field(None, alias="4")
    """A new informational message was sent."""

    message_deleted: Optional[SelectedMessages] = Field(None, alias="46")
    """Messages that were deleted."""

    chat_cleared: Optional[ChatData] = Field(None, alias="47")
    """Notification that a chat has been cleared (all messages removed)."""

    chat_deleted: Optional[ChatData] = Field(None, alias="48")
    """Notification that a chat has been deleted."""

    message: Optional[Message] = Field(None, alias="55")
    """A new message has been received."""

    message_edited: Optional[UpdatedMessage] = Field(None, alias="162")
    """A previously sent message was edited."""

    username_changed: Optional[UsernameChanged] = Field(None, alias="209")
    """The user's username has changed."""

    about_changed: Optional[AboutChanged] = Field(None, alias="210")
    """The user's 'about' (status) information has changed."""

    group_message_pinned: Optional[GroupMessagePinned] = Field(None, alias="721")
    """A message in a group was pinned."""

    group_pin_removed: Optional[GroupPinRemoved] = Field(None, alias="722")
    """A pinned message in a group was removed."""

    user_blocked: Optional[UserBlocked] = Field(None, alias="2629")
    """The user has blocked another user."""

    user_unblocked: Optional[UserUnblocked] = Field(None, alias="2630")
    """The user has unblocked another user."""

    @cached_property
    def current_event(self) -> Optional[Tuple[str, Any]]:
        """
        Returns the first non-empty event in this update as a tuple of
        (field_name, event_value).

        If the event has a `fixed` attribute, it returns that instead of the raw value.
        Returns None if no events are set.
        
        This simplifies event handling by allowing to check a single property
        for the update's active event.
        """
        for field_name in self.model_fields:
            value = getattr(self, field_name, None)
            if value is not None:
                if hasattr(value, "fixed"):
                    value = value.fixed
                return field_name, value
        return None

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            message_sent: Optional[InfoMessage] = None,
            message_deleted: Optional[SelectedMessages] = None,
            chat_cleared: Optional[ChatData] = None,
            chat_deleted: Optional[ChatData] = None,
            message: Optional[Message] = None,
            message_edited: Optional[UpdatedMessage] = None,
            username_changed: Optional[UsernameChanged] = None,
            about_changed: Optional[AboutChanged] = None,
            group_message_pinned: Optional[GroupMessagePinned] = None,
            group_pin_removed: Optional[GroupPinRemoved] = None,
            user_blocked: Optional[UserBlocked] = None,
            user_unblocked: Optional[UserUnblocked] = None,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(
                message_sent=message_sent,
                message_deleted=message_deleted,
                chat_cleared=chat_cleared,
                chat_deleted=chat_deleted,
                message=message,
                message_edited=message_edited,
                username_changed=username_changed,
                about_changed=about_changed,
                group_message_pinned=group_message_pinned,
                group_pin_removed=group_pin_removed,
                user_blocked=user_blocked,
                user_unblocked=user_unblocked,
                **__pydantic_kwargs,
            )


class UpdateBody(BaleObject):
    """
    The envelope for an update sent by the Bale server.

    Contains:
    - `body`: the detailed update event,
    - `update_id`: a unique incremental ID for the update,
    - `date`: the timestamp (in milliseconds) when the update was generated.
    """

    body: Optional[Update] = Field(None, alias="1")
    """The actual update event data."""

    update_id: Optional[int] = Field(None, alias="3")
    """Unique identifier for this update, useful for tracking and acknowledging updates."""

    date: int = Field(..., alias="4")
    """Timestamp of the update event, in milliseconds since epoch."""

    if TYPE_CHECKING:
        def __init__(
            __pydantic__self__,
            *,
            body: Optional[Update] = None,
            update_id: Optional[int] = None,
            date: int,
            **__pydantic_kwargs
        ) -> None:
            super().__init__(
                body=body,
                update_id=update_id,
                date=date,
                **__pydantic_kwargs,
            )
