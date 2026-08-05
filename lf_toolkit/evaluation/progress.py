import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 1.0  # seconds; matches shimmy's default progress-callback-timeout
_DEFAULT_DRAIN_TIMEOUT = 0.25  # seconds; matches shimmy's sidecar unbind grace period

# A single worker serializes delivery: progress events reach shimmy's
# sidecar in the same order report_progress() was called, rather than
# racing each other across threads - which could reorder them, or land
# them close enough together to trip the sidecar's own rate limiting even
# though the calling code issued them with real spacing between them.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lf-progress")

_pending_lock = threading.Lock()
_pending: List[Future] = []


def _post_progress(url: str, payload: Dict[str, Any], timeout: float) -> None:
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        if not response.ok:
            logger.debug(
                "Progress callback rejected by shimmy (status %s): %s",
                response.status_code,
                response.text,
            )
    except requests.exceptions.RequestException as e:
        logger.debug("Progress callback failed: %s", e)


def report_progress(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Report a free-form progress event to shimmy, if running under it.

    Safe to call unconditionally from any evaluation function - this is a
    no-op (does not raise, does not block) when EVAL_PROGRESS_URL is not
    set, e.g. when running the evaluation function standalone or in tests.
    """
    if not message:
        logger.debug("report_progress called with empty message, skipping")
        return

    url = os.getenv("EVAL_PROGRESS_URL")
    if not url:
        logger.debug("EVAL_PROGRESS_URL not set, skipping progress report")
        return

    payload: Dict[str, Any] = {"message": message}
    if data is not None:
        payload["data"] = data

    future = _executor.submit(_post_progress, url, payload, _DEFAULT_TIMEOUT)

    with _pending_lock:
        _pending.append(future)


def flush_progress(timeout: float = _DEFAULT_DRAIN_TIMEOUT) -> None:
    """Wait, bounded by `timeout`, for progress reports dispatched so far.

    Called by the RPC dispatch layer immediately after an evaluation or
    preview function returns, so a report_progress() call made near the end
    of the function has a real chance to reach shimmy's sidecar before the
    RPC response carries the Result back and the sidecar detaches its
    relay. Never raises: a report that doesn't finish within `timeout` is
    simply left to complete (or fail) in the background, same as before
    this existed.
    """
    with _pending_lock:
        pending = _pending[:]
        _pending.clear()

    if not pending:
        return

    wait(pending, timeout=timeout)
