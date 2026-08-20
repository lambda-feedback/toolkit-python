from typing import AsyncGenerator
from typing import Optional

import anyio

from anyio.abc import SocketStream

from .ipc_listener_base import IPCClient
from .ipc_listener_base import IPCListener


class TCPListener(IPCListener):

    host: str
    port: int

    def __init__(self, address: Optional[str]):
        host, port = (address if address is not None else "127.0.0.1:7321").rsplit(
            ":", 1
        )
        self.host = host
        self.port = int(port)

    async def listen(self) -> AsyncGenerator[IPCClient, None]:
        # anyio.create_tcp_listener() returns a MultiListener (it may bind
        # more than one underlying socket, e.g. for dual-stack IPv4/IPv6),
        # which has no accept() of its own - fan its connections into a
        # single stream via serve() instead.
        send_stream, receive_stream = anyio.create_memory_object_stream(
            max_buffer_size=1000
        )

        async def handle(stream: SocketStream):
            await send_stream.send(stream)

        async with await anyio.create_tcp_listener(
            local_host=self.host, local_port=self.port
        ) as listener:
            print(f"Server listening on {self.host}:{self.port}")

            async with anyio.create_task_group() as task_group:
                task_group.start_soon(listener.serve, handle)

                async with receive_stream:
                    async for stream in receive_stream:
                        yield TCPClient(stream)


class TCPClient(IPCClient):

    stream: SocketStream

    def __init__(self, stream: SocketStream):
        self.stream = stream

    async def read(self, size: int) -> bytes:
        return await self.stream.receive(size)

    async def write(self, data: bytes):
        await self.stream.send(data)

    async def close(self):
        await self.stream.aclose()
