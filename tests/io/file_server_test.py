import pytest
import ujson
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from lf_toolkit.io.file_server import FileHandler, FileServer
from lf_toolkit.io.handler import Handler

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class TestFileHandler:
    """Tests for FileHandler class"""

    @pytest.fixture
    def handler(self):
        """Create a FileHandler instance for testing"""
        return FileHandler()

    @pytest.mark.asyncio
    async def test_dispatch_success(self, handler):
        """Test successful command dispatch"""
        # Mock the handle method
        handler.handle = AsyncMock(return_value={"status": "success", "data": "test"})

        request = ujson.dumps({
            "command": "test_command",
            "response": "",
            "answer": "",
            "params": {"key": "value"}
        })
        response_str = await handler.dispatch(request)
        response = ujson.loads(response_str)

        assert response["command"] == "test_command"
        assert response["result"] == {"status": "success", "data": "test"}
        assert "error" not in response
        handler.handle.assert_called_once_with("test_command", {
            "command": "test_command",
            "response": "",
            "answer": "",
            "params": {"key": "value"}
        })

    @pytest.mark.asyncio
    async def test_dispatch_missing_command(self, handler):
        """Test dispatch with missing command field"""
        handler.handle = AsyncMock(return_value="ok")

        request = ujson.dumps({
            "response": "",
            "answer": "",
            "params": {"key": "value"}
        })
        response_str = await handler.dispatch(request)
        response = ujson.loads(response_str)

        assert response["command"] is None
        assert response["result"] == "ok"
        handler.handle.assert_called_once_with(None, {
            "response": "",
            "answer": "",
            "params": {"key": "value"}
        })

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, handler):
        """Test error handling when handler raises exception"""
        handler.handle = AsyncMock(side_effect=ValueError("Invalid command"))

        request = ujson.dumps({
            "command": "bad_command",
            "response": "",
            "answer": "",
            "params": {}
        })
        response_str = await handler.dispatch(request)
        response = ujson.loads(response_str)

        assert response["command"] == "bad_command"
        assert "error" in response
        assert response["error"] == "Invalid command"
        assert "result" not in response

    @pytest.mark.asyncio
    async def test_dispatch_invalid_json(self, handler):
        """Test dispatch with invalid JSON input"""
        with pytest.raises(ujson.JSONDecodeError):
            await handler.dispatch("invalid json{")

    @pytest.mark.asyncio
    async def test_dispatch_empty_request(self, handler):
        """Test dispatch with empty request object"""
        handler.handle = AsyncMock(return_value=None)

        request = ujson.dumps({})
        response_str = await handler.dispatch(request)
        response = ujson.loads(response_str)

        assert response["command"] is None
        assert response["result"] is None


class TestFileServer:
    """Tests for FileServer class"""

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary request and response files"""
        request_file = tmp_path / "request.json"
        response_file = tmp_path / "response.json"
        return str(request_file), str(response_file)

    @pytest.fixture
    def mock_handler(self):
        """Create a mock handler"""
        handler = Mock(spec=Handler)
        handler.handle = AsyncMock()
        return handler

    def test_init_with_default_handler(self, temp_files):
        """Test FileServer initialization with default handler"""
        request_file, response_file = temp_files
        server = FileServer(request_file, response_file)

        assert server._request_file_path == request_file
        assert server._response_file_path == response_file
        assert isinstance(server._handler, FileHandler)

    def test_init_with_custom_handler(self, temp_files, mock_handler):
        """Test FileServer initialization with custom handler"""
        request_file, response_file = temp_files
        server = FileServer(request_file, response_file, handler=mock_handler)

        assert server._request_file_path == request_file
        assert server._response_file_path == response_file
        assert server._handler is mock_handler

    @pytest.mark.asyncio
    async def test_run_success(self, temp_files, tmp_path):
        """Test successful file server run"""
        request_file, response_file = temp_files

        # Write request to file
        request_data = {
            "command": "test",
            "response": "",
            "answer": "",
            "params": {"data": "hello"}
        }
        Path(request_file).write_text(ujson.dumps(request_data))

        # Create server with mock handler
        handler = FileHandler()
        handler.handle = AsyncMock(return_value={"output": "success"})
        server = FileServer(request_file, response_file, handler=handler)

        # Run server
        await server.run()

        # Verify response file
        response_content = Path(response_file).read_text()
        response = ujson.loads(response_content)

        assert response["command"] == "test"
        assert response["result"] == {"output": "success"}

    @pytest.mark.asyncio
    async def test_run_with_handler_error(self, temp_files, tmp_path):
        """Test file server run when handler raises error"""
        request_file, response_file = temp_files

        # Write request to file
        request_data = {
            "command": "failing_command",
            "response": "",
            "answer": "",
            "params": {}
        }
        Path(request_file).write_text(ujson.dumps(request_data))

        # Create server with failing handler
        handler = FileHandler()
        handler.handle = AsyncMock(side_effect=RuntimeError("Processing failed"))
        server = FileServer(request_file, response_file, handler=handler)

        # Run server
        await server.run()

        # Verify error response
        response_content = Path(response_file).read_text()
        response = ujson.loads(response_content)

        assert response["command"] == "failing_command"
        assert "error" in response
        assert response["error"] == "Processing failed"

    @pytest.mark.asyncio
    async def test_run_missing_request_file(self, temp_files):
        """Test run with non-existent request file"""
        request_file, response_file = temp_files
        server = FileServer(request_file, response_file)

        with pytest.raises(FileNotFoundError):
            await server.run()

    @pytest.mark.asyncio
    async def test_run_creates_response_file(self, temp_files, tmp_path):
        """Test that run creates response file if it doesn't exist"""
        request_file, response_file = temp_files

        # Write request file
        Path(request_file).write_text(ujson.dumps({
            "command": "test",
            "response": "",
            "answer": "",
            "params": {}
        }))

        # Ensure response file doesn't exist
        assert not Path(response_file).exists()

        handler = FileHandler()
        handler.handle = AsyncMock(return_value="done")
        server = FileServer(request_file, response_file, handler=handler)

        await server.run()

        # Verify response file was created
        assert Path(response_file).exists()

    @pytest.mark.asyncio
    async def test_run_with_empty_request_file(self, temp_files, tmp_path):
        """Test run with empty request file"""
        request_file, response_file = temp_files

        # Create empty request file
        Path(request_file).write_text("")

        server = FileServer(request_file, response_file)

        with pytest.raises(ujson.JSONDecodeError):
            await server.run()

    @pytest.mark.asyncio
    async def test_run_with_complex_nested_data(self, temp_files, tmp_path):
        """Test run with complex nested JSON data"""
        request_file, response_file = temp_files

        request_data = {
            "command": "eval",
            "response": "",
            "answer": "",
            "params": {
                "array": [1, 2, 3],
                "object": {"key": "value"},
                "null": None,
                "bool": True
            }
        }
        Path(request_file).write_text(ujson.dumps(request_data))

        handler = FileHandler()
        handler.handle = AsyncMock(return_value={"processed": True})
        server = FileServer(request_file, response_file, handler=handler)

        await server.run()

        response_content = Path(response_file).read_text()
        response = ujson.loads(response_content)

        assert response["command"] == "eval"
        assert response["result"] == {"processed": True}
