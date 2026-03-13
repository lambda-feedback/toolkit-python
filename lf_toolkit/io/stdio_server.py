import sys

from typing import BinaryIO
from typing import Optional

import anyio
from anyio.streams.file import FileReadStream
from anyio.streams.file import FileWriteStream
from anyio.streams.stapled import StapledByteStream

from .handler import Handler
from .stream_io import PrefixStreamIO
from .stream_io import StreamIO
from .stream_io import StreamServer


class StdioClient(StreamIO):

    def __init__(self, stdout_buffer: BinaryIO):
        self._stdout_buffer = stdout_buffer
        self.stream = StapledByteStream(
            FileWriteStream(stdout_buffer),
            FileReadStream(sys.stdin.buffer),
        )

    async def read(self, size: int) -> bytes:
        return await self.stream.receive(size)

    async def write(self, data: bytes):
        await self.stream.send(data)
        await anyio.to_thread.run_sync(self._stdout_buffer.flush)

    async def close(self):
        await self.stream.aclose()


class StdioServer(StreamServer):

    _client: StdioClient
    _stdout_buffer: BinaryIO

    def __init__(self, handler: Optional[Handler] = None):
        super().__init__(handler)
        # Capture the real stdout buffer before redirecting sys.stdout.
        # Any print() in user code after this point goes to stderr,
        # keeping the binary Content-Length-framed protocol on fd 1 clean.
        self._stdout_buffer = sys.stdout.buffer
        sys.stdout = sys.stderr

    def wrap_io(self, client: StreamIO) -> StreamIO:
        return PrefixStreamIO(client)

    async def run(self):
        print("StdioServer started", file=sys.stderr, flush=True)
        self._client = StdioClient(self._stdout_buffer)
        await self._handle_client(self._client)