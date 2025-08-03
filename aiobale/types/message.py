from __future__ import annotations

from pydantic import Field, model_validator
from typing import TYPE_CHECKING, List, Optional, Union

from .chat import Chat
from .base import BaleObject
from ..enums import ChatType, ListLoadMode, ReportKind, TypingMode
from .quoted_message import QuotedMessage
from .message_content import MessageContent, DocumentMessage
from .other_message import OtherMessage
from .full_user import FullUser
from .user import User
from .message_reaction import MessageReactions
from .reaction_data import ReactionData
from .reaction import Reaction
from .file_details import FileDetails
from .file_input import FileInput
from .gift_packet import GiftPacket

if TYPE_CHECKING:
    from .responses import DefaultResponse


class Message(BaleObject):
    """
    Represents a message in Bale messenger with all its metadata.

    This class contains references to the chat the message belongs to, the sender,
    the message content, and related messages such as quoted replies or previous messages.
    Date fields are stored as Unix timestamps in milliseconds.
    """

    chat: Chat = Field(..., alias="1")
    """The chat object that this message belongs to."""

    sender_id: int = Field(..., alias="2")
    """The unique identifier of the sender (user ID)."""

    date: int = Field(..., alias="3")
    """Timestamp (in milliseconds) when the message was sent."""

    message_id: int = Field(..., alias="4")
    """Unique identifier for this message within the chat."""

    content: MessageContent = Field(..., alias="5")
    """The content of the message, which can be text, media, or other types."""

    quoted_replied_to: Optional[QuotedMessage] = Field(None, alias="7")
    """
    If this message is a reply, the quoted message it replies to.

    May not have the chat reference set initially, so it will be attached automatically.
    """

    previous_message: Optional[OtherMessage] = Field(None, alias="9")
    """The message that was sent immediately before this one (if known)."""

    next_message: Optional[OtherMessage] = Field(None, exclude=True)
    """The message that was sent immediately after this one (if known).  
    Excluded from serialization because it’s used only internally."""

    replied_to: Optional[Message] = Field(None, exclude=True)
    """The full `Message` object that this message replies to (if available).  
    Set automatically by `attach_chat_to_reply` validator."""

    if TYPE_CHECKING:
        # This init is only used for type checking and IDE autocomplete.
        # It will not be included in runtime behavior.
        def __init__(
            __pydantic__self__,
            *,
            chat: Chat,
            sender_id: int,
            date: int,
            message_id: int,
            content: MessageContent,
            quoted_replied_to: Optional[QuotedMessage] = None,
            previous_message: Optional[OtherMessage] = None,
            next_message: Optional[OtherMessage] = None,
            replied_to: Optional[Message] = None,
            **__pydantic_kwargs,
        ) -> None:
            super().__init__(
                chat=chat,
                sender_id=sender_id,
                date=date,
                message_id=message_id,
                content=content,
                quoted_replied_to=quoted_replied_to,
                previous_message=previous_message,
                next_message=next_message,
                replied_to=replied_to,
                **__pydantic_kwargs,
            )

    @property
    def text(self) -> Optional[str]:
        """
        Returns the textual content of the message if available.

        If the message content is not text-based, returns None.
        """
        text_content = self.content.text
        if text_content is None:
            return None
        return text_content.value

    @property
    def document(self) -> Optional[DocumentMessage]:
        """
        Returns the document content of the message if available.
        """
        return self.content.document

    @property
    def gift(self) -> Optional[GiftPacket]:
        """
        Returns the document content of the message if available.
        """
        return self.content.gift

    @model_validator(mode="after")
    def attach_chat_to_reply(self) -> Message:
        """
        Ensures that if this message quotes another message without a chat assigned,
        the chat from this message is attached to it.

        Also sets the `replied_to` field to the full replied message for easier access.
        """
        if self.quoted_replied_to and not self.quoted_replied_to.chat:
            self.quoted_replied_to.chat = self.chat

            if not self.replied_to:
                self.replied_to = self.quoted_replied_to.message

        return self

    async def answer(self, text: str, message_id: Optional[int] = None) -> Message:
        """
        Send a new message in the same chat.
        """
        return await self.client.send_message(
            text=text,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
        )

    async def reply(self, text: str, message_id: Optional[int] = None) -> Message:
        """
        Send a reply to this message.
        """
        return await self.client.send_message(
            text=text,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            reply_to=self,
            message_id=message_id,
        )

    async def answer_document(
        self,
        file: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        message_id: Optional[int] = None,
        use_own_content: bool = False,
    ) -> Message:
        """
        Send a document message to the same chat.
        """
        return await self.client.send_document(
            file=file,
            caption=caption,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            use_own_content=use_own_content
        )

    async def reply_document(
        self,
        file: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Reply with a document message to this message.
        """
        return await self.client.send_document(
            file=file,
            caption=caption,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            reply_to=self,
        )

    async def answer_photo(
        self,
        photo: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Send a photo message to the same chat.
        """
        return await self.client.send_photo(
            photo=photo,
            caption=caption,
            cover_thumb=cover_thumb,
            cover_width=cover_width,
            cover_height=cover_height,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
        )

    async def reply_photo(
        self,
        photo: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Reply with a photo message to this message.
        """
        return await self.client.send_photo(
            photo=photo,
            caption=caption,
            cover_thumb=cover_thumb,
            cover_width=cover_width,
            cover_height=cover_height,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            reply_to=self,
        )

    async def answer_video(
        self,
        video: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Send a video message to the same chat.
        """
        return await self.client.send_video(
            video=video,
            caption=caption,
            cover_thumb=cover_thumb,
            cover_width=cover_width,
            cover_height=cover_height,
            duration=duration,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
        )

    async def reply_video(
        self,
        video: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Reply with a video message to this message.
        """
        return await self.client.send_video(
            video=video,
            caption=caption,
            cover_thumb=cover_thumb,
            cover_width=cover_width,
            cover_height=cover_height,
            duration=duration,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            reply_to=self,
        )

    async def answer_voice(
        self,
        voice: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Send a voice message to the same chat.
        """
        return await self.client.send_voice(
            voice=voice,
            caption=caption,
            duration=duration,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
        )

    async def reply_voice(
        self,
        voice: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Reply with a voice message to this message.
        """
        return await self.client.send_voice(
            voice=voice,
            caption=caption,
            duration=duration,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            reply_to=self,
        )

    async def answer_audio(
        self,
        audio: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        duration: Optional[int] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        track: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Send an audio message to the same chat.
        """
        return await self.client.send_audio(
            audio=audio,
            caption=caption,
            duration=duration,
            album=album,
            genre=genre,
            track=track,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
        )

    async def reply_audio(
        self,
        audio: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        duration: Optional[int] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        track: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Reply with an audio message to this message.
        """
        return await self.client.send_audio(
            audio=audio,
            caption=caption,
            duration=duration,
            album=album,
            genre=genre,
            track=track,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            reply_to=self,
        )

    async def answer_gif(
        self,
        gif: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Send a GIF message to the same chat.
        """
        return await self.client.send_gif(
            gif=gif,
            caption=caption,
            duration=duration,
            cover_thumb=cover_thumb,
            cover_width=cover_width,
            cover_height=cover_height,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
        )

    async def reply_gif(
        self,
        gif: Union[FileDetails, DocumentMessage, FileInput],
        caption: Optional[str] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Reply with a GIF message to this message.
        """
        return await self.client.send_gif(
            gif=gif,
            caption=caption,
            duration=duration,
            cover_thumb=cover_thumb,
            cover_width=cover_width,
            cover_height=cover_height,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message_id=message_id,
            reply_to=self,
        )

    async def edit_text(self, text: str) -> DefaultResponse:
        """
        Edit the content of this message.
        """
        return await self.client.edit_message(
            text=text,
            message_id=self.message_id,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
        )

    async def delete(self, just_me: Optional[bool] = False) -> DefaultResponse:
        """
        Delete this message. If `just_me` is True, only you will stop seeing it.
        """
        return await self.client.delete_message(
            message_id=self.message_id,
            message_date=self.date,  # Timestamp in milliseconds
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            just_me=just_me,
        )

    async def forward_to(
        self, chat_id: int, chat_type: ChatType, new_id: Optional[int] = None
    ) -> DefaultResponse:
        """
        Forward this message to another chat.
        """
        return await self.client.forward_message(
            message=self, chat_id=chat_id, chat_type=chat_type, new_id=new_id
        )

    async def seen(self) -> DefaultResponse:
        """
        Mark this chat as seen (read).
        """
        return await self.client.seen_chat(
            chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def clear_chat(self) -> DefaultResponse:
        """
        Clear all messages from this chat on your side.
        """
        return await self.client.clear_chat(
            chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def delete_chat(self) -> DefaultResponse:
        """
        Delete this chat completely.
        """
        return await self.client.delete_chat(
            chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def load_history(
        self,
        limit: int = 20,
        offset_date: int = -1,
        load_mode: ListLoadMode = ListLoadMode.BACKWARD,
    ) -> List[Message]:
        """
        Load chat history from this message's chat.

        Args:
            limit: How many messages to load.
            offset_date: Timestamp (ms) to offset from. Use -1 to start from latest.
            load_mode: Direction of loading (BACKWARD or FORWARD).
        """
        return await self.client.load_history(
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            limit=limit,
            offset_date=offset_date,
            load_mode=load_mode,
        )

    async def pin(self, just_me: bool = False) -> DefaultResponse:
        """
        Pin this message in the chat. Use `just_me=True` to pin only for yourself.
        """
        return await self.client.pin_message(
            message_id=self.message_id,
            message_date=self.date,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            just_me=just_me,
        )

    async def unpin(self) -> DefaultResponse:
        """
        Unpin this message.
        """
        return await self.client.unpin_message(
            message_id=self.message_id,
            message_date=self.date,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
        )

    async def unpin_all(self) -> DefaultResponse:
        """
        Unpin all messages in this chat.
        """
        return await self.client.unpin_all(
            one_message_date=self.date,
            one_message_id=self.message_id,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
        )

    async def pin_in_group(self) -> DefaultResponse:
        """
        Pin this message in a group (server-side group pinning).
        """
        return await self.client.pin_group_message(
            message=self,
            chat_id=self.chat.id,
        )

    async def unpin_in_group(self) -> DefaultResponse:
        """
        Unpin this message from the group.
        """
        return await self.client.unpin_group_message(
            message=self,
            chat_id=self.chat.id,
        )

    async def unpin_all_in_group(self) -> DefaultResponse:
        """
        Remove all group pins from this chat.
        """
        return await self.client.remove_group_pins(chat_id=self.chat.id)

    async def load_pinned_messages(self) -> List[Message]:
        """
        Load all pinned messages in this chat.
        """
        return await self.client.load_pinned_messages(
            chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def load_full_chat(self) -> FullUser:
        """
        Load extended information about the chat.
        """
        return await self.client.load_full_user(
            chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def load_full_user(self) -> FullUser:
        """
        Load extended profile information about the sender.
        """
        return await self.client.load_full_user(
            chat_id=self.sender_id, chat_type=ChatType.PRIVATE
        )

    async def load_chat(self) -> User:
        """
        Load basic information about the chat.
        """
        return await self.client.load_user(
            chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def load_user(self) -> User:
        """
        Load basic profile information about the sender.
        """
        return await self.client.load_user(
            chat_id=self.sender_id, chat_type=ChatType.PRIVATE
        )

    async def edit_local_name(self, name: str) -> DefaultResponse:
        """
        Change how you see this user’s name locally.
        """
        return await self.client.edit_user_local_name(name=name, user_id=self.sender_id)

    async def block(self) -> DefaultResponse:
        """
        Block the sender of this message.
        """
        return await self.client.block_user(user_id=self.sender_id)

    async def unblock(self) -> DefaultResponse:
        """
        Unblock the sender of this message.
        """
        return await self.client.unblock_user(user_id=self.sender_id)

    async def add_as_contact(self) -> DefaultResponse:
        """
        Add the sender of this message as a contact.
        """
        return await self.client.add_contact(user_id=self.sender_id)

    async def remove_contact(self) -> DefaultResponse:
        """
        Remove the sender from your contacts.
        """
        return await self.client.remove_contact(user_id=self.sender_id)

    async def report(
        self, kind: ReportKind = ReportKind.SPAM, reason: Optional[str] = None
    ) -> DefaultResponse:
        """
        Report this message for a specific reason.
        """
        return await self.client.report_message(
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            message=self,
            kind=kind,
            reason=reason,
        )

    async def report_chat(
        self, reason: Optional[str] = None, kind: ReportKind = ReportKind.SPAM
    ) -> DefaultResponse:
        """
        Report the entire chat for spam or another reason.
        """
        return await self.client.report_chat(
            chat_id=self.chat.id, chat_type=self.chat.type, kind=kind, reason=reason
        )

    async def start_typing(
        self, typing_mode: TypingMode = TypingMode.TEXT
    ) -> DefaultResponse:
        """
        Simulate typing in this chat (e.g., text, voice).
        """
        return await self.client.start_typing(
            chat_id=self.chat.id, chat_type=self.chat.type, typing_mode=typing_mode
        )

    async def stop_typing(
        self, typing_mode: TypingMode = TypingMode.TEXT
    ) -> DefaultResponse:
        """
        Stop the typing indicator in this chat.
        """
        return await self.client.stop_typing(
            chat_id=self.chat.id, chat_type=self.chat.type, typing_mode=typing_mode
        )

    async def get_reactions(self) -> MessageReactions:
        """
        Get all reactions to this message.
        """
        return await self.client.get_message_reactions(
            message=self, chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def get_reaction_list(
        self, emojy: str, page: int = 1, limit: int = 20
    ) -> List[ReactionData]:
        """
        Get the list of users who reacted with a specific emoji.
        """
        return await self.client.get_reaction_list(
            emojy=emojy,
            message=self,
            chat_id=self.chat.id,
            chat_type=self.chat.type,
            limit=limit,
            page=page,
        )

    async def react(self, emojy: str) -> List[Reaction]:
        """
        Add a reaction to this message.
        """
        return await self.client.set_reaction(
            emojy=emojy, message=self, chat_id=self.chat.id, chat_type=self.chat.type
        )

    async def remove_reaction(self, emojy: str) -> List[Reaction]:
        """
        Remove your reaction from this message.
        """
        return await self.client.remove_reaction(
            emojy=emojy, message=self, chat_id=self.chat.id, chat_type=self.chat.type
        )
