import sys

from typing import Optional

import anyio

from lf_toolkit.rpc.stream_io import StreamIO

from .ipc_listener_base import IPCListener
from .rpc_handler import RpcHandler
from .stream_io import NewlineStreamIO
from .stream_io import StreamServer


def default_ipc_listener_factory(endpoint: Optional[str]) -> IPCListener:
    if sys.platform == "win32":
        from .ipc_listener_windows import NamedPipeListener

        # pipe_name = fr'\\.\pipe\{endpoint}'
        return NamedPipeListener(endpoint)
    else:
        from .ipc_listener_unix import SocketListener

        return SocketListener(endpoint)


class IPCServer(StreamServer):

    _listener: IPCListener

    def __init__(
        self,
        endpoint: Optional[str] = None,
        handler: Optional[RpcHandler] = None,
        listener_factory=default_ipc_listener_factory,
    ):
        self._listener = listener_factory(endpoint)
        super().__init__(handler)

    def wrap_io(self, client: StreamIO) -> StreamIO:
        return NewlineStreamIO(client)

    async def run(self):
        async with anyio.create_task_group() as task_group:
            async for client in self._listener.listen():
                task_group.start_soon(self._handle_client, client)
