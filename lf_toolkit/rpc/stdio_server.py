import sys

from typing import Optional

import anyio

from anyio.streams.stapled import StapledByteStream

from .rpc_handler import RpcHandler
from .stream_io import StreamIO
from .stream_io import StreamServer


class StdioClient(StreamIO):

    def __init__(self):
        self.stream = StapledByteStream(
            anyio.wrap_file(sys.stdout.buffer),
            anyio.wrap_file(sys.stdin.buffer),
        )

    async def read(self, size: int) -> bytes:
        return await self.stream.receive(size)

    async def write(self, data: bytes):
        await self.stream.send(data)
        await self.stream.flush()

    async def close(self):
        await self.stream.aclose()


class StdioServer(StreamServer):

    _client: StdioClient

    def __init__(self, handler: Optional[RpcHandler] = None):
        super().__init__(handler)
        self._client = StdioClient()

    async def run(self):
        await self._handle_client(self._client)