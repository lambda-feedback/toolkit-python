from typing import Optional

import anyio

from .handler import Handler
from .stream_io import NewlineStreamIO
from .stream_io import StreamIO
from .stream_io import StreamServer
from .tcp_listener import TCPListener


class TCPServer(StreamServer):

    _listener: TCPListener

    def __init__(
        self,
        address: Optional[str] = None,
        handler: Optional[Handler] = None,
    ):
        self._listener = TCPListener(address)
        super().__init__(handler)

    def wrap_io(self, client: StreamIO) -> StreamIO:
        return NewlineStreamIO(client)

    async def run(self):
        async with anyio.create_task_group() as task_group:
            async for client in self._listener.listen():
                task_group.start_soon(self._handle_client, client)
