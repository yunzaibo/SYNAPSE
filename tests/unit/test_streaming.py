"""Unit tests for streaming.py — PollingSource, StreamBuffer, StreamingIngestion."""

import pytest
from unittest.mock import patch, MagicMock

from synapse.event.streaming import (
    PollingSource,
    StreamBuffer,
    StreamingIngestion,
)


# ---------------------------------------------------------------------------
# PollingSource
# ---------------------------------------------------------------------------

class TestPollingSource:
    """Tests for PollingSource dataclass."""

    def test_default_values(self) -> None:
        src = PollingSource()
        assert src.poll_interval_sec == 300
        assert src.enabled is True
        assert src.headers == {}
        assert src.params == {}

    def test_custom_values(self) -> None:
        src = PollingSource(
            source_id="s1",
            name="weibo_search",
            url="https://api.example.com/weibo",
            poll_interval_sec=60,
            enabled=False,
        )
        assert src.source_id == "s1"
        assert src.poll_interval_sec == 60
        assert src.enabled is False


# ---------------------------------------------------------------------------
# StreamBuffer
# ---------------------------------------------------------------------------

class TestStreamBuffer:
    """Tests for StreamBuffer (deque-based bounded buffer)."""

    def test_append_within_capacity(self) -> None:
        buf = StreamBuffer(max_size=5)
        for i in range(5):
            buf.append(i)
        assert buf.size == 5
        assert buf.drain() == [0, 1, 2, 3, 4]

    def test_append_evicts_oldest(self) -> None:
        buf = StreamBuffer(max_size=3)
        buf.append(1)
        buf.append(2)
        buf.append(3)
        buf.append(4)  # evicts 1
        assert buf.size == 3
        assert buf.drain() == [2, 3, 4]

    def test_extend(self) -> None:
        buf = StreamBuffer(max_size=10)
        buf.extend([1, 2, 3])
        assert buf.size == 3

    def test_drain_clears_buffer(self) -> None:
        buf = StreamBuffer()
        buf.append(1)
        buf.append(2)
        result = buf.drain()
        assert result == [1, 2]
        assert buf.size == 0

    def test_peek(self) -> None:
        buf = StreamBuffer(max_size=5)
        for i in range(5):
            buf.append(i)
        assert buf.peek(2) == [3, 4]
        assert buf.size == 5  # peek doesn't remove

    def test_capacity_property(self) -> None:
        buf = StreamBuffer(max_size=100)
        assert buf.capacity == 100

    def test_len_and_bool(self) -> None:
        buf = StreamBuffer()
        assert len(buf) == 0
        assert not buf
        buf.append(1)
        assert len(buf) == 1
        assert buf


# ---------------------------------------------------------------------------
# StreamingIngestion
# ---------------------------------------------------------------------------

class TestStreamingIngestion:
    """Tests for StreamingIngestion orchestrator."""

    def test_register_source(self) -> None:
        ing = StreamingIngestion()
        src = PollingSource(name="test", url="http://example.com")
        ing.register_source(src)
        assert len(ing._sources) == 1

    def test_poll_once_with_mock(self) -> None:
        ing = StreamingIngestion()
        src = PollingSource(name="test", url="http://example.com")
        ing.register_source(src)

        mock_fn = MagicMock(return_value=[{"data": 1}, {"data": 2}])
        ing.set_fetch_fn(mock_fn)

        count = ing.poll_once()
        assert count == 2
        assert ing.buffer.size == 2

    def test_poll_once_disabled_source(self) -> None:
        ing = StreamingIngestion()
        src = PollingSource(name="disabled", enabled=False)
        ing.register_source(src)

        mock_fn = MagicMock(return_value=[{"data": 1}])
        ing.set_fetch_fn(mock_fn)

        count = ing.poll_once()
        assert count == 0
        mock_fn.assert_not_called()

    def test_poll_once_error_handling(self) -> None:
        ing = StreamingIngestion()
        src = PollingSource(name="failing", url="http://example.com")
        ing.register_source(src)

        def failing_fetch(source: PollingSource) -> list:
            raise ConnectionError("network error")

        ing.set_fetch_fn(failing_fetch)
        count = ing.poll_once()
        assert count == 0  # gracefully handled

    def test_stop(self) -> None:
        ing = StreamingIngestion()
        ing._running = True
        ing.stop()
        assert ing._running is False

    def test_buffer_capacity(self) -> None:
        ing = StreamingIngestion(buffer_size=500)
        assert ing.buffer.capacity == 500
