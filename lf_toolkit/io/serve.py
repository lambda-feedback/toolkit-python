import os
import signal

import anyio

from anyio.abc import CancelScope

from .base_server import BaseServer


async def signal_handler(scope: CancelScope):
    with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for signum in signals:
            if signum == signal.SIGINT:
                print("Received SIGINT, exiting...")
            else:
                print("Received SIGTERM, exiting...")

            scope.cancel()
            return


def run(server: BaseServer):
    async def main():
        async with anyio.create_task_group() as tg:
            tg.start_soon(signal_handler, tg.cancel_scope)
            tg.start_soon(server.run)

    anyio.run(main)


# def serve():
#     try:
#         run(create_server())
#     except Exception as e:
#         print(f"Error: {e}")
#         exit(1)


def create_server():
    io = os.environ.get("EVAL_IO", "rpc")

    if io == "rpc":
        return create_rpc_server()
    elif io == "file":
        return create_file_server()
    else:
        raise ValueError(f"Unsupported io: {io}")


def create_file_server():
    from .file_server import FileServer

    request_file_path = os.environ.get("EVAL_FILE_NAME_REQUEST", None)
    response_file_path = os.environ.get("EVAL_FILE_NAME_RESPONSE", None)

    if request_file_path is None or response_file_path is None:
        raise ValueError(
            "EVAL_FILE_NAME_REQUEST and EVAL_FILE_NAME_RESPONSE must be set"
        )

    return FileServer(request_file_path, response_file_path)


def create_rpc_server():
    # fallback to stdio if transport is not set
    transport = os.environ.get("EVAL_RPC_TRANSPORT", "stdio")

    if transport == "stdio":
        return create_stdio_server()
    elif transport == "ipc":
        return create_ipc_server()
    else:
        raise ValueError(f"Unsupported transport: {transport}")


def create_stdio_server():
    from .stdio_server import StdioServer

    return StdioServer()


def create_ipc_server():
    from .ipc_server import IPCServer

    endpoint = os.environ.get("EVAL_RPC_IPC_ENDPOINT", None)
    return IPCServer(endpoint if endpoint else None)
