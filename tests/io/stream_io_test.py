import pytest
import anyio

from lf_toolkit.io.stream_io import StreamIO, PrefixStreamIO, StreamServer


@pytest.fixture
def anyio_backend():
    return "asyncio"



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


class EchoServer(StreamServer):
    """
    Concrete StreamServer for testing.
    - run() is required by BaseServer (abstract) but not used in tests
      since we call _handle_client directly.
    - dispatch() is overridden to echo the raw request back, bypassing
      the real JsonRpcHandler so tests stay self-contained.
    """

    async def run(self):
        pass

    async def dispatch(self, data: str) -> str:
        return data


class BuggyStreamServer(StreamServer):
    """
    Reproduces the original bug by overriding _handle_client with
    close() inside the finally block.
    """

    async def run(self):
        pass

    async def dispatch(self, data: str) -> str:
        return data

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
            except Exception as e:
                print(f"Exception: {e}")
            finally:
                await client.close()  # BUG: closes after every message


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStreamServer:

    @pytest.fixture
    def stream(self):
        return FakeStreamIO()

    @pytest.fixture
    def server(self):
        return EchoServer()

    @pytest.fixture
    def buggy_server(self):
        return BuggyStreamServer()

    @pytest.mark.anyio
    async def test_handles_multiple_messages(self, stream, server):
        """
        Core fix test: the server must process multiple messages in a single
        session without closing the connection between them.
        """
        stream.feed(make_framed_message('{"command": "eval", "id": 1}'))
        stream.feed(make_framed_message('{"command": "eval", "id": 2}'))
        stream.feed(make_framed_message('{"command": "eval", "id": 3}'))

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
        stream.feed(make_framed_message('{"id": 1}'))
        stream.feed(make_framed_message('{"id": 2}'))

        await server._handle_client(stream)

        assert stream.close_count == 1, (
            f"Expected close() to be called once, but it was called "
            f"{stream.close_count} times. This is the original bug."
        )

    @pytest.mark.anyio
    async def test_buggy_server_closes_after_each_message(self, stream, buggy_server):
        """
        Demonstrates the original bug: close() in the finally block causes
        the stream to be closed after every message, not just at the end.
        """
        stream.feed(make_framed_message('{"id": 1}'))
        stream.feed(make_framed_message('{"id": 2}'))

        await buggy_server._handle_client(stream)

        assert stream.close_count > 1, (
            "Expected buggy server to call close() more than once, "
            "confirming the bug exists in the original code."
        )

    @pytest.mark.anyio
    async def test_single_message(self, stream, server):
        """A single message round-trip should work correctly."""
        payload = '{"command": "eval", "response": "test"}'
        stream.feed(make_framed_message(payload))

        await server._handle_client(stream)

        assert len(stream.responses) == 1
        assert payload.encode() in stream.responses[0]

    @pytest.mark.anyio
    async def test_closes_on_empty_stream(self, stream, server):
        """Server should exit cleanly when the stream ends with no data."""
        await server._handle_client(stream)

        assert stream.close_count == 1

    @pytest.mark.anyio
    async def test_response_content(self, stream, server):
        """Verify the actual response content is correct across messages."""
        messages = [
            '{"id": 1, "command": "eval"}',
            '{"id": 2, "command": "preview"}',
        ]

        for msg in messages:
            stream.feed(make_framed_message(msg))

        await server._handle_client(stream)

        assert len(stream.responses) == 2
        for i, msg in enumerate(messages):
            assert msg.encode() in stream.responses[i]


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
