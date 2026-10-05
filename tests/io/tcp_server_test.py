import socket

import anyio
import pytest
import ujson

from lf_toolkit.io.stream_io import StreamIO
from lf_toolkit.io.tcp_server import TCPServer


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_newline_message(payload: str) -> bytes:
    return payload.encode("utf-8") + b"\n"


class FakeStreamIO(StreamIO):

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


class TestTCPServer:

    @pytest.fixture
    def stream(self):
        return FakeStreamIO()

    @pytest.fixture
    def server(self):
        return TCPServer()

    @pytest.mark.anyio
    async def test_handles_multiple_messages_newline_framed(self, stream, server):
        server.eval(lambda response, answer, params: {"received": True})

        stream.feed(
            make_newline_message(
                ujson.dumps(
                    {"jsonrpc": "2.0", "method": "eval", "params": [{}], "id": 1}
                )
            )
        )
        stream.feed(
            make_newline_message(
                ujson.dumps(
                    {"jsonrpc": "2.0", "method": "eval", "params": [{}], "id": 2}
                )
            )
        )

        await server._handle_client(stream)

        assert len(stream.responses) == 2
        for response in stream.responses:
            assert response.endswith(b"\n")
            assert b"Content-Length:" not in response

    @pytest.mark.anyio
    async def test_closes_connection_once(self, stream, server):
        stream.feed(
            make_newline_message(
                ujson.dumps(
                    {"jsonrpc": "2.0", "method": "eval", "params": [{}], "id": 1}
                )
            )
        )

        await server._handle_client(stream)

        assert stream.close_count == 1


class TestTCPServerLive:

    @pytest.mark.anyio
    async def test_end_to_end_roundtrip(self):
        port = free_port()
        server = TCPServer(address=f"127.0.0.1:{port}")
        server.eval(lambda response, answer, params: {"is_correct": response == answer})

        async with anyio.create_task_group() as tg:
            tg.start_soon(server.run)

            request = ujson.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "eval",
                    "params": [{"response": "42", "answer": "42"}],
                    "id": 1,
                }
            )

            client = None
            for _ in range(50):
                try:
                    client = await anyio.connect_tcp("127.0.0.1", port)
                    break
                except OSError:
                    await anyio.sleep(0.05)
            assert client is not None, "TCPServer never started listening"

            await client.send(request.encode("utf-8") + b"\n")

            data = b""
            while not data.endswith(b"\n"):
                data += await client.receive(4096)
            await client.aclose()

            response = ujson.loads(data.decode("utf-8"))
            assert response["result"]["is_correct"] is True

            tg.cancel_scope.cancel()
