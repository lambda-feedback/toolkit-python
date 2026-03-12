import subprocess
import sys

import pytest
import anyio

from lf_toolkit.io.stream_io import StreamIO, PrefixStreamIO, StreamServer
from lf_toolkit.io.stdio_server import StdioServer


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_framed_message(payload: str) -> bytes:
    """Wrap a JSON string in Content-Length framing."""
    body = payload.encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    return header + body


class FakeStreamIO(StreamIO):
    """
    Simulates a bidirectional byte stream.
    Feed messages via feed(), read responses via responses.
    """

    def __init__(self):
        self._buffer = b""
        self.responses = []
        self.close_count = 0

    def feed(self, data: bytes):
        self._buffer += data

    async def read(self, size: int) -> bytes:
        if not self._buffer:
            raise anyio.EndOfStream()
        chunk = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return chunk

    async def write(self, data: bytes):
        self.responses.append(data)

    async def close(self):
        self.close_count += 1


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStdioServer:

    @pytest.fixture
    def stream(self):
        return FakeStreamIO()

    @pytest.fixture
    def server(self):
        return StdioServer()

    @pytest.mark.anyio
    async def test_handles_multiple_messages(self, stream, server):
        """
        Core fix test: the server must process multiple messages in a single
        session without closing the connection between them.
        """
        stream.feed(make_framed_message('{"jsonrpc":"2.0","method":"eval","params":{},"id":1}'))
        stream.feed(make_framed_message('{"jsonrpc":"2.0","method":"eval","params":{},"id":2}'))
        stream.feed(make_framed_message('{"jsonrpc":"2.0","method":"eval","params":{},"id":3}'))

        await server._handle_client(stream)

        assert len(stream.responses) == 3, (
            f"Expected 3 responses but got {len(stream.responses)}. "
            "Server likely closed the connection after the first message."
        )

    @pytest.mark.anyio
    async def test_closes_only_once(self, stream, server):
        """
        The client connection should be closed exactly once — after the loop
        exits — not once per message.
        """
        stream.feed(make_framed_message('{"jsonrpc":"2.0","method":"eval","params":{},"id":1}'))
        stream.feed(make_framed_message('{"jsonrpc":"2.0","method":"eval","params":{},"id":2}'))

        await server._handle_client(stream)

        assert stream.close_count == 1, (
            f"Expected close() to be called once, but it was called "
            f"{stream.close_count} times. This is the original bug."
        )

    @pytest.mark.anyio
    async def test_single_message(self, stream, server):
        """A single message round-trip should work correctly."""
        stream.feed(make_framed_message('{"jsonrpc":"2.0","method":"eval","params":{},"id":1}'))

        await server._handle_client(stream)

        assert len(stream.responses) == 1
        # Response is a framed JSON-RPC envelope
        assert b"Content-Length:" in stream.responses[0]
        assert b"jsonrpc" in stream.responses[0]

    @pytest.mark.anyio
    async def test_closes_on_empty_stream(self, stream, server):
        """Server should exit cleanly when the stream ends with no data."""
        await server._handle_client(stream)

        assert stream.close_count == 1

    @pytest.mark.anyio
    async def test_response_content(self, stream, server):
        """Verify a response is returned for each message sent."""
        messages = [
            '{"jsonrpc":"2.0","method":"eval","params":{},"id":1}',
            '{"jsonrpc":"2.0","method":"preview","params":{},"id":2}',
        ]

        for msg in messages:
            stream.feed(make_framed_message(msg))

        await server._handle_client(stream)

        assert len(stream.responses) == 2
        for response in stream.responses:
            assert b"Content-Length:" in response
            assert b"jsonrpc" in response


class TestPrefixStreamIO:

    @pytest.fixture
    def stream(self):
        return FakeStreamIO()

    @pytest.mark.anyio
    async def test_framing_round_trip(self, stream):
        """PrefixStreamIO correctly encodes and decodes Content-Length framing."""
        prefix_io = PrefixStreamIO(stream)

        payload = b'{"command": "eval"}'
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode()
        stream.feed(header + payload)

        result = await prefix_io.read(4096)
        assert result == payload

    @pytest.mark.anyio
    async def test_write_includes_content_length_header(self, stream):
        """PrefixStreamIO write includes correct Content-Length header."""
        prefix_io = PrefixStreamIO(stream)

        payload = b'{"result": "ok"}'
        await prefix_io.write(payload)

        assert len(stream.responses) == 1
        written = stream.responses[0]
        assert b"Content-Length:" in written
        assert f"{len(payload)}".encode() in written
        assert payload in written

    @pytest.mark.anyio
    async def test_raises_on_missing_content_length(self, stream):
        """PrefixStreamIO should raise if Content-Length header is absent."""
        prefix_io = PrefixStreamIO(stream)

        stream.feed(b"X-Custom-Header: something\r\n\r\n")

        with pytest.raises(ValueError, match="Content-Length"):
            await prefix_io.read(4096)

    @pytest.mark.anyio
    async def test_large_payload_does_not_raise(self, stream):
        """Payloads larger than 4096 bytes must be read without raising."""
        prefix_io = PrefixStreamIO(stream)

        payload = b"x" * 8192
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode()
        stream.feed(header + payload)

        result = await prefix_io.read(4096)
        assert result == payload

    @pytest.mark.anyio
    async def test_exact_read_of_partial_chunks(self, stream):
        """All bytes are read even when the underlying stream delivers chunks smaller than content_length."""
        prefix_io = PrefixStreamIO(stream)

        payload = b"a" * 100
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode()
        # Feed header and payload as separate tiny chunks (10 bytes each)
        full = header + payload
        for i in range(0, len(full), 10):
            stream.feed(full[i:i + 10])

        result = await prefix_io.read(4096)
        assert result == payload
        assert len(result) == 100


class TestStdioServerSubprocess:

    def test_binary_pipe_roundtrip(self):
        """
        Spawn the StdioServer as a subprocess and pipe a framed JSON-RPC
        request to its stdin (as raw bytes). Confirms sys.stdin.buffer /
        sys.stdout.buffer is used — text-mode streams would break this.
        """
        msg = b'{"jsonrpc":"2.0","id":1,"method":"eval","params":{}}'
        frame = f"Content-Length: {len(msg)}\r\n\r\n".encode() + msg

        proc = subprocess.Popen(
            [sys.executable, "-c",
             "import anyio; from lf_toolkit.io.stdio_server import StdioServer; "
             "anyio.run(StdioServer().run)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = proc.communicate(input=frame, timeout=5)

        # Must receive a framed response
        assert b"Content-Length:" in stdout, (
            f"No framed response received.\nstderr: {stderr.decode()}"
        )
        assert b"jsonrpc" in stdout
