import ujson

from jsonrpcserver import Error
from jsonrpcserver import Success
from jsonrpcserver import async_dispatch

from .handler import Handler


class JsonRpcHandler(Handler):

    def __init__(self):
        self._methods = {
            name: jsonrpc_handler(self, name) for name in ["eval", "preview"]
        }

    async def dispatch(self, req: str) -> str:
        return await async_dispatch(
            req,
            methods=self._methods,
            serializer=ujson.dumps,
            deserializer=ujson.loads,
        )


def jsonrpc_handler(handler: Handler, name: str):
    async def wrapped(req: dict):
        try:
            result = await handler.handle(name, req)
            return Success(result)
        except Exception as e:
            return Error(0, str(e), e)

    return wrapped
