import asyncio

from abc import ABC
from abc import abstractmethod
from typing import Awaitable
from typing import Callable
from typing import Dict

import anyio
import ujson

from jsonrpcserver import Error
from jsonrpcserver import Success
from jsonrpcserver import async_dispatch

from lf_toolkit.evaluation import Params


HandlerFunction = Callable[..., Awaitable[Dict]]


class RpcHandler(ABC):

    _handlers: Dict[str, HandlerFunction] = {}

    @abstractmethod
    async def dispatch(self, req: str) -> str:
        pass

    def register(self, name: str, fn: HandlerFunction):
        self._handlers[name] = fn

    async def _call_handler(self, req: str, *args, **kwargs):
        handler = self._handlers.get(req)
        if handler is None:
            raise ValueError(f"No handler for '{req}'")

        if asyncio.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        else:
            return await anyio.to_thread.run_sync(handler, *args, **kwargs)

    async def _handle_eval(self, req: dict):
        response = req.get("response", None)
        answer = req.get("answer", None)
        params = Params(req.get("params", {}))

        return await self._call_handler("eval", response, answer, params)

    async def _handle_preview(self, req: dict):
        response = req.get("response", None)
        params = Params(req.get("params", {}))

        return await self._call_handler("preview", response, params)


class JsonRpcHandler(RpcHandler):

    async def _eval(self, req: dict):
        try:
            result = await self._handle_eval(req)
            return Success(result)
        except Exception as e:
            return Error(0, str(e), e)

    async def _preview(self, req: dict):
        try:
            result = await self._handle_preview(req)
            return Success(result)
        except Exception as e:
            return Error(0, str(e), e)

    async def dispatch(self, req: str) -> str:
        return await async_dispatch(
            req,
            methods={
                "eval": self._eval,
                "preview": self._preview,
            },
            serializer=ujson.dumps,
            deserializer=ujson.loads,
        )


# def main():
#     try:
#         if len(sys.argv) != 3:
#             raise ValueError('Usage: python -m evaluation_function.main <request_file_path> <response_file_path>')

#         # Read the request file path and response file path from command-line arguments
#         request_file_path = sys.argv[1]
#         response_file_path = sys.argv[2]

#         # Read the request data from the request file
#         with open(request_file_path, 'r') as request_file:
#             request_data = json.load(request_file)

#         # Handle the request
#         command, result =handle_request(request_data)

#         # Prepare the response data
#         response = {"command": command, "result": result}

#         # Write the response data to the response file
#         with open(response_file_path, 'w') as response_file:
#             json.dump(response, response_file)

#     except Exception as e:
#         # Write any error messages to stderr
#         sys.stderr.write(str(e))
#         sys.exit(1)

# if __name__ == "__main__":
#     main()
