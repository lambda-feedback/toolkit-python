# Evaluation Function Toolkit for Python

A Python toolkit for building and serving evaluation functions. Supports multiple transport mechanisms (stdio, IPC, file) and provides result types for evaluation, chat, and preview use cases.

## Installation

```bash
pip install lf_toolkit
```

Install with optional extras:

```bash
# Set parsing (antlr4, lark, latex2sympy)
pip install "lf_toolkit[parsing]"

# IPC support on Windows (named pipes)
pip install "lf_toolkit[ipc]"

# HTTP server support
pip install "lf_toolkit[http]"
```

## Quick Start

```python
from lf_toolkit import create_server, run
from lf_toolkit.evaluation import Result
from lf_toolkit.shared import Params

server = create_server()

@server.eval
def evaluate(response, answer, params: Params) -> Result:
    is_correct = response.strip() == answer.strip()
    result = Result(is_correct=is_correct)
    if not is_correct:
        result.add_feedback("hint", "Check your answer again.")
    return result

run(server)
```

## Servers

The toolkit provides three server types:

| Class | Transport | Use case |
|---|---|---|
| `StdioServer` | stdin/stdout | Default; subprocess communication |
| `IPCServer` | Unix socket / named pipe | Local IPC |
| `FileServer` | Files on disk | File-based request/response |

### Manual instantiation

```python
from lf_toolkit import StdioServer, IPCServer, FileServer

server = StdioServer()
server = IPCServer(endpoint="/tmp/eval.sock")
server = FileServer(request_file_path="request.json", response_file_path="response.json")
```

### `create_server()` with environment variables

`create_server()` selects the server type from environment variables:

| Variable | Values | Default |
|---|---|---|
| `EVAL_IO` | `rpc`, `file` | `rpc` |
| `EVAL_RPC_TRANSPORT` | `stdio`, `ipc` | `stdio` |
| `EVAL_RPC_IPC_ENDPOINT` | socket/pipe path | — |
| `EVAL_FILE_NAME_REQUEST` | file path | — |
| `EVAL_FILE_NAME_RESPONSE` | file path | — |

## Handlers

Register handlers using decorators on the server instance:

```python
@server.eval
def evaluate(response, answer, params: Params) -> Result:
    ...

@server.preview
def preview(response, params: Params):
    ...

@server.health
def healthcheck():
    ...
```

Handlers can be `async`:

```python
@server.eval
async def evaluate(response, answer, params: Params) -> Result:
    ...
```

## Result Types

### `evaluation.Result`

```python
from lf_toolkit.evaluation import Result

result = Result(
    is_correct=True,
    latex=r"\frac{1}{2}",
    simplified="1/2",
)

result.add_feedback("hint", "Well done!")

result.to_dict()
# {"is_correct": True, "feedback": "Well done!", "response_latex": "...", ...}
```

Tags (e.g. `"hint"`, `"error"`) group feedback messages and are used for data analytics, so using consistent tag names across evaluation functions enables meaningful aggregation and reporting.

### `chat.ChatResult`

```python
from lf_toolkit.chat import ChatResult

result = ChatResult()
result.add_response("main", "Here is the explanation...")
result.add_metadata("model", "gpt-4")
result.add_processing_time(1.23)

result.to_dict()
# {"chatbot_response": "Here is the explanation..."}
```

### `chat.ChatParams`

```python
from lf_toolkit.chat import ChatParams

params: ChatParams = {
    "include_test_data": False,
    "conversation_history": ["Hello", "Hi there"],
    "summary": "Previous summary",
    "conversational_style": "formal",
    "question_response_details": "...",
    "conversation_id": "abc-123",
}
```

### `chat` API types

`lf_toolkit.chat` also exports auto-generated types for the MuEd API:

```python
from lf_toolkit.chat import ChatRequest, ChatResponse, Message
```

## Image Upload

Upload PIL images to AWS S3 or Google Cloud Storage:

```python
from PIL import Image
from lf_toolkit.evaluation.image_upload import upload_image

img = Image.open("diagram.png")
url = upload_image(img, folder_name="my-eval-function")
```

### Backend selection

`upload_image` picks a backend at call time:

1. `IMAGE_UPLOAD_BACKEND` env var, when set to `s3` or `gcs`, wins.
2. Otherwise, if `GCS_BUCKET` is set the GCS backend is used.
3. Otherwise S3 is used (the default — existing deployments are unaffected).

### S3 backend

Uses AWS SigV4-signed `PUT` requests.

| Variable | Description |
|---|---|
| `S3_BUCKET_URI` | Base S3 bucket URI |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_SESSION_TOKEN` | (optional) Session token |
| `AWS_REGION` | AWS region (default: `eu-west-2`) |

### GCS backend

Requires the `gcs` extra (`poetry install --extras gcs`, or
`lf_toolkit = { ..., extras = ["gcs"] }`). Authenticates with Application
Default Credentials (the runtime service account on Cloud Run / GKE / GCE) — no
static keys. The target bucket / prefix must be readable by whoever consumes the
returned URL (e.g. `roles/storage.objectViewer` for `allUsers`).

| Variable | Description |
|---|---|
| `GCS_BUCKET` | Target bucket name |
| `GCS_PUBLIC_BASE_URL` | (optional) URL host for the returned link (default: `https://storage.googleapis.com`) |

## Set Notation Parser

Parse and evaluate set expressions (requires `parsing` extra):

```python
from lf_toolkit.parse.set import parse, evaluate
```

## Development

```bash
# Install dependencies
poetry install

# Run tests
pytest

# Lint
make lint
```