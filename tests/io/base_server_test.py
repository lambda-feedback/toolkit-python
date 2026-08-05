from lf_toolkit.chat import ChatHealthResponse
from lf_toolkit.chat import ChatRequest
from lf_toolkit.chat import ChatResponse
from lf_toolkit.io.base_server import BaseServer


class ConcreteServer(BaseServer):
    async def run(self):
        pass


class TestBaseServerChatRegistration:

    def test_chat_registers_under_chat_name(self):
        server = ConcreteServer()

        @server.chat
        def chat_fn(request: ChatRequest) -> ChatResponse:
            raise NotImplementedError

        assert server._handler._handlers["chat"] is chat_fn

    def test_chat_health_registers_under_chat_slash_health_name(self):
        server = ConcreteServer()

        @server.chat_health
        def chat_health_fn() -> ChatHealthResponse:
            raise NotImplementedError

        assert server._handler._handlers["chat/health"] is chat_health_fn
