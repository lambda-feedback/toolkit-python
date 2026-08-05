import pytest
from unittest.mock import patch

from lf_toolkit.io.file_server import FileHandler

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class TestCallUserHandlerFlushesProgress:
    """_call_user_handler must flush any pending report_progress() posts
    before returning, so they have a chance to reach shimmy's sidecar
    before the RPC response (carrying the Result) goes out."""

    @pytest.fixture
    def handler(self):
        return FileHandler()

    @pytest.mark.asyncio
    async def test_flushes_after_sync_handler_returns(self, handler):
        handler.register("eval", lambda: "ok")

        with patch("lf_toolkit.io.handler.flush_progress") as mock_flush:
            result = await handler._call_user_handler("eval")

        assert result == "ok"
        mock_flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_flushes_after_async_handler_returns(self, handler):
        async def async_eval():
            return "ok"

        handler.register("eval", async_eval)

        with patch("lf_toolkit.io.handler.flush_progress") as mock_flush:
            result = await handler._call_user_handler("eval")

        assert result == "ok"
        mock_flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_flushes_even_when_handler_raises(self, handler):
        def boom():
            raise RuntimeError("boom")

        handler.register("eval", boom)

        with patch("lf_toolkit.io.handler.flush_progress") as mock_flush:
            with pytest.raises(ValueError):
                await handler._call_user_handler("eval")

        mock_flush.assert_called_once()
