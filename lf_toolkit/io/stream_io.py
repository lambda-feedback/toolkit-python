import sys
import traceback

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
        chunk = await self.base.read(1)
        while chunk != b"\n":
            data += chunk
            chunk = await self.base.read(1)
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

        serving = True
        while serving:
            serving = await self._serve_once(io)

        await client.close()

    async def _serve_once(self, io: StreamIO) -> bool:
        """Read one request, dispatch it and write the response.

        Returns True when the session can carry on, and False once the
        stream has ended or is no longer safe to read from.
        """
        try:
            print("waiting for data...", file=sys.stderr, flush=True)
            data = await io.read(4096)
            print(f"got data: {data[:80]}", file=sys.stderr, flush=True)
        except (anyio.EndOfStream, anyio.ClosedResourceError):
            return False
        except Exception:
            # A read failure may have consumed part of a frame, so there is
            # no point in the stream we can safely resume from.
            traceback.print_exc(file=sys.stderr)
            return False

        if not data:
            return False

        try:
            print("dispatching...", file=sys.stderr, flush=True)
            response = await self.dispatch(data.decode("utf-8"))
            print(f"got response: {str(response)[:80]}", file=sys.stderr, flush=True)
        except Exception:
            # One bad request must not end the session: the frame was read in
            # full, so the stream is still aligned and the next request can be
            # served. The caller gets no reply for this one and will time out,
            # which beats every later request on this worker timing out too.
            traceback.print_exc(file=sys.stderr)
            return True

        try:
            await io.write(response.encode("utf-8"))
            print("wrote response", file=sys.stderr, flush=True)
        except (anyio.EndOfStream, anyio.ClosedResourceError):
            return False
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return False

        return True
