import ujson
import pytest

from lf_toolkit.chat import ChatCapabilities
from lf_toolkit.chat import ChatHealthResponse
from lf_toolkit.chat import ChatRequest
from lf_toolkit.chat import ChatResponse
from lf_toolkit.chat import Message
from lf_toolkit.io.rpc_handler import JsonRpcHandler
from lf_toolkit.shared.mued_api_v0_1_0 import DataPolicySupport
from lf_toolkit.shared.mued_api_v0_1_0 import HealthStatus
from lf_toolkit.shared.mued_api_v0_1_0 import Role

pytest_plugins = ('pytest_asyncio',)


class TestJsonRpcHandlerChat:

    @pytest.fixture
    def handler(self):
        return JsonRpcHandler()

    def test_registers_chat_methods(self, handler):
        assert "chat" in handler._methods
        assert "chat/health" in handler._methods

    @pytest.mark.asyncio
    async def test_dispatch_chat_round_trip(self, handler):
        def chat_fn(request: ChatRequest) -> ChatResponse:
            last = request.messages[-1]
            return ChatResponse(output=Message(role=Role.ASSISTANT, content=f"echo: {last.content}"))

        handler.register("chat", chat_fn)

        # go-ethereum's rpc.Client sends a single positional params array,
        # not a params object -- this is the actual wire shape shimmy produces.
        req = ujson.dumps({
            "jsonrpc": "2.0",
            "method": "chat",
            "params": [{"messages": [{"role": "USER", "content": "hi"}]}],
            "id": 1,
        })

        response = ujson.loads(await handler.dispatch(req))

        assert response["result"] == {"output": {"role": "ASSISTANT", "content": "echo: hi"}}

    @pytest.mark.asyncio
    async def test_dispatch_chat_health_round_trip(self, handler):
        def chat_health_fn() -> ChatHealthResponse:
            return ChatHealthResponse(
                status=HealthStatus.OK,
                capabilities=ChatCapabilities(
                    supportsChat=True,
                    supportsDataPolicy=DataPolicySupport.NOT_SUPPORTED,
                ),
            )

        handler.register("chat/health", chat_health_fn)

        req = ujson.dumps({
            "jsonrpc": "2.0",
            "method": "chat/health",
            "params": [{}],
            "id": 2,
        })

        response = ujson.loads(await handler.dispatch(req))

        assert response["result"]["status"] == "OK"
        assert response["result"]["capabilities"]["supportsChat"] is True
