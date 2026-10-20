import asyncio

from abc import ABC
from abc import abstractmethod
from typing import Callable
from typing import Dict

import anyio

from ..chat import ChatHealthResponse
from ..chat import ChatRequest
from ..chat import ChatResponse
from ..evaluation import Result as EvaluationResult
from ..shared import Command
from ..shared import Params

# JSON-RPC error code for submissions the user handler cannot process.
INVALID_SUBMISSION_CODE = 422

# JSON-RPC error code for failures of a service the user handler depends on.
# These are not failures of the evaluation function itself, so they are
# reported as 424 (Failed Dependency) rather than 5xx, matching shimmy.
UPSTREAM_ERROR_CODE = 424


class EvaluationFunctionError(Exception):
    """An error the evaluation function chose to report.

    The message is passed to the caller verbatim, and the class decides the
    JSON-RPC code (stdio/IPC) and the error code (file IO) it is reported with.
    Over JSON-RPC the error code is also sent as the error's `data`, since
    several classes share a JSON-RPC code.
    """

    rpc_code = 500
    file_code = "INTERNAL_ERROR"


class InvalidSubmissionError(EvaluationFunctionError):
    """Raised when the user handler cannot process the submitted response."""

    rpc_code = INVALID_SUBMISSION_CODE
    file_code = "INVALID_SUBMISSION"


class UpstreamTimeoutError(EvaluationFunctionError):
    """A service the evaluation function depends on did not answer in time."""

    rpc_code = UPSTREAM_ERROR_CODE
    file_code = "UPSTREAM_TIMEOUT"


class UpstreamUnavailableError(EvaluationFunctionError):
    """A service the evaluation function depends on refused or failed."""

    rpc_code = UPSTREAM_ERROR_CODE
    file_code = "UPSTREAM_UNAVAILABLE"


class Handler(ABC):

    _handlers: Dict[str, Callable]

    def __init__(self):
        self._handlers = {}

    @abstractmethod
    async def dispatch(self, req: str) -> str:
        pass

    def register(self, name: str, fn: Callable):
        self._handlers[name] = fn

    async def _call_user_handler(self, req: str, *args, **kwargs):
        handler = self._handlers.get(req)

        if handler is None:
            raise ValueError(f"No user handler for '{req}'")

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(*args, **kwargs)
            else:
                return await anyio.to_thread.run_sync(handler, *args, **kwargs)
        except EvaluationFunctionError:
            raise
        except ValueError as e:
            raise InvalidSubmissionError(str(e)) from e
        except Exception as e:
            raise ValueError(f"Error calling user handler for '{req}': {e}")

    async def handle_eval(self, req: dict):
        params = req["params"]
        response = params.get("response", None)
        answer = params.get("answer", None)
        request_params = Params(params.get("params", {}))

        result = await self._call_user_handler("eval", response, answer, request_params)

        if isinstance(result, EvaluationResult):
            return result.to_dict()

        return result

    async def handle_preview(self, req: dict):
        params = req["params"]
        response = params.get("response", None)
        request_params = Params(params.get("params", {}))

        return await self._call_user_handler("preview", response, request_params)

    async def handle_healthcheck(self, req: dict):
        from .healthcheck import run_healthcheck
        return await anyio.to_thread.run_sync(run_healthcheck)

    async def handle_chat(self, req: dict):
        params = req["params"]
        chat_request = ChatRequest.model_validate(params)

        result = await self._call_user_handler("chat", chat_request)

        if isinstance(result, ChatResponse):
            return result.model_dump(mode="json", exclude_none=True)

        return result

    async def handle_chat_health(self, req: dict):
        result = await self._call_user_handler("chat/health")

        if isinstance(result, ChatHealthResponse):
            return result.model_dump(mode="json", exclude_none=True)

        return result

    async def handle(self, name: Command, req: dict) -> dict:
        handler = getattr(self, f"handle_{name.replace('/', '_')}", None)

        if handler is None:
            raise ValueError(f"No handler for '{name}'")

        return await handler(req)
