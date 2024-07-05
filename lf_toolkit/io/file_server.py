from typing import Optional

import ujson

from anyio import open_file

from .base_server import BaseServer
from .handler import Handler


class FileHandler(Handler):

    async def dispatch(self, req: str) -> str:
        request = ujson.loads(req)
        command = request.get("command", None)
        try:
            result = await self.handle(command, request)
            response = {"command": command, "result": result}
        except Exception as e:
            response = {"command": command, "error": str(e)}
        return ujson.dumps(response)


class FileServer(BaseServer):

    _request_file_path: str
    _response_file_path: str

    def __init__(
        self,
        request_file_path: str,
        response_file_path: str,
        handler: Optional[Handler] = None,
    ):
        super().__init__(handler if handler is not None else FileHandler())
        self._request_file_path = request_file_path
        self._response_file_path = response_file_path

    async def run(self):
        async with await open_file(self._request_file_path, "r") as f:
            request = await f.read()

        response = await self.dispatch(request)

        async with await open_file(self._response_file_path, "w") as f:
            await f.write(response)
