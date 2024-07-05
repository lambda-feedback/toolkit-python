from typing import AsyncGenerator
from typing import Optional

import anyio

from anyio.abc import SocketStream

from .ipc_listener_base import IPCClient
from .ipc_listener_base import IPCListener


class SocketListener(IPCListener):

    endpoint: str

    def __init__(self, endpoint: Optional[str]):
        self.endpoint = endpoint if endpoint is not None else "/tmp/eval.sock"

    async def listen(self) -> AsyncGenerator[IPCClient, None]:
        async with await anyio.create_unix_listener(self.endpoint) as listener:
            print(f"Server listening on {self.endpoint}")
            while True:
                try:
                    stream = await listener.accept()
                    # print("Client connected")
                    yield SocketClient(stream)
                except Exception as e:
                    print(f"Exception: {e}")
                    break


class SocketClient(IPCClient):

    stream: SocketStream

    def __init__(self, stream: SocketStream):
        self.stream = stream

    async def read(self, size: int) -> bytes:
        return await self.stream.receive(size)

    async def write(self, data: bytes):
        await self.stream.send(data)

    async def close(self):
        await self.stream.aclose()
