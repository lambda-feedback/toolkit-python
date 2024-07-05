from typing import AsyncGenerator
from typing import Optional

import anyio
import pywintypes
import win32file
import win32pipe

from .ipc_listener_base import IPCClient
from .ipc_listener_base import IPCListener


class NamedPipeListener(IPCListener):

    endpoint: str

    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint if endpoint is not None else r"\\.\pipe\eval"

    async def listen(self) -> AsyncGenerator[IPCClient, None]:
        while True:
            try:
                client = await self._handle_client()
                yield client
            except Exception as e:
                print(f"Exception: {e}")
                break

    async def _handle_client(self) -> AsyncGenerator[IPCClient, None]:
        # create a new named pipe instance
        pipe = win32pipe.CreateNamedPipe(
            self.endpoint,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE
            | win32pipe.PIPE_READMODE_MESSAGE
            | win32pipe.PIPE_WAIT,
            win32pipe.PIPE_UNLIMITED_INSTANCES,
            65536,
            65536,
            0,
            None,
        )

        if pipe == win32file.INVALID_HANDLE_VALUE:
            error = pywintypes.error(win32file.GetLastError())
            raise Exception(f"Failed to create named pipe {error}")

        try:
            # Wait for the client to connect
            print("Waiting for client to connect...")
            # Block until a client connects
            win32pipe.ConnectNamedPipe(pipe, None)
            print("Client connected")

            return NamedPipeClient(pipe)

        except pywintypes.error as e:
            print(f"Pipe error: {e}")
            win32file.CloseHandle(pipe)


class NamedPipeClient(IPCClient):

    def __init__(self, pipe: int):
        self.pipe = pipe

    async def read(self, size: int) -> bytes:
        return await anyio.to_thread.run_sync(
            lambda: win32file.ReadFile(self.pipe, size)[1]
        )

    async def write(self, data: bytes):
        await anyio.to_thread.run_sync(lambda: win32file.WriteFile(self.pipe, data)[1])

    async def close(self):
        win32file.CloseHandle(self.pipe)
