from abc import ABC
from abc import abstractmethod
from functools import wraps
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Union

from ..evaluation import Result as EvaluationResult
from ..preview import Result as PreviewResult
from ..shared import Params
from .handler import Handler
from .rpc_handler import JsonRpcHandler


EvaluationFunction = Callable[
    [Any, Any, Params], Union[EvaluationResult, Awaitable[EvaluationResult]]
]

PreviewFunction = Callable[
    [Any, Params], Union[PreviewResult, Awaitable[PreviewResult]]
]


class BaseServer(ABC):

    _handler: Handler

    def __init__(self, handler: Optional[Handler] = None):
        self._handler = handler if handler is not None else JsonRpcHandler()

    @abstractmethod
    async def run(self):
        pass

    async def dispatch(self, req: str) -> str:
        return await self._handler.dispatch(req)

    def eval(self, fn: EvaluationFunction):
        return handler_decorator(self._handler, "eval", fn)

    def preview(self, fn: PreviewFunction):
        return handler_decorator(self._handler, "preview", fn)


def handler_decorator(registry: Handler, name: str, fn):
    @wraps(fn)
    def decorator():
        registry.register(name, fn)
        return fn

    return decorator()
