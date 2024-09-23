import sys

from typing import Optional

from anyio.streams.file import FileReadStream
from anyio.streams.file import FileWriteStream
from anyio.streams.stapled import StapledByteStream

from .handler import Handler
from .stream_io import PrefixStreamIO
from .stream_io import StreamIO
from .stream_io import StreamServer


class StdioClient(StreamIO):

    def __init__(self):
        self.stream = StapledByteStream(
            FileWriteStream(sys.stdout),
            FileReadStream(sys.stdin),
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

    def __init__(self, handler: Optional[Handler] = None):
        super().__init__(handler)
        self._client = StdioClient()

    def wrap_io(self, client: StreamIO) -> StreamIO:
        return PrefixStreamIO(client)

    async def run(self):
        await self._handle_client(self._client)
