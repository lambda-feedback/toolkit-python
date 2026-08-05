import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 1.0  # seconds; matches shimmy's default progress-callback-timeout
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lf-progress")


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

    _executor.submit(_post_progress, url, payload, _DEFAULT_TIMEOUT)
