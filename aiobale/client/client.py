from __future__ import annotations

import asyncio
import io
import pathlib
import signal
import sys
import warnings
import aiofiles
import os
from typing import (
    AsyncGenerator,
    BinaryIO,
    Callable,
    Coroutine,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Final,
    Union,
)
from types import TracebackType
from contextlib import suppress

from .session import AiohttpSession, BaseSession
from ..exceptions import AiobaleError
from ..utils import parse_jwt, generate_id, clean_grpc, extract_join_token
from ..methods import (
    SendMessage,
    BaleMethod,
    BaleType,
    StartPhoneAuth,
    ValidateCode,
    DeleteMessage,
    ForwardMessages,
    MessageRead,
    EditName,
    EditNickName,
    CheckNickName,
    UpdateMessage,
    ClearChat,
    DeleteChat,
    LoadHistory,
    SetOnline,
    PinMessage,
    UnPinMessages,
    LoadPinnedMessages,
    LoadDialogs,
    EditAbout,
    LoadFullUsers,
    LoadUsers,
    EditUserLocalName,
    BlockUser,
    UnblockUser,
    LoadBlockedUsers,
    SearchContact,
    ImportContacts,
    ResetContacts,
    RemoveContact,
    AddContact,
    GetContacts,
    SendReport,
    StopTyping,
    Typing,
    GetParameters,
    EditParameter,
    GetMessagesReactions,
    GetMessageReactionsList,
    MessageSetReaction,
    MessageRemoveReaction,
    GetMessagesViews,
    ValidatePassword,
    GetFullGroup,
    LoadMembers,
    CreateGroup,
    InviteUsers,
    EditGroupTitle,
    EditGroupAbout,
    SetRestriction,
    GetGroupInviteURL,
    RevokeInviteURL,
    LeaveGroup,
    TransferOwnership,
    RemoveUserAdmin,
    MakeUserAdmin,
    KickUser,
    RemoveUserAdmin,
    JoinGroup,
    JoinPublicGroup,
    PinGroupMessage,
    RemoveSinglePin,
    RemoveAllPins,
    GetPins,
    EditChannelUsername,
    SetMemberPermissions,
    GetMemberPermissions,
    SetGroupDefaultPermissions,
    GetBannedUsers,
    UnbanUser,
    GetGroupPreview,
    GetFileUrl,
    GetFileUploadUrl,
    GetMyKifpools,
    SendGiftPacketWithWallet,
    OpenGiftPacket,
    SignOut,
)
from ..types import (
    MessageContent,
    ClientData,
    Peer,
    Chat,
    TextMessage,
    DocumentMessage,
    UserAuth,
    IntValue,
    Message,
    InfoMessage,
    StringValue,
    OtherMessage,
    MessageData,
    QuotedMessage,
    PeerData,
    InfoPeer,
    FullUser,
    User,
    ContactData,
    Report,
    PeerReport,
    MessageReport,
    ExtKeyValue,
    MessageReactions,
    ReactionData,
    Reaction,
    MessageViews,
    FullGroup,
    ShortPeer,
    Member,
    Condition,
    BoolValue,
    Permissions,
    BanData,
    FileInfo,
    FileURL,
    FileInput,
    FileUploadInfo,
    FileDetails,
    SendTypeModel,
    MessageCaption,
    Thumbnail,
    VideoExt,
    VoiceExt,
    AudioExt,
    PhotoExt,
    DocumentsExt,
    UpdateBody,
    Request,
    GiftPacket,
)
from ..types.responses import (
    MessageResponse,
    PhoneAuthResponse,
    ValidateCodeResponse,
    DefaultResponse,
    NickNameAvailable,
    HistoryResponse,
    DialogResponse,
    FullUsersResponse,
    UsersResponse,
    BlockedUsersResponse,
    ContactResponse,
    ContactsResponse,
    ParametersResponse,
    ReactionsResponse,
    ReactionListResponse,
    ReactionSentResponse,
    ViewsResponse,
    FullGroupResponse,
    MembersResponse,
    GroupCreatedResponse,
    InviteResponse,
    InviteURLResponse,
    JoinedGroupResponse,
    GetPinsResponse,
    MemberPermissionsResponse,
    BannedUsersResponse,
    FileURLResponse,
    WalletResponse,
    PacketResponse,
)
from ..enums import (
    ChatType,
    PeerType,
    SendCodeType,
    ListLoadMode,
    PeerSource,
    ReportKind,
    TypingMode,
    Restriction,
    GroupType,
    SendType,
    GivingType,
)
from ..dispatcher.dispatcher import Dispatcher
from ..logger import logger
from .auth_cli import PhoneLoginCLI


DEFAULT_SESSION: Final[str] = "./session.bale"


class Client:
    """
    Main interface for interacting with the Bale API.

    ----

    This class manages the session, dispatches updates, and provides core context
    for sending and receiving messages. It acts as the entry point to most high-level
    API functionality.

    .. warning::

        Improper or abusive use of this client — such as spamming, unauthorized automation,
        or violating platform rules — can result in account suspension or permanent bans.
        Always follow Bale’s official API usage policies.

    A :class:Client instance can be initialized with an optional :class:Dispatcher object.
    While the dispatcher is not required, it must be provided if you intend to handle incoming updates.
    You may also optionally provide a session file or a custom session backend.
    If none is given, a default Aiohttp-based session will be used.

    If a token is not found in the session file, authentication falls back to the CLI login flow.

    .. note::

        The session file path must end with a ``.bale`` extension. Otherwise, an
        :class:`AiobaleError` will be raised during initialization.

    Internally, the client binds the session to itself and loads authentication tokens,
    metadata, and user context if available.

    Most timestamp values returned by the API (such as message time, update time, etc.)
    are in milliseconds since the UNIX epoch.

    .. note::

        When working with datetime objects in Python, divide these values by 1000
        before converting with `datetime.fromtimestamp()` or related utilities.

    In the Bale protocol, the concept of a "group" encompasses both regular groups and
    broadcast channels. They are distinguished by specific internal flags but are
    represented uniformly in API responses.

    .. note::

        You can safely create a client instance even if you don't have a valid session yet.
        The CLI login flow will guide you through the authentication process interactively.

    """

    def __init__(
        self,
        dispatcher: Optional[Dispatcher] = None,
        session_file: Optional[str] = DEFAULT_SESSION,
        session: Optional[BaseSession] = None,
    ):
        if session is None:
            session = AiohttpSession()

        session._bind_client(self)
        self.session: BaseSession = session
        self.dispatcher: Optional[Dispatcher] = dispatcher
        self._ping_task = None
        self._ping_id = 0
        self._lock = asyncio.Lock()
        self._tasks = set()
        self._stopped = False

        if not isinstance(session_file, str) or not session_file.lower().endswith(
            ".bale"
        ):
            raise AiobaleError(
                f"Invalid session file: {session_file!r}. "
                "Only `.bale` files are allowed."
            )

        self.__session_file = session_file
        self.__token = None
        self._me = None

        self._add_token_via_file()

    @property
    def token(self) -> str:
        """
        Returns the currently loaded authentication token for the session.

        This token is required for making authorized API requests. It is either
        loaded from the session file or obtained during the interactive login flow.
        """
        return self.__token

    @property
    def me(self) -> ClientData:
        """
        Returns information about the authenticated user.

        This includes details such as user ID and other metadata
        returned from the Bale API after successful login.
        """
        return self._me

    @property
    def id(self) -> int:
        """
        Returns the numeric ID of the authenticated user.

        Equivalent to `client.me.id`. Useful as a shortcut for user identification
        in event handling and API interactions.
        """
        return self._me.id
    
    def _create_task(self, coro: Coroutine):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _write_session_content(self, content: bytes) -> None:
        if not self.__session_file:
            return

        with open(self.__session_file, "wb") as f:
            f.write(content)

    def _get_session_content(self) -> Optional[bytes]:
        if self.__session_file and os.path.exists(self.__session_file):
            with open(self.__session_file, "rb") as f:
                return f.read()
        return None

    def _parse_session_content(self, data: bytes) -> ValidateCodeResponse:
        decoded = self.session.decoder(clean_grpc(data))
        model = ValidateCodeResponse.model_validate(decoded)

        self.__token = model.jwt.value
        self._me = self._check_token(model.user)

        return model

    def _add_token_via_file(self) -> bool:
        content = self._get_session_content()
        if content is None:
            return False

        self._parse_session_content(content)
        return True

    async def _ensure_token_exists(self) -> None:
        if self.__token is None:
            if not self._add_token_via_file():
                auth_cli = PhoneLoginCLI(self)
                await auth_cli.start()

    async def __call__(self, method: BaleMethod[BaleType]):
        if not self.session.running:
            await self._ensure_token_exists()
            return await self.session.post(
                method=method, just_bale_type=True, token=self.__token
            )

        return await self.session.make_request(method)

    async def _cleanup_session(self):
        async with self._lock:
            if self.session and not self.session.is_closed():
                await self.session.close()

            if self._ping_task:
                self._ping_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._ping_task
                self._ping_task = None

    async def _send_ping(self):
        async with self._lock:
            if self.session.is_closed():
                return

            self._ping_id += 1
            ping_id = self._ping_id
            request = Request(ping=IntValue(value=ping_id))
            payload = request.model_dump(exclude_none=True, by_alias=True)
            data = self.session.encoder(payload)

            try:
                await self.session.send_bytes(data, f"ping_{ping_id}")
            except RuntimeError:
                logger.warning("Ping failed. Closing session to trigger restart.")
                await self._cleanup_session()

    async def _ping_loop(self, interval=5):
        try:
            while True:
                await asyncio.sleep(interval)
                await self._send_ping()
        except asyncio.CancelledError:
            logger.info("Ping loop cancelled.")
        except Exception as e:
            logger.error(f"Unexpected error in ping loop: {e}")
            await self._cleanup_session()

    async def _safe_listen(self):
        try:
            await self.session._listen()
        except Exception as e:
            logger.error(f"Listen failed: {e}")
            await self._cleanup_session()
            
    def _setup_signal_handlers(self, loop):
        def handler():
            logger.info("Signal received, stopping client...")
            asyncio.create_task(self.stop())

        signals = []
        if sys.platform != "win32":
            signals = [signal.SIGINT, signal.SIGTERM]

        for sig in signals:
            try:
                loop.add_signal_handler(sig, handler)
            except NotImplementedError:
                logger.warning(f"Signal {sig} handler not implemented.")

    async def start(self, run_in_background: bool = False):
        """
        Starts the client session and begins listening for events.
        Args:
            run_in_background (bool, optional): If True, starts listening in a background task;
                otherwise, listens in the current coroutine. Defaults to False.
        Raises:
            BaleError: If the server returns an error during connection or handshake.
            AiobaleError: For client-side errors such as invalid token or session issues.
        Returns:
            None
        This method ensures the authentication token exists, connects to the server, performs the handshake,
        and starts listening for incoming events. Use `run_in_background=True` to keep listening without blocking
        the current coroutine.
        """
        self._stopped = False
        await self._ensure_token_exists()
        
        loop = asyncio.get_running_loop()
        self._setup_signal_handlers(loop)

        try:
            while not self._stopped:
                await self._cleanup_session()

                async with self._lock:
                    try:
                        logger.info("Trying to connect...")
                        await self.session.connect(self.__token)
                        await self.session.handshake_request()
                        logger.info("Connected successfully.")

                        self._ping_task = self._create_task(self._ping_loop())
                        listen_task = self._create_task(self._safe_listen())
                    except Exception as e:
                        logger.error(f"Connection failed: {e}")
                        await asyncio.sleep(5)
                        continue

                if run_in_background:
                    return
                else:
                    try:
                        await listen_task
                    except asyncio.CancelledError:
                        logger.info("Listening task cancelled.")
                        break

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, stopping client...")
            await self.stop()
        except Exception as e:
            logger.error(f"Unhandled exception in start: {e}")
            await self.stop()
            raise

    async def stop(self):
        """
        Gracefully stops the client by closing the associated session.

        This method ensures that all resources tied to the session are properly
        released. It should be called when the client is no longer needed to
        prevent resource leaks.
        """
        if self._stopped:
            return

        self._stopped = True
        logger.info("Stopping client...")

        if self._ping_task:
            self._ping_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ping_task
            self._ping_task = None

        for task in list(self._tasks):
            task.cancel()

        for task in list(self._tasks):
            with suppress(asyncio.CancelledError):
                await task

        await self._cleanup_session()
        logger.info("Client stopped cleanly.")

    async def handle_update(self, update: UpdateBody) -> None:
        """
        Handle a single incoming update event from the Bale API.

        This method processes the incoming `UpdateBody`, extracts the current event,
        and dispatches it to the associated dispatcher, if available. Messages sent by
        the client itself are ignored.

        Args:
            update (UpdateBody): The incoming update payload received from the API.

        Returns:
            None
        """
        if update.body is None:
            return

        event_info = update.body.current_event
        if not event_info:
            return

        event_type, event = event_info

        # Ignore messages sent by this client
        if event_type == "message" and getattr(event, "sender_id", None) == self.id:
            return

        if self.dispatcher is not None:
            await self.dispatcher.dispatch(event_type, event)

    @classmethod
    async def __download_file_binary_io(
        cls, destination: BinaryIO, seek: bool, stream: AsyncGenerator[bytes, None]
    ) -> BinaryIO:
        async for chunk in stream:
            destination.write(chunk)
            destination.flush()
        if seek is True:
            destination.seek(0)
        return destination

    @classmethod
    async def __download_file(
        cls, destination: Union[str, pathlib.Path], stream: AsyncGenerator[bytes, None]
    ) -> None:
        async with aiofiles.open(destination, "wb") as f:
            async for chunk in stream:
                await f.write(chunk)

    async def __aenter__(self) -> Client:
        await self.start(True)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.session.close()

    def _check_token(self, user: UserAuth) -> ClientData:
        token = self.__token
        result = parse_jwt(token)
        if not result:
            raise AiobaleError("Not a valid jwt token")

        data, _ = result
        if "payload" not in data:
            raise AiobaleError("Wrong jwt payload")

        data["payload"]["user"] = user
        return ClientData.model_validate(data["payload"])

    async def start_phone_auth(
        self,
        phone_number: int,
        code_type: Optional[SendCodeType] = SendCodeType.DEFAULT,
    ) -> PhoneAuthResponse:
        """
        Initiates phone authentication by sending a code to the specified phone number.

        Args:
            phone_number (int): The phone number to authenticate.
            code_type (Optional[aiobale.enums.SendCodeType], optional): Type of code to send. Defaults to SendCodeType.DEFAULT.

        Returns:
            aiobale.types.responses.PhoneAuthResponse: Contains transaction hash and other authentication details.

        Raises:
            BaleError: If the server returns an error during authentication.
            AiobaleError: If the phone number is banned or other client-side errors occur.
        """
        call = StartPhoneAuth(
            phone_number=phone_number,
            app_id=4,
            app_key="C28D46DC4C3A7A26564BFCC48B929086A95C93C98E789A19847BEE8627DE4E7D",
            device_hash="ce5ced83-a9ab-47fa-80c8-ed425eeb2ace",
            device_title="Chrome_138.0.0.0, Windows",
            send_code_type=code_type,
        )

        try:
            return await self.session.post(call)
        except:
            raise AiobaleError("This phone number is banned")

    async def validate_code(
        self, code: str, transaction_hash: str
    ) -> ValidateCodeResponse:
        """
        Validates the authentication code received via SMS or other means.

        Args:
            code (str): The code received for authentication.
            transaction_hash (str): The transaction hash from the login step.

        Returns:
            aiobale.types.responses.ValidateCodeResponse: Contains JWT token and user authentication data.

        Raises:
            BaleError: If the server returns an error during validation.
            AiobaleError: For invalid code, password requirement, or client-side errors.
        """
        call = ValidateCode(code=code, transaction_hash=transaction_hash)

        content = await self.session.post(call)
        if isinstance(content, str):
            if content == "PHONE_CODE_INVALID":
                raise AiobaleError("Invalid code specified.")
            elif content == "password needed for login":
                raise AiobaleError("Password needed for login")
            else:
                raise AiobaleError("Unknown Error")

        try:
            self._write_session_content(content)
            return self._parse_session_content(content)

        except Exception as e:
            raise AiobaleError("Error while parsing data.") from e

    async def validate_password(
        self, password: str, transaction_hash: str
    ) -> ValidateCodeResponse:
        """
        Validates the password for two-factor authentication if required.

        Args:
            password (str): The password for authentication.
            transaction_hash (str): The transaction hash from the login step.

        Returns:
            aiobale.types.responses.ValidateCodeResponse: Contains JWT token and user authentication data.

        Raises:
            BaleError: If the server returns an error during validation.
            AiobaleError: For wrong password or client-side errors.
        """
        call = ValidatePassword(password=password, transaction_hash=transaction_hash)

        content = await self.session.post(call)
        if isinstance(content, str):
            if content == "wrong password":
                raise AiobaleError("Wrong password specified.")
            else:
                raise AiobaleError("Unknown Error")

        try:
            self._write_session_content(content)
            return self._parse_session_content(content)

        except Exception as e:
            raise AiobaleError("Error while parsing data.") from e

    async def sign_out(self, delete_session: bool = True) -> None:
        """
        Signs out the current user and optionally deletes the session file.

        This method sends a sign-out request to the server, stops the client session,
        and if requested, deletes the local session file from disk.

        Args:
            delete_session (bool, optional): Whether to delete the local session file after sign out.
                Defaults to True.

        Raises:
            OSError: If the session file deletion fails due to an OS-level error.
            Exception: Any unexpected exceptions during stopping the client or file deletion.
        """
        call = SignOut()
        await self.session.post(call, just_bale_type=True, token=self.__token)
        await self.stop()

        if (
            delete_session
            and self.__session_file
            and os.path.exists(self.__session_file)
        ):
            try:
                os.remove(self.__session_file)
                logger.info(
                    f"Session file '{self.__session_file}' deleted successfully."
                )
            except Exception as e:
                logger.error(f"Failed to delete session file: {e}")

    async def send_message(
        self,
        text: str,
        chat_id: int,
        chat_type: ChatType,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Sends a text message to a specified chat.

        Args:
            text (str): The message text to send.
            chat_id (int): The target chat ID.
            chat_type (aiobale.enums.ChatType): The type of chat (private, group, etc.).
            reply_to (Optional[aiobale.types.Message or aiobale.types.InfoMessage], optional): Message to reply to. Defaults to None.
            message_id (Optional[int], optional): Custom message ID. Defaults to None.

        Returns:
            aiobale.types.Message: The sent message object.

        Raises:
            BaleError: If the server returns an error during sending.
            AiobaleError: For client-side errors.
        """
        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        message_id = message_id or generate_id()

        content = MessageContent(text=TextMessage(value=text))

        if reply_to is not None:
            reply_to = self._ensure_info_message(reply_to)

        call = SendMessage(
            peer=peer,
            message_id=message_id,
            content=content,
            reply_to=reply_to,
            chat=chat,
        )

        result: MessageResponse = await self(call)
        return result.message

    def _resolve_peer_type(self, chat_type: ChatType) -> PeerType:
        """
        Resolves the PeerType based on the given ChatType.

        Args:
            chat_type (aiobale.enums.ChatType): The chat type.

        Returns:
            aiobale.enums.PeerType: The resolved peer type.
        """
        if chat_type == ChatType.UNKNOWN:
            return PeerType.UNKNOWN
        elif chat_type in (ChatType.PRIVATE, ChatType.BOT):
            return PeerType.PRIVATE
        return PeerType.GROUP

    def _resolve_peer(self, chat: Chat) -> Peer:
        """
        Converts a Chat object to a Peer object.

        Args:
            chat (aiobale.types.Chat): The chat object.

        Returns:
            aiobale.types.Peer: The corresponding peer object.
        """
        peer_type = self._resolve_peer_type(chat.type)
        return Peer(id=chat.id, type=peer_type)

    async def edit_message(
        self, text: str, message_id: int, chat_id: int, chat_type: ChatType
    ) -> DefaultResponse:
        """
        Edits the content of an existing message.

        Args:
            text (str): The new message text.
            message_id (int): The ID of the message to edit.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error during editing.
            AiobaleError: For client-side errors.
        """
        peer_type = self._resolve_peer_type(chat_type)
        peer = Peer(type=peer_type, id=chat_id)
        content = MessageContent(text=TextMessage(value=text))

        call = UpdateMessage(peer=peer, message_id=message_id, updated_message=content)

        return await self(call)

    async def delete_messages(
        self,
        message_ids: List[int],
        message_dates: List[int],
        chat_id: int,
        chat_type: ChatType,
        just_me: Optional[bool] = False,
    ) -> DefaultResponse:
        """
        Deletes multiple messages from a chat.

        Args:
            message_ids (List[int]): List of message IDs to delete.
            message_dates (List[int]): List of corresponding message dates.
            chat_id (int): The chat ID containing the messages.
            chat_type (aiobale.enums.ChatType): The type of chat.
            just_me (Optional[bool], optional): If True, deletes only for the current user. Defaults to False.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the delete operation.

        Raises:
            BaleError: If the server returns an error during deletion.
            AiobaleError: If input lists are empty or for other client-side errors.
        """
        if not message_ids or not message_dates:
            raise AiobaleError("`message_ids` or `message_dates` can not be empty")

        peer_type = self._resolve_peer_type(chat_type)
        peer = Peer(type=peer_type, id=chat_id)

        call = DeleteMessage(
            peer=peer,
            message_ids=message_ids,
            dates=message_dates,
            just_me=IntValue(value=int(just_me)),
        )

        return await self(call)

    async def delete_message(
        self,
        message_id: int,
        message_date: int,
        chat_id: int,
        chat_type: ChatType,
        just_me: Optional[bool] = False,
    ) -> DefaultResponse:
        """
        Deletes a single message from a chat.

        Args:
            message_id (int): The ID of the message to delete.
            message_date (int): The date of the message.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.
            just_me (Optional[bool], optional): If True, deletes only for the current user. Defaults to False.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the delete operation.

        Raises:
            BaleError: If the server returns an error during deletion.
            AiobaleError: For client-side errors.
        """
        return await self.delete_messages(
            message_ids=[message_id],
            message_dates=[message_date],
            chat_id=chat_id,
            chat_type=chat_type,
            just_me=just_me,
        )

    async def forward_messages(
        self,
        messages: List[Union[Message, InfoMessage]],
        chat_id: int,
        chat_type: ChatType,
        new_ids: Optional[List[int]] = None,
    ) -> DefaultResponse:
        """
        Forwards multiple messages to another chat.

        Args:
            messages (List[aiobale.types.Message or aiobale.types.InfoMessage]): List of messages to forward.
            chat_id (int): The target chat ID.
            chat_type (aiobale.enums.ChatType): The type of target chat.
            new_ids (Optional[List[int]], optional): List of new message IDs for the forwarded messages. Defaults to None.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the forward operation.

        Raises:
            BaleError: If the server returns an error during forwarding.
            AiobaleError: If input lists are empty or mismatched, or for other client-side errors.
        """
        if not messages:
            raise AiobaleError("`messages` cannot be empty")

        if new_ids is None:
            new_ids = [generate_id() for _ in messages]

        if len(new_ids) != len(messages):
            raise AiobaleError("Mismatch between number of `new_ids` and `messages`")

        target_peer = Peer(type=self._resolve_peer_type(chat_type), id=chat_id)

        forwarded_messages = [self._ensure_info_message(msg) for msg in messages]

        call = ForwardMessages(
            peer=target_peer, message_ids=new_ids, forwarded_messages=forwarded_messages
        )

        return await self(call)

    def _ensure_info_message(
        self, message: Union[Message, InfoMessage], rewrite_date: bool = False
    ) -> InfoMessage:
        """
        Converts a Message object to an InfoMessage if necessary.

        Args:
            message (Union[aiobale.types.Message, aiobale.types.InfoMessage]): The message to ensure as InfoMessage.

        Returns:
            aiobale.types.InfoMessage: The InfoMessage representation of the input.

        Raises:
            AiobaleError: For client-side errors.
        """
        if isinstance(message, InfoMessage):
            if rewrite_date and isinstance(message.date, IntValue):
                message.date = message.date.value

            return message

        origin_peer = self._resolve_peer(message.chat)

        return InfoMessage(
            peer=origin_peer,
            message_id=message.message_id,
            date=message.date if rewrite_date else IntValue(value=message.date),
        )

    def _ensure_other_message(
        self,
        message: Union[Message, InfoMessage, OtherMessage],
        seq: Optional[int] = None,
    ) -> InfoMessage:
        """
        Converts a Message or InfoMessage to OtherMessage, optionally setting the sequence.

        Args:
            message (Union[aiobale.types.Message, aiobale.types.InfoMessage, aiobale.types.OtherMessage]): The message to convert.
            seq (Optional[int], optional): Sequence number to set. Defaults to None.

        Returns:
            aiobale.types.OtherMessage: The OtherMessage representation.

        Raises:
            AiobaleError: For client-side errors.
        """
        if isinstance(message, OtherMessage):
            if seq is not None:
                message.seq = seq

            return message

        return OtherMessage(message_id=message.message_id, date=message.date, seq=seq)

    async def forward_message(
        self,
        message: Union[Message, InfoMessage],
        chat_id: int,
        chat_type: ChatType,
        new_id: Optional[int] = None,
    ) -> DefaultResponse:
        """
        Forwards a single message to another chat.

        Args:
            message (Union[aiobale.types.Message, aiobale.types.InfoMessage]): The message to forward.
            chat_id (int): The target chat ID.
            chat_type (aiobale.enums.ChatType): The type of target chat.
            new_id (Optional[int], optional): New message ID for the forwarded message. Defaults to None.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the forward operation.

        Raises:
            BaleError: If the server returns an error during forwarding.
            AiobaleError: For client-side errors.
        """
        new_ids = [new_id] if new_id is not None else None

        return await self.forward_messages(
            messages=[message], chat_id=chat_id, chat_type=chat_type, new_ids=new_ids
        )

    async def seen_chat(self, chat_id: int, chat_type: ChatType) -> DefaultResponse:
        """
        Marks a chat as seen (read).

        Args:
            chat_id (int): The chat ID to mark as seen.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the seen operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer_type = self._resolve_peer_type(chat_type)
        peer = Peer(id=chat_id, type=peer_type)

        call = MessageRead(peer=peer)

        return await self(call)

    async def clear_chat(self, chat_id: int, chat_type: ChatType) -> DefaultResponse:
        """
        Clears all messages in a chat.

        Args:
            chat_id (int): The chat ID to clear.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the clear operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer_type = self._resolve_peer_type(chat_type)
        peer = Peer(id=chat_id, type=peer_type)

        call = ClearChat(peer=peer)

        return await self(call)

    async def delete_chat(self, chat_id: int, chat_type: ChatType) -> DefaultResponse:
        """
        Deletes a chat entirely.

        Args:
            chat_id (int): The chat ID to delete.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the delete operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer_type = self._resolve_peer_type(chat_type)
        peer = Peer(id=chat_id, type=peer_type)

        call = DeleteChat(peer=peer)

        return await self(call)

    async def load_history(
        self,
        chat_id: int,
        chat_type: ChatType,
        limit: int = 20,
        offset_date: int = -1,
        load_mode: ListLoadMode = ListLoadMode.BACKWARD,
    ) -> List[Message]:
        """
        Loads the message history for a chat.

        Args:
            chat_id (int): The chat ID to load history from.
            chat_type (aiobale.enums.ChatType): The type of chat.
            limit (int, optional): Number of messages to load. Defaults to 20.
            offset_date (int, optional): Date offset for pagination. Defaults to -1.
            load_mode (aiobale.enums.ListLoadMode, optional): Direction to load messages. Defaults to BACKWARD.

        Returns:
            List[aiobale.types.Message]: List of loaded messages.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        call = LoadHistory(
            peer=peer, offset_date=offset_date, load_mode=load_mode, limit=limit
        )

        result: HistoryResponse = await self(call)
        result.add_chat(chat)

        return self._resolve_list_messages(result.data)

    @staticmethod
    def _resolve_list_messages(
        data: List[Union[MessageData, QuotedMessage]],
    ) -> List[Message]:
        """
        Extracts Message objects from a list of MessageData or QuotedMessage.

        Args:
            data (List[Union[aiobale.types.MessageData, aiobale.types.QuotedMessage]]): The data to extract from.

        Returns:
            List[aiobale.types.Message]: List of Message objects.
        """
        return [item.message for item in data]

    async def pin_message(
        self,
        message_id: int,
        message_date: int,
        chat_id: int,
        chat_type: ChatType,
        just_me: bool = False,
    ) -> DefaultResponse:
        """
        Pins a message in a private chat.

        Args:
            message_id (int): The ID of the message to pin.
            message_date (int): The date of the message.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.
            just_me (bool, optional): If True, pins only for the current user. Defaults to False.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the pin operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        call = PinMessage(
            peer=peer,
            message=OtherMessage(message_id=message_id, date=message_date),
            just_me=just_me,
        )

        return await self(call)

    async def unpin_message(
        self, message_id: int, message_date: int, chat_id: int, chat_type: ChatType
    ) -> DefaultResponse:
        """
        Unpins a specific message in a private chat.

        Args:
            message_id (int): The ID of the message to unpin.
            message_date (int): The date of the message.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the unpin operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        call = UnPinMessages(
            peer=peer, messages=[OtherMessage(message_id=message_id, date=message_date)]
        )

        return await self(call)

    async def unpin_all(
        self,
        one_message_id: int,
        one_message_date: int,
        chat_id: int,
        chat_type: ChatType,
    ) -> DefaultResponse:
        """
        Unpins all messages in a private chat.

        Args:
            one_message_id (int): The ID of one pinned message (required by API).
            one_message_date (int): The date of the pinned message.
            chat_id (int): The chat ID.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the unpin all operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        call = UnPinMessages(
            peer=peer,
            messages=[OtherMessage(message_id=one_message_id, date=one_message_date)],
            all_messages=True,
        )

        return await self(call)

    async def load_pinned_messages(
        self, chat_id: int, chat_type: ChatType
    ) -> List[Message]:
        """
        Loads all pinned messages in a chat.

        Args:
            chat_id (int): The chat ID to load pinned messages from.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            List[aiobale.types.Message]: List of pinned messages.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        call = LoadPinnedMessages(peer=peer)

        result: HistoryResponse = await self(call)
        result.add_chat(chat)

        return self._resolve_list_messages(result.data)

    async def load_dialogs(
        self, limit: int = 40, offset_date: int = -1, exclude_pinned: bool = False
    ) -> List[PeerData]:
        """
        Loads the list of dialogs (chats) for the user.

        Args:
            limit (int, optional): Number of dialogs to load. Defaults to 40.
            offset_date (int, optional): Date offset for pagination. Defaults to -1.
            exclude_pinned (bool, optional): If True, excludes pinned dialogs. Defaults to False.

        Returns:
            List[aiobale.types.PeerData]: List of dialog data.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = LoadDialogs(
            offset_date=offset_date, limit=limit, exclude_pinned=exclude_pinned
        )

        result: DialogResponse = await self(call)
        return result.dialogs

    async def edit_name(self, name: str) -> DefaultResponse:
        """
        Edits the user's display name.

        Args:
            name (str): The new display name.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = EditName(name=name)
        return await self(call)

    async def check_username(self, username: str) -> bool:
        """
        Checks if a username is available.

        Args:
            username (str): The username to check.

        Returns:
            bool: True if available, False otherwise.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = CheckNickName(nick_name=username)

        result: NickNameAvailable = await self(call)
        return result.availbale

    async def edit_username(self, username: str) -> DefaultResponse:
        """
        Edits the user's username.

        Args:
            username (str): The new username.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = EditNickName(nick_name=StringValue(value=username))
        return await self(call)

    async def edit_about(self, about: str) -> DefaultResponse:
        """
        Edits the user's "about" section.

        Args:
            about (str): The new about text.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = EditAbout(about=StringValue(value=about))
        return await self(call)

    async def load_full_users(
        self, peers: List[Union[Peer, InfoPeer]]
    ) -> List[FullUser]:
        """
        Loads detailed information for a list of users or peers.

        Args:
            peers (List[Union[aiobale.types.Peer, aiobale.types.InfoPeer]]): List of Peer or InfoPeer objects to fetch details for.

        Returns:
            List[aiobale.types.FullUser]: List of FullUser objects containing detailed user information.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peers = [
            InfoPeer(id=peer.id, type=peer.type) if isinstance(peer, Peer) else peer
            for peer in peers
        ]

        call = LoadFullUsers(peers=peers)

        result: FullUsersResponse = await self(call)
        return result.data

    async def load_full_user(self, chat_id: int, chat_type: ChatType) -> FullUser:
        """
        Loads detailed information for a single user or peer.

        Args:
            chat_id (int): The ID of the user or peer.
            chat_type (aiobale.enums.ChatType): The type of chat (private, group, etc.).

        Returns:
            aiobale.types.FullUser: Detailed information about the user.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peers = [InfoPeer(id=chat_id, type=chat_type)]
        result = await self.load_full_users(peers=peers)
        return result[0]

    async def get_full_me(self) -> FullUser:
        """
        Loads detailed information for the current authenticated user.

        Args:
            None

        Returns:
            aiobale.types.FullUser: Detailed information about the current user.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peers = [InfoPeer(id=self.id, type=ChatType.PRIVATE)]
        result = await self.load_full_users(peers=peers)
        return result[0]

    async def load_users(self, peers: List[Union[Peer, InfoPeer]]) -> List[User]:
        """
        Loads basic information for a list of users or peers.

        Args:
            peers (List[Union[aiobale.types.Peer, aiobale.types.InfoPeer]]): List of Peer or InfoPeer objects.

        Returns:
            List[aiobale.types.User]: List of User objects with basic information.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peers = [
            InfoPeer(id=peer.id, type=peer.type) if isinstance(peer, Peer) else peer
            for peer in peers
        ]

        call = LoadUsers(peers=peers)

        result: UsersResponse = await self(call)
        return result.data

    async def load_user(self, chat_id: int, chat_type: ChatType) -> User:
        """
        Loads basic information for a single user or peer.

        Args:
            chat_id (int): The ID of the user or peer.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            aiobale.types.User: Basic information about the user.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peers = [InfoPeer(id=chat_id, type=chat_type)]
        result = await self.load_users(peers=peers)
        return result[0]

    async def get_me(self) -> FullUser:
        """
        Loads basic information for the current authenticated user.

        Args:
            None

        Returns:
            aiobale.types.User: Basic information about the current user.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peers = [InfoPeer(id=self.id, type=ChatType.PRIVATE)]
        result = await self.load_users(peers=peers)
        return result[0]

    async def edit_user_local_name(
        self, name: str, user_id: int, access_hash: int = 1
    ) -> DefaultResponse:
        """
        Edits the local name for a user in your contacts.

        Args:
            name (str): The new local name.
            user_id (int): The user ID to edit.
            access_hash (int, optional): Access hash for the user. Defaults to 1.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = EditUserLocalName(user_id=user_id, name=name, access_hash=access_hash)

        return await self(call)

    async def block_user(self, user_id: int) -> DefaultResponse:
        """
        Blocks a user, preventing them from contacting you.

        Args:
            user_id (int): The user ID to block.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the block operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        info_peer = InfoPeer(id=user_id, type=ChatType.PRIVATE)
        call = BlockUser(peer=info_peer)

        return await self(call)

    async def unblock_user(self, user_id: int) -> DefaultResponse:
        """
        Unblocks a previously blocked user.

        Args:
            user_id (int): The user ID to unblock.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the unblock operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        info_peer = InfoPeer(id=user_id, type=ChatType.PRIVATE)
        call = UnblockUser(peer=info_peer)

        return await self(call)

    async def load_blocked_users(self) -> List[InfoPeer]:
        """
        Loads the list of users you have blocked.

        Args:
            None

        Returns:
            List[aiobale.types.InfoPeer]: List of blocked users.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = LoadBlockedUsers()
        result: BlockedUsersResponse = await self(call)
        return result.users

    async def load_contacts(self) -> List[InfoPeer]:
        """
        Loads your contact list.

        Args:
            None

        Returns:
            List[aiobale.types.InfoPeer]: List of contacts.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = GetContacts()
        result: BannedUsersResponse = await self(call)
        return result.users

    async def search_contact(self, phone_number: str) -> Optional[InfoPeer]:
        """
        Searches for a contact by phone number.

        Args:
            phone_number (str): The phone number to search for.
                Phone number must be in international format, starting with the country code (without leading zero).
                For example: 989123456789 (country code 98 for Iran, then the rest of the number).

        Returns:
            Optional[aiobale.types.InfoPeer]: The found contact, or None if not found.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        phone_number = phone_number.replace("+", "")
        call = SearchContact(request=phone_number)

        result: ContactResponse = await self(call)
        return result.user

    async def search_username(self, username: str) -> ContactResponse:
        """
        Searches for a user, bot, group, or channel by username.

        Args:
            username (str): The username to search for.

        Returns:
            aiobale.types.responses.ContactResponse: The response containing the found contact.
                - If the username belongs to a user or bot, the result will be in the `user` field.
                - If the username belongs to a group or channel, the result will be in the `group` field.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = SearchContact(request=username)
        return await self(call)

    async def import_contacts(self, contacts: List[Tuple[int, str]]) -> List[InfoPeer]:
        """
        Imports a list of contacts into your account.

        Args:
            contacts (List[Tuple[int, str]]): List of tuples containing phone number and name.
            Phone numbers must be in international format, starting with the country code (without leading zero).
            For example: 989123456789 (country code 98 for Iran, then the rest of the number).

        Returns:
            List[aiobale.types.InfoPeer]: List of imported contacts.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        contacts = [
            ContactData(phone_number=contact[0], name=StringValue(value=contact[1]))
            for contact in contacts
        ]

        call = ImportContacts(phones=contacts)
        result: ContactsResponse = await self(call)
        return result.peers

    async def reset_contacts(self) -> DefaultResponse:
        """
        Removes all contacts from your account.

        Args:
            None

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the reset operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = ResetContacts()
        return await self(call)

    async def remove_contact(self, user_id: int) -> DefaultResponse:
        """
        Removes a contact from your account.

        Args:
            user_id (int): The user ID to remove.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the remove operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = RemoveContact(user_id=user_id)
        return await self(call)

    async def add_contact(self, user_id: int) -> DefaultResponse:
        """
        Adds a user to your contacts.

        Args:
            user_id (int): The user ID to add.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the add operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = AddContact(user_id=user_id)
        return await self(call)

    async def set_online(self, is_online: bool, timeout: int) -> DefaultResponse:
        """
        Sets your online status.

        Args:
            is_online (bool): True to set online, False to set offline.
            timeout (int): Timeout in seconds for online status.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = SetOnline(is_online=is_online, timeout=timeout)
        return await self(call)

    async def report_chat(
        self,
        chat_id: int,
        chat_type: ChatType,
        reason: Optional[str] = None,
        kind: ReportKind = ReportKind.SPAM,
    ) -> DefaultResponse:
        """
        Reports a chat for spam or other reasons.

        Args:
            chat_id (int): The chat ID to report.
            chat_type (aiobale.enums.ChatType): The type of chat.
            reason (Optional[str], optional): Description of the report. Defaults to None.
            kind (aiobale.enums.ReportKind, optional): Type of report. Defaults to SPAM.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the report operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer_report = PeerReport(
            source=PeerSource.DIALOGS, peer=Peer(id=chat_id, type=chat_type)
        )
        report = Report(kind=kind, description=reason, peer_report=peer_report)
        call = SendReport(report_body=report)
        return await self(call)

    async def report_messages(
        self,
        chat_id: int,
        chat_type: ChatType,
        messages: List[Union[Message, InfoMessage, OtherMessage]],
        reason: Optional[str] = None,
        kind: ReportKind = ReportKind.SPAM,
    ) -> DefaultResponse:
        """
        Reports one or more messages for spam or other reasons.

        Args:
            chat_id (int): The chat ID containing the messages.
            chat_type (aiobale.enums.ChatType): The type of chat.
            messages (List[Union[aiobale.types.Message, aiobale.types.InfoMessage, aiobale.types.OtherMessage]]): Messages to report.
            reason (Optional[str], optional): Description of the report. Defaults to None.
            kind (aiobale.enums.ReportKind, optional): Type of report. Defaults to SPAM.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the report operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        other_messages = [self._ensure_other_message(message) for message in messages]

        message_report = MessageReport(
            messages=other_messages, peer=Peer(id=chat_id, type=chat_type)
        )
        report = Report(kind=kind, description=reason, message_report=message_report)
        call = SendReport(report_body=report)
        return await self(call)

    async def report_message(
        self,
        chat_id: int,
        chat_type: ChatType,
        message: Union[Message, InfoMessage, OtherMessage],
        reason: Optional[str] = None,
        kind: ReportKind = ReportKind.SPAM,
    ) -> DefaultResponse:
        """
        Reports a single message for spam or other reasons.

        Args:
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.
            message (Union[aiobale.types.Message, aiobale.types.InfoMessage, aiobale.types.OtherMessage]): The message to report.
            reason (Optional[str], optional): Description of the report. Defaults to None.
            kind (aiobale.enums.ReportKind, optional): Type of report. Defaults to SPAM.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the report operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        return await self.report_messages(
            chat_id=chat_id,
            chat_type=chat_type,
            messages=[message],
            reason=reason,
            kind=kind,
        )

    async def start_typing(
        self,
        chat_id: int,
        chat_type: ChatType,
        typing_mode: TypingMode = TypingMode.TEXT,
    ) -> DefaultResponse:
        """
        Notifies the server that you are performing an action (typing, uploading, etc.) in a chat.

        Args:
            chat_id (int): The chat ID.
            chat_type (aiobale.enums.ChatType): The type of chat.
            typing_mode (aiobale.enums.TypingMode, optional): The type of action (not just typing). Defaults to TEXT.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Note:
            This method is used to indicate any activity (not just typing), such as sending a photo, uploading a file, etc.
            The meaning depends on the selected TypingMode.
        """
        call = Typing(peer=Peer(id=chat_id, type=chat_type), typing_type=typing_mode)
        return await self(call)

    async def stop_typing(
        self,
        chat_id: int,
        chat_type: ChatType,
        typing_mode: TypingMode = TypingMode.TEXT,
    ) -> DefaultResponse:
        """
        Notifies the server that you have stopped performing an action (typing, uploading, etc.) in a chat.

        Args:
            chat_id (int): The chat ID.
            chat_type (aiobale.enums.ChatType): The type of chat.
            typing_mode (aiobale.enums.TypingMode, optional): The type of action (not just typing). Defaults to TEXT.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Note:
            This method is used to indicate stopping any activity (not just typing), such as sending a photo, uploading a file, etc.
            The meaning depends on the selected TypingMode.
        """
        call = StopTyping(
            peer=Peer(id=chat_id, type=chat_type), typing_type=typing_mode
        )
        return await self(call)

    async def get_parameters(self) -> List[ExtKeyValue]:
        """
        Retrieves a list of key-value parameters for the current user or session.

        These parameters are typically used for privacy settings, chat drafts, and other configuration options.
        For more information about available parameters and their usage, please refer to our website.

        Args:
            None

        Returns:
            List[aiobale.types.ExtKeyValue]: A list of key-value pairs representing user/session parameters.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = GetParameters()
        result: ParametersResponse = await self(call)
        return result.params

    async def edit_parameter(self, key: str, value: str) -> DefaultResponse:
        """
        Edits or sets a specific parameter for the current user or session.

        Parameters can be used for privacy settings, chat drafts, and other customizations.
        For details on available keys and their effects, check our website.

        Args:
            key (str): The parameter key to edit.
            value (str): The new value for the parameter.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        call = EditParameter(key=key, value=value)
        return await self(call)

    async def get_messages_reactions(
        self,
        messages: List[Union[Message, InfoMessage, OtherMessage]],
        chat_id: int,
        chat_type: ChatType,
    ) -> List[MessageReactions]:
        """
        Retrieves reactions for a list of messages in a specific chat.

        Useful for displaying which users have reacted to messages and what reactions were used.

        Args:
            messages (List[Union[aiobale.types.Message, InfoMessage, OtherMessage]]): The messages to get reactions for.
            chat_id (int): The chat ID containing the messages.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            List[aiobale.types.MessageReactions]: List of reactions data for each message.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        other_messages = [self._ensure_other_message(message) for message in messages]
        peer = Peer(id=chat_id, type=chat_type)

        call = GetMessagesReactions(
            peer=peer,
            message_ids=other_messages,
            origin_peer=peer,
            origin_message_ids=other_messages,
        )
        result: ReactionsResponse = await self(call)
        return result.messages

    async def get_message_reactions(
        self,
        message: Union[Message, InfoMessage, OtherMessage],
        chat_id: int,
        chat_type: ChatType,
    ) -> Optional[MessageReactions]:
        """
        Retrieves reactions for a single message in a chat.

        Args:
            message (Union[aiobale.types.Message, InfoMessage, OtherMessage]): The message to get reactions for.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            Optional[aiobale.types.MessageReactions]: Reactions for the message, or None if not found.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        result = await self.get_messages_reactions(
            messages=[message], chat_id=chat_id, chat_type=chat_type
        )
        return result[0] if result else None

    async def get_reaction_list(
        self,
        emojy: str,
        message: Union[Message, InfoMessage, OtherMessage],
        chat_id: int,
        chat_type: ChatType,
        page: int = 1,
        limit: int = 20,
    ) -> List[ReactionData]:
        """
        Retrieves a paginated list of users who reacted to a message with a specific emoji.

        Useful for displaying which users used a particular reaction on a message.

        Args:
            emojy (str): The emoji to filter reactions by.
            message (Union[aiobale.types.Message, InfoMessage, OtherMessage]): The message to get reactions for.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.
            page (int, optional): Page number for pagination. Defaults to 1.
            limit (int, optional): Number of results per page. Defaults to 20.

        Returns:
            List[aiobale.types.ReactionData]: List of users and their reaction details.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer = Peer(id=chat_id, type=chat_type)
        call = GetMessageReactionsList(
            peer=peer,
            message_id=message.message_id,
            date=message.date,
            emojy=emojy,
            page=page,
            limit=limit,
        )
        result: ReactionListResponse = await self(call)
        return result.data

    async def set_reaction(
        self,
        emojy: str,
        message: Union[Message, InfoMessage, OtherMessage],
        chat_id: int,
        chat_type: ChatType,
    ) -> List[Reaction]:
        """
        Sets a reaction (emoji) on a specific message in a chat.

        Args:
            emojy (str): The emoji to react with.
            message (Union[aiobale.types.Message, InfoMessage, OtherMessage]): The message to react to.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            List[aiobale.types.Reaction]: List of reactions after the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer = Peer(id=chat_id, type=chat_type)
        call = MessageSetReaction(
            peer=peer, message_id=message.message_id, date=message.date, emojy=emojy
        )
        result: ReactionSentResponse = await self(call)
        return result.reactions

    async def remove_reaction(
        self,
        emojy: str,
        message: Union[Message, InfoMessage, OtherMessage],
        chat_id: int,
        chat_type: ChatType,
    ) -> List[Reaction]:
        """
        Removes a specific reaction (emoji) from a message in a chat.

        Args:
            emojy (str): The emoji to remove.
            message (Union[aiobale.types.Message, InfoMessage, OtherMessage]): The message to remove the reaction from.
            chat_id (int): The chat ID containing the message.
            chat_type (aiobale.enums.ChatType): The type of chat.

        Returns:
            List[aiobale.types.Reaction]: List of reactions after removal.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer = Peer(id=chat_id, type=chat_type)
        call = MessageRemoveReaction(
            peer=peer, message_id=message.message_id, date=message.date, emojy=emojy
        )
        result: ReactionSentResponse = await self(call)
        return result.reactions

    async def get_messages_views(
        self, messages: List[Union[Message, InfoMessage, OtherMessage]], chat_id: int
    ) -> List[MessageViews]:
        """
        Retrieves view counts for a list of messages in a chat.

        Useful for analytics and tracking message engagement.

        **Note:** This method is only applicable for channels.

        Args:
            messages (List[Union[aiobale.types.Message, InfoMessage, OtherMessage]]): The messages to get views for.
            chat_id (int): The chat ID containing the messages.

        Returns:
            List[aiobale.types.MessageViews]: List of view counts for each message.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        other_messages = [self._ensure_other_message(message) for message in messages]
        peer = Peer(id=chat_id, type=2)

        call = GetMessagesViews(peer=peer, message_ids=other_messages)
        result: ViewsResponse = await self(call)
        return result.messages

    async def get_message_views(
        self, message: Union[Message, InfoMessage, OtherMessage], chat_id: int
    ) -> List[MessageViews]:
        """
        Retrieves view count for a single message in a chat.

        **Note:** This method is only applicable for channels.

        Args:
            message (Union[aiobale.types.Message, InfoMessage, OtherMessage]): The message to get views for.
            chat_id (int): The chat ID containing the message.

        Returns:
            List[aiobale.types.MessageViews]: View count for the message.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        return await self.get_messages_views(messages=[message], chat_id=chat_id)

    async def get_full_group(self, chat_id: int) -> FullGroup:
        """
        Loads detailed information about a group or channel.

        This includes group settings, member counts, permissions, and other metadata.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.FullGroup: Detailed information about the group.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer = ShortPeer(id=chat_id)
        call = GetFullGroup(group=peer)

        result: FullGroupResponse = await self(call)
        return result.fullgroup

    async def load_members(
        self,
        chat_id: int,
        limit: int = 20,
        next_offset: Optional[int] = None,
        condition: Literal["none", "excepted_permissions", "contacts"] = "none",
    ) -> List[Member]:
        """
        Loads members of a group or channel with optional filtering.

        You can filter members by contacts or by those with specific permissions.
        For more information about available conditions and their use cases, check our website.

        Args:
            chat_id (int): The group or channel ID.
            limit (int, optional): Number of members to load. Defaults to 20.
            next_offset (Optional[int], optional): Offset for pagination. Defaults to None.
            condition (Literal["none", "excepted_permissions", "contacts"], optional): Filter condition for members.

        Returns:
            List[aiobale.types.Member]: List of group/channel members.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        peer = ShortPeer(id=chat_id)

        condition_map = {
            "contacts": Condition(contacts=BoolValue(value=True)),
            "excepted_permissions": Condition(
                excepted_permissions=BoolValue(value=True)
            ),
        }
        condition_type = condition_map.get(condition)

        call = LoadMembers(
            group=peer,
            limit=limit,
            next_offset=StringValue(value=str(next_offset)),
            condition=condition_type,
        )

        result: MembersResponse = await self(call)
        return result.members

    async def create_group(
        self,
        title: str,
        username: Optional[str] = None,
        users: Tuple[int] = (),
        group_type: GroupType = GroupType.GROUP,
    ) -> GroupCreatedResponse:
        """
        Creates a new group or channel.

        You can specify a title, optional username (for public groups/channels), initial members, and the type (group or channel).
        The restriction will be set to PUBLIC if a username is provided, otherwise PRIVATE.

        Args:
            title (str): The title of the group or channel.
            username (Optional[str], optional): The public username (for public groups/channels).
            users (Tuple[int], optional): Initial user IDs to add to the group/channel.
            group_type (aiobale.enums.GroupType, optional): The type (group or channel).

        Returns:
            aiobale.types.responses.GroupCreatedResponse: The result of the group/channel creation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.
        """
        random_id = generate_id()
        users = [ShortPeer(id=v) for v in users]
        restriction = Restriction.PUBLIC if username else Restriction.PRIVATE

        call = CreateGroup(
            random_id=random_id,
            title=title,
            users=users,
            username=StringValue(value=username),
            group_type=group_type,
            restriction=restriction,
        )

        return await self(call)

    async def create_channel(
        self, title: str, username: Optional[str] = None, users: Tuple[int] = ()
    ) -> GroupCreatedResponse:
        """
        Creates a new channel.

        Args:
            title (str): The title of the channel.
            username (Optional[str], optional): The public username for the channel (for public channels).
            users (Tuple[int], optional): Initial user IDs to add to the channel.

        Returns:
            aiobale.types.responses.GroupCreatedResponse: The result of the channel creation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method is used to create a channel, which is similar to a group but intended for broadcasting messages to a large audience. You can specify a title, an optional public username, and initial members. For more details about channel settings and restrictions, check our website.
        """
        return await self.create_group(
            title=title, username=username, users=users, group_type=GroupType.CHANNEL
        )

    async def invite_users(self, users: Tuple[int], chat_id: int) -> InviteResponse:
        """
        Invites users to a group or channel.

        Args:
            users (Tuple[int]): User IDs to invite.
            chat_id (int): The group or channel ID to invite users to.

        Returns:
            aiobale.types.responses.InviteResponse: The result of the invite operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method allows you to invite multiple users to a group or channel. The `users` argument should be a tuple of user IDs. For more information about invitation limits and restrictions, check our website.
        """
        call = InviteUsers(
            group=ShortPeer(id=chat_id),
            random_id=generate_id(12),
            users=[ShortPeer(id=u) for u in users],
        )
        return await self(call)

    async def edit_group_title(self, title: str, chat_id: int) -> DefaultResponse:
        """
        Edits the title of a group or channel.

        Args:
            title (str): The new title.
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to change the title of an existing group or channel. For title length limits and formatting rules, check our website.
        """
        call = EditGroupTitle(
            group=ShortPeer(id=chat_id), random_id=generate_id(12), title=title
        )
        return await self(call)

    async def edit_group_about(self, about: str, chat_id: int) -> DefaultResponse:
        """
        Edits the "about" section of a group or channel.

        Args:
            about (str): The new about text.
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method updates the description or "about" section for a group or channel. For content guidelines and maximum length, check our website.
        """
        call = EditGroupAbout(
            group=ShortPeer(id=chat_id),
            random_id=generate_id(12),
            about=StringValue(value=about),
        )
        return await self(call)

    async def make_group_public(self, chat_id: int, username: str) -> DefaultResponse:
        """
        Makes a group or channel public by assigning a username.

        Args:
            chat_id (int): The group or channel ID.
            username (str): The public username to assign.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method sets the group or channel restriction to PUBLIC and assigns a username, making it accessible via a public link. For username rules and restrictions, check our website.
        """
        call = SetRestriction(
            group=ShortPeer(id=chat_id),
            restriction=Restriction.PUBLIC,
            username=StringValue(value=username),
        )
        return await self(call)

    async def make_group_private(self, chat_id: int) -> DefaultResponse:
        """
        Makes a group or channel private.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method sets the group or channel restriction to PRIVATE, removing any public username and link. For more details about privacy settings, check our website.
        """
        call = SetRestriction(
            group=ShortPeer(id=chat_id), restriction=Restriction.PRIVATE
        )
        return await self(call)

    async def get_group_link(self, chat_id: int) -> str:
        """
        Retrieves the invite link for a group or channel.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            str: The invite URL.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to get the current invite link for a group or channel. This link can be shared with others to join the group. For more information about link expiration and usage, check our website.
        """
        call = GetGroupInviteURL(group=ShortPeer(id=chat_id))
        result: InviteURLResponse = await self(call)
        return result.url

    async def revoke_group_link(self, chat_id: int) -> str:
        """
        Revokes the current invite link for a group or channel and generates a new one.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            str: The new invite URL.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method invalidates the existing invite link and creates a new one. Use this to reset access if the link has been shared too widely. For more details, check our website.
        """
        call = RevokeInviteURL(group=ShortPeer(id=chat_id))
        result: InviteURLResponse = await self(call)
        return result.url

    async def leave_group(self, chat_id: int) -> DefaultResponse:
        """
        Leaves a group or channel.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the leave operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to exit a group or channel. You will no longer receive messages from it. For more information about leaving and rejoining, check our website.
        """
        call = LeaveGroup(group=ShortPeer(id=chat_id), random_id=generate_id(12))
        return await self(call)

    async def transfer_group_ownership(
        self, chat_id: int, new_owner: int
    ) -> DefaultResponse:
        """
        Transfers ownership of a group or channel to another user.

        Args:
            chat_id (int): The group or channel ID.
            new_owner (int): The user ID of the new owner.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the transfer operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method allows the current owner to assign ownership to another user. Only the owner can perform this action. For more details about ownership transfer, check our website.
        """
        call = TransferOwnership(group=ShortPeer(id=chat_id), new_owner=new_owner)
        return await self(call)

    async def make_user_admin(
        self, chat_id: int, user_id: int, admin_name: Optional[str] = None
    ) -> DefaultResponse:
        """
        Assigns admin privileges to a user in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            user_id (int): The user ID to make admin.
            admin_name (Optional[str], optional): Custom admin name (optional).

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to promote a user to admin status. You can optionally assign a custom admin name.
        Note: To assign specific admin rights and permissions, you must use the `set_member_permissions` method after creating the admin.
        For more information about admin roles and permissions, check our website.
        """
        call = MakeUserAdmin(
            group=ShortPeer(id=chat_id),
            user=ShortPeer(id=user_id),
            admin_name=StringValue(value=admin_name),
        )
        return await self(call)

    async def remove_admin(self, chat_id: int, user_id: int) -> DefaultResponse:
        """
        Removes admin privileges from a user in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            user_id (int): The user ID to remove as admin.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method demotes an admin to a regular member. For more information about admin management, check our website.
        """
        call = RemoveUserAdmin(group=ShortPeer(id=chat_id), user=ShortPeer(id=user_id))
        return await self(call)

    async def kick_user(self, chat_id: int, user_id: int) -> DefaultResponse:
        """
        Removes a user from a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            user_id (int): The user ID to remove.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the kick operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to forcibly remove a user from a group or channel. For more details about kicking users and restrictions, check our website.
        """
        call = KickUser(
            group=ShortPeer(id=chat_id),
            user=ShortPeer(id=user_id),
            random_id=generate_id(12),
        )
        return await self(call)

    async def join_chat(self, token_or_url: str) -> JoinedGroupResponse:
        """
        Joins a group or channel using an invite token or URL.

        Args:
            token_or_url (str): The invite token or URL.

        Returns:
            aiobale.types.responses.JoinedGroupResponse: The result of the join operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to join a group or channel via an invite link. The token is extracted automatically from the URL if needed. For more information about joining groups, check our website.
        """
        token = extract_join_token(token_or_url)
        call = JoinGroup(token=token)
        return await self(call)

    async def join_public_chat(self, chat_id: int) -> JoinedGroupResponse:
        """
        Joins a public group or channel by its ID.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.JoinedGroupResponse: The result of the join operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method allows you to join a public group or channel directly by its ID. For more details about public chats, check our website.
        """
        call = JoinPublicGroup(peer=Peer(id=chat_id, type=ChatType.GROUP))
        return await self(call)

    async def pin_group_message(
        self,
        message: Union[Message, MessageData, InfoMessage, OtherMessage],
        chat_id: int,
    ) -> DefaultResponse:
        """
        Pins a message in a group or channel.

        Args:
            message (Union[aiobale.types.Message, MessageData, InfoMessage, OtherMessage]): The message to pin.
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the pin operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to highlight important messages by pinning them in a group or channel. For more information about pin limits and visibility, check our website.
        """
        call = PinGroupMessage(
            group=ShortPeer(id=chat_id),
            message_id=message.message_id,
            date=message.date,
        )
        return await self(call)

    async def unpin_group_message(
        self,
        message: Union[Message, MessageData, InfoMessage, OtherMessage],
        chat_id: int,
    ) -> DefaultResponse:
        """
        Unpins a specific message in a group or channel.

        Args:
            message (Union[aiobale.types.Message, MessageData, InfoMessage, OtherMessage]): The message to unpin.
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the unpin operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method removes a pinned message from the group or channel. For more details about pin management, check our website.
        """
        call = RemoveSinglePin(
            group=ShortPeer(id=chat_id),
            message_id=message.message_id,
            date=message.date,
        )
        return await self(call)

    async def remove_group_pins(self, chat_id: int) -> DefaultResponse:
        """
        Removes all pinned messages from a group or channel.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to clear all pinned messages at once. For more information about pin limits and management, check our website.
        """
        call = RemoveAllPins(group=ShortPeer(id=chat_id))
        return await self(call)

    async def get_group_pins(
        self, chat_id: int, page: int = 1, limit: int = 20
    ) -> GetPinsResponse:
        """
        Retrieves a paginated list of pinned messages in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            page (int, optional): Page number for pagination. Defaults to 1.
            limit (int, optional): Number of results per page. Defaults to 20.

        Returns:
            aiobale.types.responses.GetPinsResponse: The response containing pinned messages.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to view all pinned messages, with support for pagination. For more details about pin history and limits, check our website.
        """
        call = GetPins(group=ShortPeer(id=chat_id), page=page, limit=limit)
        return await self(call)

    async def edit_chat_username(self, chat_id: int, username: str) -> DefaultResponse:
        """
        Edits the public username of a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            username (str): The new public username.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the edit operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method changes the public username, which affects the group's or channel's public link. For username rules and restrictions, check our website.
        """
        call = EditChannelUsername(
            group=ShortPeer(id=chat_id), username=username, random_id=generate_id(12)
        )
        return await self(call)

    async def get_member_permissions(self, chat_id: int, user_id: int) -> Permissions:
        """
        Retrieves the permissions for a specific member in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            user_id (int): The user ID of the member.

        Returns:
            aiobale.types.Permissions: The permissions object for the member.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to view what actions a member can perform in a group or channel. For more details about permission types, check our website.
        """
        call = GetMemberPermissions(
            group=ShortPeer(id=chat_id), user=ShortPeer(id=user_id)
        )
        result: MemberPermissionsResponse = await self(call)
        return result.permissions

    async def set_member_permissions(
        self, chat_id: int, user_id: int, permissions: Permissions
    ) -> DefaultResponse:
        """
        Sets custom permissions for a member in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            user_id (int): The user ID of the member.
            permissions (aiobale.types.Permissions): The permissions to assign.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method allows you to customize what a member can do, such as sending messages or managing pins.
        Note: This is the only way to assign specific rights to admins in a group or channel. After creating a new admin, use this method to set their permissions and rights. For more information about permission settings, check our website.
        """
        call = SetMemberPermissions(
            group=ShortPeer(id=chat_id),
            user=ShortPeer(id=user_id),
            permissions=permissions,
        )
        return await self(call)

    async def set_group_permissions(
        self, chat_id: int, permissions: Permissions
    ) -> DefaultResponse:
        """
        Sets default permissions for all members in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            permissions (aiobale.types.Permissions): The default permissions to assign.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to set the baseline permissions for all members. Individual permissions can still be customized. For more details, check our website.
        """
        call = SetGroupDefaultPermissions(
            group=ShortPeer(id=chat_id),
            permissions=permissions,
        )
        return await self(call)

    async def get_banned_users(self, chat_id: int) -> List[BanData]:
        """
        Retrieves a list of banned users in a group or channel.

        Args:
            chat_id (int): The group or channel ID.

        Returns:
            List[aiobale.types.BanData]: List of banned users and their ban details.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to view users who have been banned, including ban reasons and durations. For more details about banning policies, check our website.
        """
        call = GetBannedUsers(group=ShortPeer(id=chat_id))
        result: BannedUsersResponse = await self(call)
        return result.users

    async def unban_user(self, chat_id: int, user_id: int) -> DefaultResponse:
        """
        Unbans a user in a group or channel.

        Args:
            chat_id (int): The group or channel ID.
            user_id (int): The user ID to unban.

        Returns:
            aiobale.types.responses.DefaultResponse: The result of the unban operation.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method restores access for a previously banned user. For more information about ban management, check our website.
        """
        call = UnbanUser(group=ShortPeer(id=chat_id), user=ShortPeer(id=user_id))
        return await self(call)

    async def get_group_preview(self, token_or_url: str) -> FullGroup:
        """
        Retrieves a preview of a group or channel using an invite token or URL.

        Args:
            token_or_url (str): The invite token or URL.

        Returns:
            aiobale.types.FullGroup: Detailed information about the group or channel.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to view group/channel details before joining, such as title and member count. For more information about previews, check our website.
        """
        token = extract_join_token(token_or_url)
        call = GetGroupPreview(token=token)
        result: FullGroupResponse = await self(call)
        return result.fullgroup

    async def get_file(self, file_id: int, access_hash: int) -> Optional[FileURL]:
        """
        Retrieves a direct file URL for downloading media stored on Bale servers.

        Args:
            file_id (int): Unique identifier of the file.
            access_hash (int): Access hash associated with the file, used for validation.

        Returns:
            Optional[aiobale.types.FileURL]: File URL and metadata, or None if not found.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Use this method to retrieve download links for existing media such as photos, videos, or documents.
        """
        call = GetFileUrl(file=FileInfo(file_id=file_id, access_hash=access_hash))
        result: FileURLResponse = await self(call)
        return result.file_urls[0] if result.file_urls else None

    async def download_file(
        self,
        file_id: int,
        access_hash: int,
        destination: Optional[Union[BinaryIO, pathlib.Path, str]] = None,
        seek: bool = True,
    ) -> Optional[BinaryIO]:
        """
        Downloads a file from Bale servers using its file ID and access hash.

        Args:
            file_id (int): Unique identifier of the file.
            access_hash (int): Access hash for the file.
            destination (Optional[Union[BinaryIO, pathlib.Path, str]]): File-like object or file path to save the file to.
                - If None, returns the file content in a `BytesIO` object.
            seek (bool): Whether to seek the returned BinaryIO to the beginning. Default is True.

        Returns:
            Optional[BinaryIO]: The file content in a BinaryIO object if destination was None or BinaryIO. Otherwise, None.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        This method is suitable for downloading files directly into memory or saving them to disk. Make sure to use `seek=False`
        if you want to avoid rewinding the stream.
        """
        file_info = await self.get_file(file_id, access_hash)

        if destination is None:
            destination = io.BytesIO()

        stream = self.session.stream_content(
            url=file_info.url,
            chunk_size=file_info.chunk_size,
            raise_for_status=True,
        )

        try:
            if isinstance(destination, (str, pathlib.Path)):
                await self.__download_file(destination=destination, stream=stream)
                return None
            return await self.__download_file_binary_io(
                destination=destination, seek=seek, stream=stream
            )
        finally:
            await stream.aclose()

    def _build_chat(
        self, chat_id: Optional[int], chat_type: Optional[ChatType]
    ) -> Optional[Chat]:
        if chat_id is None or chat_type is None:
            return None
        return Chat(id=chat_id, type=chat_type)

    async def get_file_upload_url(
        self,
        size: int,
        name: str,
        mime_type: str,
        chat: Optional[Chat] = None,
        send_type: Optional[SendType] = None,
    ) -> FileUploadInfo:
        """
        Requests an upload URL from Bale's server for uploading a file.

        Args:
            size (int): Size of the file in bytes.
            name (str): File name including extension.
            mime_type (str): MIME type of the file (e.g., 'image/jpeg', 'video/mp4').
            chat (Optional[Chat]): Target chat to associate the upload with.
            send_type (Optional[SendType]): Optional hint about the file's intended use (e.g., voice, gif).

        Returns:
            aiobale.types.FileUploadInfo: Contains upload URL, chunk size, and file ID.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Note:
            You may omit `chat` and `send_type` when the upload is not directly tied to a specific message or chat —
            for example, when uploading a profile picture or avatar.
        """
        call = GetFileUploadUrl(
            expected_size=size,
            user_id=self.id,
            name=name,
            mime_type=mime_type,
            chat=chat,
            send_type=SendTypeModel(type=send_type),
        )
        return await self(call)

    async def upload_file(
        self,
        file: FileInput,
        chat_id: Optional[int] = None,
        chat_type: Optional[ChatType] = None,
        send_type: Optional[SendType] = None,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> FileDetails:
        """
        Uploads a file to Bale servers and returns its metadata.

        Args:
            file (FileInput): A `FileInput` object representing the file to be uploaded.
            chat_id (Optional[int]): ID of the target chat (optional).
            chat_type (Optional[ChatType]): Type of the target chat (e.g., user, group).
            send_type (Optional[SendType]): Optional hint for how the file will be used (e.g., voice, gif).
            progress_callback (Optional[Callable[[int, Optional[int]], None]]): Callback for upload progress,
                called with bytes sent and total size.

        Returns:
            aiobale.types.FileDetails: Information about the uploaded file including file ID, name, size, and MIME type.

        Raises:
            BaleError: If the server returns an error.
            AiobaleError: For client-side errors.

        Note:
            `chat_id`, `chat_type`, and `send_type` can be omitted when uploading files for non-message-related purposes,
            such as updating a user or group profile photo.
        """
        file_info = file.info
        chat = self._build_chat(chat_id, chat_type)

        upload_info = await self.get_file_upload_url(
            size=file_info.size,
            name=file_info.name,
            mime_type=file_info.mime_type,
            chat=chat,
            send_type=send_type,
        )

        await self.session.upload(
            file=file,
            url=upload_info.url,
            token=self.__token,
            chunk_size=upload_info.chunk_size,
            progress_callback=progress_callback,
        )

        return FileDetails(
            name=file_info.name,
            size=file_info.size,
            mime_type=file_info.mime_type,
            file_id=upload_info.file_id,
            access_hash=self.id,
        )

    async def _send_file_message(
        self,
        file: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        message_id: Optional[int] = None,
        send_type: SendType = SendType.DOCUMENT,
        thumb: Optional[Thumbnail] = None,
        ext: Optional[DocumentsExt] = None,
        use_own_content: bool = False,
    ) -> Message:
        if isinstance(file, FileInput):
            file_info = await self.upload_file(
                file=file, chat_id=chat_id, chat_type=chat_type, send_type=send_type
            )
        else:
            file_info = file

        chat = self._build_chat(chat_id, chat_type)
        peer = self._resolve_peer(chat)

        message_id = message_id or generate_id()

        if isinstance(file_info, DocumentMessage) and use_own_content:
            document = file_info
        else:
            if caption is not None:
                caption = MessageCaption(content=caption)

            document = DocumentMessage(
                file_id=file_info.file_id,
                size=file_info.size,
                name=file_info.name,
                mime_type=file_info.mime_type,
                access_hash=file_info.access_hash,
                caption=caption,
                thumb=thumb,
                ext=ext,
            )

        content = MessageContent(document=document)

        if reply_to is not None:
            reply_to = self._ensure_info_message(reply_to)

        call = SendMessage(
            peer=peer,
            message_id=message_id,
            content=content,
            chat=chat,
            reply_to=reply_to,
        )

        result: MessageResponse = await self(call)
        return result.message

    async def send_document(
        self,
        file: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        message_id: Optional[int] = None,
        use_own_content: bool = False,
    ) -> Message:
        """
        Sends a document file to the specified chat.

        Args:
            file (Union[FileDetails, DocumentMessage, FileInput]): File or message representing the document.
            chat_id (int): ID of the target chat.
            chat_type (ChatType): Type of the chat (user, group, etc.).
            caption (Optional[str]): Text to accompany the document.
            reply_to (Optional[Union[Message, InfoMessage]]): Optional message to reply to.
            message_id (Optional[int]): Optional custom message ID.
            use_own_content (bool, optional): Whether to send the file using the provided content instead of only using file ID and access hash. Defaults to False.

        Returns:
            aiobale.types.Message: The message containing the sent document.

        Note:
            No additional metadata is required, but sending descriptive captions helps users identify the file.
        """
        return await self._send_file_message(
            file=file,
            chat_id=chat_id,
            chat_type=chat_type,
            caption=caption,
            reply_to=reply_to,
            message_id=message_id,
            send_type=SendType.DOCUMENT,
            use_own_content=use_own_content,
        )

    async def _get_thumb(
        self, cover_thumb: FileInput, cover_width: int, cover_height: int
    ) -> Thumbnail:
        if cover_thumb.info.size > 2 * 1024:
            raise AiobaleError("Cover should not be larger than 2KB")

        thumb_width = 50
        thumb_height = int((thumb_width / cover_width) * cover_height)
        return Thumbnail(
            w=thumb_width, h=thumb_height, image=await cover_thumb.get_content()
        )

    async def send_photo(
        self,
        photo: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Sends a photo to the specified chat.

        Args:
            photo (Union[FileDetails, DocumentMessage, FileInput]): The image file to send.
            chat_id (int): ID of the target chat.
            chat_type (ChatType): Type of the chat.
            caption (Optional[str]): Caption to accompany the photo.
            reply_to (Optional[Union[Message, InfoMessage]]): Optional message to reply to.
            cover_thumb (Optional[FileInput]): Small preview thumbnail (≤ 2 KB).
            cover_width (int): Width of the photo in pixels. Default is 1000.
            cover_height (int): Height of the photo in pixels. Default is 1000.
            message_id (Optional[int]): Optional custom message ID.

        Returns:
            aiobale.types.Message: The message containing the sent photo.

        Note:
            Providing `cover_thumb`, `cover_width`, and `cover_height` is optional but enhances preview display in Bale apps.
            The `cover_thumb` must be no larger than 2 KB.
        """
        if cover_thumb is not None:
            cover_thumb = await self._get_thumb(
                cover_thumb=cover_thumb,
                cover_width=cover_width,
                cover_height=cover_height,
            )

        ext = DocumentsExt(photo=PhotoExt(w=cover_width, h=cover_height))
        return await self._send_file_message(
            file=photo,
            chat_id=chat_id,
            chat_type=chat_type,
            caption=caption,
            reply_to=reply_to,
            message_id=message_id,
            send_type=SendType.PHOTO,
            thumb=cover_thumb,
            ext=ext,
        )

    async def send_video(
        self,
        video: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Sends a video file to the specified chat.

        Args:
            video (Union[FileDetails, DocumentMessage, FileInput]): The video file to send.
            chat_id (int): ID of the target chat.
            chat_type (ChatType): Type of the chat.
            caption (Optional[str]): Caption for the video.
            reply_to (Optional[Union[Message, InfoMessage]]): Optional message to reply to.
            cover_thumb (Optional[FileInput]): Preview thumbnail (≤ 2 KB).
            cover_width (int): Width of the video in pixels. Default is 1000.
            cover_height (int): Height of the video in pixels. Default is 1000.
            duration (Optional[int]): Duration of the video in milliseconds.
            message_id (Optional[int]): Optional custom message ID.

        Returns:
            aiobale.types.Message: The message containing the sent video.

        Note:
            Providing `duration`, `cover_thumb`, and dimensions enhances the video preview before loading.
            `cover_thumb` must be at most 2 KB in size.
        """
        if cover_thumb is not None:
            cover_thumb = await self._get_thumb(
                cover_thumb=cover_thumb,
                cover_width=cover_width,
                cover_height=cover_height,
            )

        ext = DocumentsExt(
            video=VideoExt(w=cover_width, h=cover_height, duration=duration)
        )
        return await self._send_file_message(
            file=video,
            chat_id=chat_id,
            chat_type=chat_type,
            caption=caption,
            reply_to=reply_to,
            message_id=message_id,
            send_type=SendType.VIDEO,
            thumb=cover_thumb,
            ext=ext,
        )

    async def send_voice(
        self,
        voice: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Sends a voice message to the specified chat.

        Args:
            voice (Union[FileDetails, DocumentMessage, FileInput]): The voice file to send.
            chat_id (int): ID of the target chat.
            chat_type (ChatType): Type of the chat.
            caption (Optional[str]): Optional caption.
            reply_to (Optional[Union[Message, InfoMessage]]): Optional message to reply to.
            duration (Optional[int]): Duration of the voice message in milliseconds.
            message_id (Optional[int]): Optional custom message ID.

        Returns:
            aiobale.types.Message: The message containing the sent voice.

        Note:
            Supplying the `duration` is optional, but improves the waveform preview in Bale apps before playback.
        """
        ext = DocumentsExt(voice=VoiceExt(duration=duration))
        return await self._send_file_message(
            file=voice,
            chat_id=chat_id,
            chat_type=chat_type,
            caption=caption,
            reply_to=reply_to,
            message_id=message_id,
            send_type=SendType.VOICE,
            ext=ext,
        )

    async def send_audio(
        self,
        audio: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        duration: Optional[int] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        track: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Sends a music/audio file to the specified chat.

        Args:
            audio (Union[FileDetails, DocumentMessage, FileInput]): The audio file to send.
            chat_id (int): ID of the target chat.
            chat_type (ChatType): Type of the chat.
            caption (Optional[str]): Caption to accompany the audio.
            reply_to (Optional[Union[Message, InfoMessage]]): Optional message to reply to.
            duration (Optional[int]): Duration of the audio in milliseconds.
            album (Optional[str]): Album title.
            genre (Optional[str]): Music genre.
            track (Optional[str]): Track name or number.
            message_id (Optional[int]): Optional custom message ID.

        Returns:
            aiobale.types.Message: The message containing the sent audio.

        Note:
            Metadata such as `duration`, `album`, `genre`, and `track` are optional but improve the preview shown before loading the audio.
        """
        ext = DocumentsExt(
            audio=AudioExt(album=album, genre=genre, track=track, duration=duration)
        )
        return await self._send_file_message(
            file=audio,
            chat_id=chat_id,
            chat_type=chat_type,
            caption=caption,
            reply_to=reply_to,
            message_id=message_id,
            send_type=SendType.AUDIO,
            ext=ext,
        )

    async def send_gif(
        self,
        gif: Union[FileDetails, DocumentMessage, FileInput],
        chat_id: int,
        chat_type: ChatType,
        caption: Optional[str] = None,
        reply_to: Optional[Union[Message, InfoMessage]] = None,
        cover_thumb: Optional[FileInput] = None,
        cover_width: int = 1000,
        cover_height: int = 1000,
        duration: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> Message:
        """
        Sends an animated GIF to the specified chat.

        Args:
            gif (Union[FileDetails, DocumentMessage, FileInput]): The GIF file to send.
            chat_id (int): ID of the target chat.
            chat_type (ChatType): Type of the chat.
            caption (Optional[str]): Caption to accompany the GIF.
            reply_to (Optional[Union[Message, InfoMessage]]): Optional message to reply to.
            cover_thumb (Optional[FileInput]): Preview thumbnail (≤ 2 KB).
            cover_width (int): Width of the GIF in pixels. Default is 1000.
            cover_height (int): Height of the GIF in pixels. Default is 1000.
            duration (Optional[int]): Duration of the GIF in milliseconds.
            message_id (Optional[int]): Optional custom message ID.

        Returns:
            aiobale.types.Message: The message containing the sent GIF.

        Note:
            Supplying `duration`, dimensions, and `cover_thumb` improves the media preview. The thumbnail must not exceed 2 KB.
        """
        if cover_thumb is not None:
            cover_thumb = await self._get_thumb(
                cover_thumb=cover_thumb,
                cover_width=cover_width,
                cover_height=cover_height,
            )

        ext = DocumentsExt(
            gif=VideoExt(w=cover_width, h=cover_height, duration=duration)
        )
        return await self._send_file_message(
            file=gif,
            chat_id=chat_id,
            chat_type=chat_type,
            caption=caption,
            reply_to=reply_to,
            message_id=message_id,
            send_type=SendType.GIF,
            thumb=cover_thumb,
            ext=ext,
        )

    async def get_wallet(self) -> WalletResponse:
        """
        Retrieves the current user's wallet information.

        This includes the wallet's balance, token, account data, and merchant status.

        Returns:
            WalletResponse: The response containing the wallet object and its metadata.
        """
        call = GetMyKifpools()
        return await self(call)

    async def send_gift(
        self,
        chat_id: int,
        chat_type: ChatType,
        amount: int,
        message: str,
        gift_count: int = 1,
        giving_type: GivingType = GivingType.SAME,
        show_amounts: bool = True,
        token: Optional[str] = None,
    ) -> DefaultResponse:
        """
        Sends a gift to a specified chat using the sender's wallet.

        Args:
            chat_id (int): ID of the target chat (user, group, or channel).
            chat_type (ChatType): Type of the target chat.
            amount (int): Total amount of the gift to be distributed.
            message (str): Message to accompany the gift.
            gift_count (int): Number of recipients who can claim the gift. Default is 1.
            giving_type (GivingType): Distribution type (e.g., equally or randomly). Default is SAME.
            show_amounts (bool): Whether to show individual received amounts to recipients.
            token (Optional[str]): Wallet token to authorize the gift. If not provided, it is retrieved automatically.

        Returns:
            DefaultResponse: A response indicating success or failure of the operation.

        Note:
            This method replaces the deprecated `send_giftpacket()`.
            The wallet token is required to send the gift. If not supplied, it is fetched via `get_wallet()`.
        """
        chat = Chat(id=chat_id, type=chat_type)
        peer = self._resolve_peer(chat)

        if not token:
            wallet_data = await self.get_wallet()
            token = wallet_data.wallet.token

        gift = GiftPacket(
            count=gift_count,
            total_amount=amount,
            giving_type=giving_type,
            message=StringValue(value=message),
            owner_id=self.id,
            show_amounts=BoolValue(value=show_amounts),
        )

        call = SendGiftPacketWithWallet(
            peer=peer, random_id=generate_id(), gift=gift, token=token
        )
        return await self(call)

    async def open_gift(
        self, message: Union[Message, InfoMessage], receiver_token: Optional[str] = None
    ) -> PacketResponse:
        """
        Opens a gift from a specific message using the receiver's token.

        Args:
            message (Union[Message, InfoMessage]): The message that contains the gift.
            receiver_token (Optional[str]): Token to identify the receiver. If not provided, it is fetched automatically.

        Returns:
            PacketResponse: Contains details about the opening result, such as amount received, winners, and stats.

        Note:
            This method replaces the deprecated `open_packet()`.
            If `receiver_token` is not provided, the method will call `get_wallet()` to obtain the current user's token.
        """
        message = self._ensure_info_message(message, rewrite_date=True)
        if not receiver_token:
            wallet_data = await self.get_wallet()
            receiver_token = wallet_data.wallet.token

        call = OpenGiftPacket(message=message, receiver_token=receiver_token)
        return await self(call)
    
    async def send_giftpacket(
        self,
        chat_id: int,
        chat_type: ChatType,
        amount: int,
        message: str,
        gift_count: int = 1,
        giving_type: GivingType = GivingType.SAME,
        show_amounts: bool = True,
        token: Optional[str] = None,
    ) -> DefaultResponse:
        """
        DEPRECATED: Use `send_gift()` instead. This method will be removed in version 0.1.4.

        Sends a gift packet to a specified chat using the sender's wallet.

        Args:
            (same as send_gift)
        """
        warnings.warn(
            "send_giftpacket() is deprecated and will be removed in a future version. Use send_gift() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.send_gift(
            chat_id, chat_type, amount, message, gift_count, giving_type, show_amounts, token
        )

    async def open_packet(
        self, message: Union[Message, InfoMessage], receiver_token: Optional[str] = None
    ) -> PacketResponse:
        """
        DEPRECATED: Use `open_gift()` instead. This method will be removed in version 0.1.4.

        Opens a gift packet from a specific message using the receiver's token.

        Args:
            (same as open_gift)
        """
        warnings.warn(
            "open_packet() is deprecated and will be removed in a future version. Use open_gift() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.open_gift(message, receiver_token)
