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
        headers = b""
        while b"\r\n\r\n" not in headers:
            headers += await self.base.read(1)
        headers_str = headers.decode("utf-8").strip()

        content_length = 0
        lines = headers_str.split("\r\n")
        for line in lines:
            line = line.strip()

            if line.startswith("Content-Length:"):
                parts = line.split(":", 1)
                content_length = int(parts[1].strip())
                break

        if content_length == 0:
            raise ValueError("Content-Length header not found or is zero")

        if content_length > size:
            raise ValueError("Content-Length is larger than the read size")

        return await self.base.read(content_length)

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
                import sys
                print("waiting for data...", file=sys.stderr, flush=True)
                data = await io.read(4096)
                print(f"got data: {data[:80]}", file=sys.stderr, flush=True)

                if not data:
                    break

                print("dispatching...", file=sys.stderr, flush=True)
                response = await self.dispatch(data.decode("utf-8"))
                print(f"got response: {str(response)[:80]}", file=sys.stderr, flush=True)

                await io.write(response.encode("utf-8"))
                print("wrote response", file=sys.stderr, flush=True)
            except anyio.EndOfStream:
                break
            except anyio.ClosedResourceError:
                break
            except Exception as e:
                import traceback
                traceback.print_exc(file=sys.stderr)
                break

        await client.close()
