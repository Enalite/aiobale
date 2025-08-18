from __future__ import annotations

import asyncio
from typing import (
    AsyncGenerator,
    Dict,
    Final,
    Callable,
    Any,
    Optional,
    TYPE_CHECKING,
    Union,
)
import abc
import time

from ...utils import ProtoBuf
from ...logger import logger
from ...methods import BaleMethod, BaleType
from ...types import (
    Request,
    RequestBody,
    AuthBody,
    ExtData,
    ExtValue,
    MetaList,
    Response,
)
from ...exceptions import BaleError

if TYPE_CHECKING:
    from ..client import Client


_Decoder = Callable[..., dict]
_Encoder = Callable[..., bytes]

BALE_WS: Final[str] = "wss://next-ws.bale.ai/ws/"
BALE_URL: Final[str] = "https://next-ws.bale.ai"
DEFAULT_TIMEOUT: Final[float] = 5.0


class BaseSession(abc.ABC):
    """
    BaseSession is an abstract base class that provides the foundational structure for managing
    sessions, handling requests, and processing responses in an asynchronous environment.
    Attributes:
        ws_url (str): WebSocket URL for the session. Defaults to `BALE_WS`.
        post_url (str): URL for HTTP POST requests. Defaults to `BALE_URL`.
        decoder (_Decoder): Function to decode incoming data. Defaults to `ProtoBuf().decode`.
        encoder (_Encoder): Function to encode outgoing data. Defaults to `ProtoBuf().encode`.
        timeout (float): Default timeout for requests. Defaults to `DEFAULT_TIMEOUT`.
        session_id (int): Unique session identifier generated based on the current time.
        client (Optional[Client]): The client instance bound to this session.
        _pending_requests (Dict[int, asyncio.Future]): A dictionary mapping request IDs to their corresponding futures.
    """

    def __init__(
        self,
        ws_url: str = BALE_WS,
        post_url: str = BALE_URL,
        decoder: _Decoder = ProtoBuf().decode,
        encoder: _Encoder = ProtoBuf().encode,
        timeout: float = DEFAULT_TIMEOUT,
        show_update_errors: bool = False
    ) -> None:
        self.ws_url = ws_url
        self.post_url = post_url
        self.decoder = decoder
        self.encoder = encoder
        self.timeout = timeout
        self._request_id = 0
        self._running = False
        self.session_id = int(time.time() * 1000)
        self.show_update_errors = show_update_errors

        self.client: Optional[Client] = None
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}

    def _bind_client(self, client: Client) -> None:
        self.client = client

    @property
    def running(self) -> bool:
        return self._running

    def build_payload(self, method: BaleMethod[BaleType], request_id: int) -> bytes:
        request = Request(
            body=RequestBody(
                service=method.__service__,
                method=method.__method__,
                payload=method,
                metadata=self._get_meta_data(),
                request_id=request_id,
            )
        )

        payload = request.model_dump(by_alias=True, exclude_none=True)
        return self.encoder(payload)

    def decode_result(self, result: Any, method: BaleMethod[BaleType]) -> Any:
        result["method_data"] = method

        model_type = method.__returning__
        return model_type.model_validate(result, context={"client": self.client})

    def get_handshake_payload(self) -> bytes:
        request = Request(handshake=AuthBody(authorized=1, ready=1))

        payload = request.model_dump(by_alias=True, exclude_none=True)
        return self.encoder(payload)

    def _get_meta(self) -> dict:
        return {
            "app_version": "113466",
            "browser_type": "1",
            "browser_version": "138.0.0.0",
            "os_type": "3",
            "session_id": str(self.session_id),
            "mt_app_version": "113466",
            "mt_browser_type": "1",
            "mt_browser_version": "138.0.0.0",
            "mt_os_type": "3",
            "mt_session_id": str(self.session_id),
        }

    def _get_meta_data(self) -> MetaList:
        data = self._get_meta()

        ext = []
        for key, value in data.items():
            ext.append(ExtData(name=key, value=ExtValue(string=value)))

        return MetaList(meta_list=ext)

    async def _handle_received_data(self, data: bytes) -> None:
        data = self.decoder(data)
        try:
            received = Response.model_validate(data, context={"client": self.client})
        except Exception:
            if self.show_update_errors:
                logger.exception("Error while validating Update")
            return

        if received.update is not None:
            await self.client.handle_update(received.update.body)
            return

        if received.pong is not None:
            result = True
            request_id = f"ping_{received.pong.value}"
        elif received.response is not None:
            result = received.response
            request_id = result.number
        else:
            return

        future = self._pending_requests.pop(request_id, None)
        if future is None or future.done():
            return

        future.set_result(result)

    @abc.abstractmethod
    async def close(self) -> None:
        pass

    @abc.abstractmethod
    async def connect(self, token: str) -> None:
        pass

    @abc.abstractmethod
    async def handshake_request(self) -> None:
        pass

    @abc.abstractmethod
    async def make_request(
        self, method: BaleMethod[BaleType], timeout: Optional[int] = None
    ) -> BaleType:
        pass

    @abc.abstractmethod
    async def post(
        self,
        method: BaleMethod[BaleType],
        just_bale_type: bool = False,
        token: Optional[str] = None,
    ) -> Union[bytes, str, BaleType]:
        pass

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    @abc.abstractmethod
    async def upload(
        self,
        url: str,
        token: str,
        chunk_size: int = 4096,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> None:
        pass

    @abc.abstractmethod
    async def stream_content(
        self,
        url: str,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        pass

    @abc.abstractmethod
    async def send_bytes(
        self, data: bytes, future_key: str, timeout: Optional[int] = None
    ) -> Any:
        pass
    
    @abc.abstractmethod
    def is_closed(self) -> bool:
        pass
