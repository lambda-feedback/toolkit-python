import signal

from abc import ABC
from abc import abstractmethod
from functools import wraps
from typing import Optional

import anyio

from anyio.abc import CancelScope

from .rpc_handler import HandlerFunction
from .rpc_handler import JsonRpcHandler
from .rpc_handler import RpcHandler


class BaseServer(ABC):

    def __init__(self, handler: Optional[RpcHandler] = None):
        self._handler = handler if handler is not None else JsonRpcHandler()

    @abstractmethod
    async def run(self):
        pass

    async def dispatch(self, req: str) -> str:
        return await self._handler.dispatch(req)

    def eval(self, fn: HandlerFunction):
        return handler_decorator(self._handler, "eval", fn)

    def preview(self, fn: HandlerFunction):
        return handler_decorator(self._handler, "preview", fn)


def handler_decorator(registry: RpcHandler, name: str, fn: HandlerFunction):
    @wraps(fn)
    def decorator():
        registry.register(name, fn)
        return fn

    return decorator()


async def signal_handler(scope: CancelScope):
    with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for signum in signals:
            if signum == signal.SIGINT:
                print("Received SIGINT, exiting...")
            else:
                print("Received SIGTERM, exiting...")

            scope.cancel()
            return


def run(server: BaseServer):
    async def main():
        async with anyio.create_task_group() as tg:
            tg.start_soon(signal_handler, tg.cancel_scope)
            tg.start_soon(server.run)

    anyio.run(main)
