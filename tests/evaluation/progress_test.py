import logging
import threading
from unittest.mock import Mock, patch

import pytest
import requests

from lf_toolkit.evaluation.progress import _post_progress, report_progress


class TestReportProgress:
    """Test suite for report_progress"""

    def test_noop_when_env_var_unset(self, monkeypatch):
        monkeypatch.delenv("EVAL_PROGRESS_URL", raising=False)

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            report_progress("hello")
            _wait_for_executor()

        mock_post.assert_not_called()

    def test_noop_when_message_empty(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            report_progress("")
            _wait_for_executor()

        mock_post.assert_not_called()

    def test_posts_message_only_payload(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            mock_post.return_value = Mock(ok=True)
            report_progress("evaluating step 1")
            _wait_for_executor()

        mock_post.assert_called_once_with(
            "http://127.0.0.1:9999",
            json={"message": "evaluating step 1"},
            timeout=1.0,
        )

    def test_posts_message_and_data_payload(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            mock_post.return_value = Mock(ok=True)
            report_progress("evaluating step 2", data={"step": 2})
            _wait_for_executor()

        mock_post.assert_called_once_with(
            "http://127.0.0.1:9999",
            json={"message": "evaluating step 2", "data": {"step": 2}},
            timeout=1.0,
        )

    def test_returns_immediately_without_waiting_on_network_call(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        release_event = threading.Event()

        def slow_post(*args, **kwargs):
            release_event.wait(timeout=5)
            return Mock(ok=True)

        with patch(
            "lf_toolkit.evaluation.progress.requests.post", side_effect=slow_post
        ):
            report_progress("hello")  # must not block on slow_post

        release_event.set()


class TestPostProgress:
    """Test suite for the internal _post_progress worker function"""

    def test_swallows_request_exception(self, caplog):
        with patch(
            "lf_toolkit.evaluation.progress.requests.post",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with caplog.at_level(logging.DEBUG):
                _post_progress("http://127.0.0.1:9999", {"message": "hi"}, 1.0)

        assert "Progress callback failed" in caplog.text

    def test_logs_non_ok_response(self, caplog):
        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            mock_post.return_value = Mock(ok=False, status_code=429, text="rate limited")

            with caplog.at_level(logging.DEBUG):
                _post_progress("http://127.0.0.1:9999", {"message": "hi"}, 1.0)

        assert "rejected by shimmy" in caplog.text

    def test_ok_response_logs_nothing(self, caplog):
        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            mock_post.return_value = Mock(ok=True)

            with caplog.at_level(logging.DEBUG):
                _post_progress("http://127.0.0.1:9999", {"message": "hi"}, 1.0)

        assert caplog.text == ""


def _wait_for_executor():
    """Block until all currently-submitted background progress posts finish."""
    from lf_toolkit.evaluation.progress import _executor

    _executor.shutdown(wait=True)

    # Re-create the executor since shutdown() is terminal, so later tests
    # in this module can still submit new work.
    import lf_toolkit.evaluation.progress as progress_module
    from concurrent.futures import ThreadPoolExecutor

    progress_module._executor = ThreadPoolExecutor(
        max_workers=2, thread_name_prefix="lf-progress"
    )
