from __future__ import annotations

import aiohttp
import asyncio
from typing import Any, AsyncGenerator, Callable, Optional, Dict, Union

from ...methods import BaleMethod, BaleType
from ...utils import add_header, clean_grpc
from ...exceptions import AiobaleError, BaleError
from ...types import FileInput
from .base import BaseSession


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)


class AiohttpSession(BaseSession):
    """
    A session implementation for handling WebSocket and HTTP requests using `aiohttp`.
    This class extends `BaseSession` and provides functionality for managing
    WebSocket connections, making HTTP requests, uploading files, and streaming
    content. It is specifically designed to work with the `aiohttp` library.
    Inherits:
        BaseSession: The base session class providing core functionality.
    Features:
        - WebSocket connection management.
        - HTTP request handling with custom headers and payloads.
        - File upload with progress tracking.
        - Streaming content from a URL in chunks.
        - Graceful session and WebSocket closure.
    Note:
        Ensure that the `aiohttp` library is installed and properly configured
        in your environment to use this session implementation.
    """

    def __init__(
        self, user_agent: Optional[str] = None, proxy: Optional[str] = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None

        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.proxy = proxy

    def _build_headers(self, token: str) -> Dict[str, str]:
        return {"User-Agent": self.user_agent, "Cookie": f"access_token={token}"}

    async def connect(self, token: str):
        if not self.session or self.session.closed:
            session_timeout = aiohttp.ClientTimeout(total=None)
            self.session = aiohttp.ClientSession(
                timeout=session_timeout, proxy=self.proxy
            )

        if self._running:
            raise AiobaleError("Client is already running")

        headers = self._build_headers(token)
        self.ws = await self.session.ws_connect(
            self.ws_url,
            timeout=self.timeout,
            headers=headers,
            origin="https://web.bale.ai",
        )
        self._running = True

    async def _listen(self):
        try:
            async for msg in self.ws:
                if msg.type != aiohttp.WSMsgType.BINARY:
                    continue

                asyncio.create_task(self._handle_received_data(msg.data))

        except Exception as e:
            print(f"WebSocket listening failed: {e}")
        finally:
            self._running = False

    async def send_bytes(
        self, data: bytes, future_key: str, timeout: Optional[int] = None
    ) -> Any:
        if not self.ws:
            raise RuntimeError("WebSocket is not connected")

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[future_key] = future
        await self.ws.send_bytes(data)

        try:
            return await asyncio.wait_for(future, timeout=timeout or self.timeout)
        except asyncio.TimeoutError:
            raise RuntimeError("WebSocket is not responding")

    async def make_request(
        self,
        method: BaleMethod[BaleType],
        timeout: Optional[int] = None,
    ) -> BaleType:
        if not self.ws:
            raise RuntimeError("WebSocket is not connected")

        request_id = self._next_request_id()
        payload = self.build_payload(method, request_id)

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        await self.ws.send_bytes(payload)

        try:
            response = await asyncio.wait_for(future, timeout=timeout or self.timeout)
            if response.error:
                raise BaleError(response.error.message, response.error.topic)

            return self.decode_result(response.result, method)

        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise

    async def handshake_request(self):
        payload = self.get_handshake_payload()
        await self.ws.send_bytes(payload)

    async def post(
        self,
        method: BaleMethod[BaleType],
        just_bale_type: bool = False,
        token: Optional[str] = None,
    ) -> Union[bytes, str, BaleType]:
        if not self.session:
            self.session = aiohttp.ClientSession(proxy=self.proxy)

        headers = {
            "User-Agent": self.user_agent,
            "Origin": "https://web.bale.ai",
            "content-type": "application/grpc-web+proto",
        }
        headers.update({k[0].upper() + k[1:]: v for k, v in self._get_meta().items()})
        if token is not None:
            headers.update(self._build_headers(token))

        url = f"{self.post_url}/{method.__service__}/{method.__method__}"
        data = method.model_dump(by_alias=True, exclude_none=True)
        payload = add_header(self.encoder(data))

        req = await self.session.post(url=url, headers=headers, data=payload)
        content = await req.read()
        grpc_message = req.headers.get("grpc-message")
        if grpc_message is not None:
            if just_bale_type:
                raise BaleError(grpc_message, -1)

            return grpc_message

        if method.__returning__ is None:
            return content

        result = self.decoder(clean_grpc(content))
        return method.__returning__.model_validate(result)

    async def upload(
        self,
        file: FileInput,
        url: str,
        token: str,
        chunk_size: int = 4096,
        progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> None:
        own_session = False
        session = self.session
        if session is None:
            own_session = True
            session_timeout = aiohttp.ClientTimeout(total=None)
            session = aiohttp.ClientSession(timeout=session_timeout, proxy=self.proxy)

        headers = {
            "Origin": "https://web.bale.ai",
            "content-type": "multipart/form-data",
        }
        headers.update(self._build_headers(token))

        total_size = file.info.size
        bytes_uploaded = 0

        async def chunk_generator():
            nonlocal bytes_uploaded
            async for chunk in file.read(chunk_size):
                bytes_uploaded += len(chunk)
                if progress_callback:
                    progress_callback(bytes_uploaded, total_size)
                yield chunk

        try:
            async with session.put(
                url, data=chunk_generator(), headers=headers
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise AiobaleError(
                        f"Upload failed with status {resp.status}: {text}"
                    )
        except Exception as e:
            raise AiobaleError(f"Upload error: {e}") from e
        finally:
            if own_session:
                await session.close()

    async def stream_content(
        self,
        url: str,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        session = self.session
        own_session = False

        if session is None:
            own_session = True
            session_timeout = aiohttp.ClientTimeout(total=None)
            session = aiohttp.ClientSession(timeout=session_timeout, proxy=self.proxy)

        headers = {
            "User-Agent": self.user_agent,
            "Origin": "https://web.bale.ai",
        }

        try:
            async with session.get(
                url, headers=headers, raise_for_status=raise_for_status
            ) as resp:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    yield chunk
        except Exception as e:
            raise AiobaleError(f"Upload error: {e}") from e
        finally:
            if own_session:
                await session.close()

    def is_closed(self) -> bool:
        return not self.session or self.session.closed

    async def close(self):
        self._running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        self.session = None
