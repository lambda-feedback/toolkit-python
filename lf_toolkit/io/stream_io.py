import sys
from abc import ABC
from abc import abstractmethod

import anyio

from .base_server import BaseServer


class StreamIO(ABC):

    @abstractmethod
    async def read(self, size: int) -> bytes:
        pass

    @abstractmethod
    async def write(self, data: bytes):
        pass


class NewlineStreamIO:

    base: StreamIO

    def __init__(self, base: StreamIO):
        self.base = base

    async def read(self, size: int) -> bytes:
        data = b""
        while len(data) < size:
            chunk = await self.base.read(1)
            if chunk == b"\n":
                break
            data += chunk
        return data

    async def write(self, data: bytes):
        await self.base.write(data + b"\n")


class PrefixStreamIO:

    base: StreamIO

    def __init__(self, base: StreamIO):
        self.base = base

    async def read(self, size: int) -> bytes:
        # Scan line-by-line for Content-Length:, skipping any stray output.
        content_length = None
        while True:
            line = b""
            while not line.endswith(b"\n"):
                line += await self.base.read(1)
            line = line.decode("utf-8").strip()
            if line.startswith("Content-Length:"):
                _, _, value = line.partition(":")
                content_length = int(value.strip())
                break
            # skip unrecognised lines (stray stdout, other headers)

        if content_length is None or content_length == 0:
            raise ValueError("Content-Length header not found or is zero")

        # Drain remaining header lines until the blank separator.
        while True:
            line = b""
            while not line.endswith(b"\n"):
                line += await self.base.read(1)
            if line.strip() == b"":
                break

        data = b""
        while len(data) < content_length:
            chunk = await self.base.read(content_length - len(data))
            data += chunk
        return data

    async def write(self, data: bytes):
        response_headers_str = f"Content-Length: {len(data)}\r\n\r\n"
        response_bytes = response_headers_str.encode("utf-8") + data
        await self.base.write(response_bytes)


class StreamServer(BaseServer):

    def wrap_io(self, client: StreamIO) -> StreamIO:
        return client

    async def _handle_client(self, client: StreamIO):
        io = self.wrap_io(client)

        while True:
            try:
                data = await io.read(4096)

                if not data:
                    break

                response = await self.dispatch(data.decode("utf-8"))
                await io.write(response.encode("utf-8"))
            except anyio.EndOfStream:
                break
            except anyio.ClosedResourceError:
                break
            except Exception:
                import traceback
                traceback.print_exc(file=sys.stderr)
                break

        await client.close()