from abc import ABC
from abc import abstractmethod
from functools import wraps
from typing import Optional

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
