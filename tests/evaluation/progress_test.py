import logging
import threading
import time
from unittest.mock import Mock, patch

import pytest
import requests

from lf_toolkit.evaluation.progress import (
    _post_progress,
    flush_progress,
    report_progress,
)


class TestReportProgress:
    """Test suite for report_progress"""

    def test_noop_when_env_var_unset(self, monkeypatch):
        monkeypatch.delenv("EVAL_PROGRESS_URL", raising=False)

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            report_progress("hello")
            flush_progress()

        mock_post.assert_not_called()

    def test_noop_when_message_empty(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            report_progress("")
            flush_progress()

        mock_post.assert_not_called()

    def test_posts_message_only_payload(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        with patch("lf_toolkit.evaluation.progress.requests.post") as mock_post:
            mock_post.return_value = Mock(ok=True)
            report_progress("evaluating step 1")
            flush_progress()

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
            flush_progress()

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
        flush_progress()

    def test_delivers_in_call_order(self, monkeypatch):
        """A single worker serializes delivery, so events reach shimmy's
        sidecar in the order report_progress() was called - never racing
        each other across threads and arriving out of order."""
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        seen = []

        def recording_post(url, json, timeout):
            seen.append(json["message"])
            return Mock(ok=True)

        with patch(
            "lf_toolkit.evaluation.progress.requests.post", side_effect=recording_post
        ):
            for i in range(5):
                report_progress(f"step {i}")
            flush_progress()

        assert seen == [f"step {i}" for i in range(5)]


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


class TestFlushProgress:
    """Test suite for flush_progress"""

    def test_noop_when_nothing_pending(self):
        # must return promptly with no pending reports, not block on anything
        start = time.monotonic()
        flush_progress(timeout=5)
        assert time.monotonic() - start < 1

    def test_waits_for_pending_report_to_complete(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        delivered = threading.Event()

        def slow_post(*args, **kwargs):
            time.sleep(0.05)
            delivered.set()
            return Mock(ok=True)

        with patch(
            "lf_toolkit.evaluation.progress.requests.post", side_effect=slow_post
        ):
            report_progress("hello")
            flush_progress(timeout=1)

        assert delivered.is_set()

    def test_bounded_by_timeout(self, monkeypatch):
        monkeypatch.setenv("EVAL_PROGRESS_URL", "http://127.0.0.1:9999")

        release_event = threading.Event()

        def slow_post(*args, **kwargs):
            release_event.wait(timeout=5)
            return Mock(ok=True)

        with patch(
            "lf_toolkit.evaluation.progress.requests.post", side_effect=slow_post
        ):
            report_progress("hello")

            start = time.monotonic()
            flush_progress(timeout=0.05)
            elapsed = time.monotonic() - start

        assert elapsed < 1, "flush_progress must not block past its timeout"
        release_event.set()
