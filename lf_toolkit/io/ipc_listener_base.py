from abc import ABC
from abc import abstractmethod
from typing import AsyncGenerator

from .stream_io import StreamIO


class IPCClient(StreamIO):

    @abstractmethod
    async def close(self):
        pass


class IPCListener(ABC):

    @abstractmethod
    async def listen(self) -> AsyncGenerator[IPCClient, None]:
        pass
