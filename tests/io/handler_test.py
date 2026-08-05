import pytest

from lf_toolkit.chat import ChatCapabilities
from lf_toolkit.chat import ChatHealthResponse
from lf_toolkit.chat import ChatRequest
from lf_toolkit.chat import ChatResponse
from lf_toolkit.chat import Message
from lf_toolkit.io.file_server import FileHandler
from lf_toolkit.shared.mued_api_v0_1_0 import DataPolicySupport
from lf_toolkit.shared.mued_api_v0_1_0 import HealthStatus
from lf_toolkit.shared.mued_api_v0_1_0 import Role

pytest_plugins = ('pytest_asyncio',)


class TestHandleChat:

    @pytest.fixture
    def handler(self):
        return FileHandler()

    @pytest.mark.asyncio
    async def test_calls_registered_handler_with_chat_request(self, handler):
        received = {}

        def chat_fn(request: ChatRequest) -> ChatResponse:
            received["request"] = request
            return ChatResponse(output=Message(role=Role.ASSISTANT, content="hi there"))

        handler.register("chat", chat_fn)

        result = await handler.handle_chat({
            "params": {"messages": [{"role": "USER", "content": "hello"}]}
        })

        assert isinstance(received["request"], ChatRequest)
        assert received["request"].messages[0].content == "hello"
        assert result == {"output": {"role": "ASSISTANT", "content": "hi there"}}

    @pytest.mark.asyncio
    async def test_passes_through_non_chat_response_result(self, handler):
        handler.register("chat", lambda request: {"output": {"role": "ASSISTANT", "content": "raw"}})

        result = await handler.handle_chat({
            "params": {"messages": [{"role": "USER", "content": "hello"}]}
        })

        assert result == {"output": {"role": "ASSISTANT", "content": "raw"}}

    @pytest.mark.asyncio
    async def test_raises_when_no_handler_registered(self, handler):
        with pytest.raises(ValueError, match="No user handler for 'chat'"):
            await handler.handle_chat({
                "params": {"messages": [{"role": "USER", "content": "hello"}]}
            })


class TestHandleChatHealth:

    @pytest.fixture
    def handler(self):
        return FileHandler()

    @pytest.mark.asyncio
    async def test_calls_registered_handler_with_no_arguments(self, handler):
        def chat_health_fn() -> ChatHealthResponse:
            return ChatHealthResponse(
                status=HealthStatus.OK,
                capabilities=ChatCapabilities(
                    supportsChat=True,
                    supportsDataPolicy=DataPolicySupport.NOT_SUPPORTED,
                ),
            )

        handler.register("chat/health", chat_health_fn)

        result = await handler.handle_chat_health({"params": {}})

        assert result == {
            "status": "OK",
            "capabilities": {"supportsChat": True, "supportsDataPolicy": "NOT_SUPPORTED"},
        }

    @pytest.mark.asyncio
    async def test_passes_through_non_chat_health_response_result(self, handler):
        handler.register("chat/health", lambda: {"status": "OK"})

        result = await handler.handle_chat_health({"params": {}})

        assert result == {"status": "OK"}


class TestHandleDispatch:
    """Covers the name -> method lookup in Handler.handle, including the
    'chat/health' slash normalisation."""

    @pytest.fixture
    def handler(self):
        return FileHandler()

    @pytest.mark.asyncio
    async def test_dispatches_chat_to_handle_chat(self, handler):
        handler.register("chat", lambda request: ChatResponse(
            output=Message(role=Role.ASSISTANT, content="ok")
        ))

        result = await handler.handle("chat", {
            "params": {"messages": [{"role": "USER", "content": "hi"}]}
        })

        assert result == {"output": {"role": "ASSISTANT", "content": "ok"}}

    @pytest.mark.asyncio
    async def test_dispatches_chat_slash_health_to_handle_chat_health(self, handler):
        handler.register("chat/health", lambda: ChatHealthResponse(
            status=HealthStatus.OK,
            capabilities=ChatCapabilities(
                supportsChat=True,
                supportsDataPolicy=DataPolicySupport.NOT_SUPPORTED,
            ),
        ))

        result = await handler.handle("chat/health", {"params": {}})

        assert result["status"] == "OK"

    @pytest.mark.asyncio
    async def test_unknown_command_raises(self, handler):
        with pytest.raises(ValueError, match="No handler for 'unknown'"):
            await handler.handle("unknown", {"params": {}})
