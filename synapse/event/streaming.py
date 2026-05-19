"""Streaming Ingestion -- Poll-based streaming pipeline with bounded buffer.

Provides PollingSource configuration, StreamBuffer (deque-based bounded
buffer), and StreamingIngestion orchestrator for real-time signal collection.

Part of P4 Real-time & Social Sentiment (F-007).
MVP scope: Poll-based, in-memory buffer. No WebSocket/Redis yet.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Polling Source
# ---------------------------------------------------------------------------

@dataclass
class PollingSource:
    """Configuration for a poll-based data source.

    Attributes
    ----------
    source_id:
        Unique identifier for this source.
    name:
        Human-readable name (e.g. "weibo_search", "eastmoney_guba").
    url:
        Poll endpoint URL.
    poll_interval_sec:
        Seconds between polls. Default 300 (5 minutes).
    headers:
        Optional HTTP headers (e.g. auth tokens).
    params:
        Optional query parameters.
    enabled:
        Whether this source is active.
    """

    source_id: str = ""
    name: str = ""
    url: str = ""
    poll_interval_sec: int = 300
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Stream Buffer
# ---------------------------------------------------------------------------

class StreamBuffer:
    """Bounded in-memory buffer using collections.deque.

    O(1) append, automatic eviction of oldest items when full.
    Thread-safe for single-producer/single-consumer patterns.

    Parameters
    ----------
    max_size:
        Maximum buffer capacity. Default 1000.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._buffer: deque[Any] = deque(maxlen=max_size)
        self._max_size = max_size

    def append(self, item: Any) -> None:
        """Append item. Evicts oldest if at capacity."""
        self._buffer.append(item)

    def extend(self, items: list[Any]) -> None:
        """Append multiple items."""
        self._buffer.extend(items)

    def drain(self) -> list[Any]:
        """Remove and return all items. O(n)."""
        result = list(self._buffer)
        self._buffer.clear()
        return result

    def peek(self, n: int = 10) -> list[Any]:
        """Return up to n most recent items without removing."""
        return list(self._buffer)[-n:]

    @property
    def size(self) -> int:
        """Current buffer size."""
        return len(self._buffer)

    @property
    def capacity(self) -> int:
        """Maximum buffer capacity."""
        return self._max_size

    def __len__(self) -> int:
        return len(self._buffer)

    def __bool__(self) -> bool:
        return bool(self._buffer)


# ---------------------------------------------------------------------------
# Streaming Ingestion
# ---------------------------------------------------------------------------

class StreamingIngestion:
    """Orchestrates polling from multiple sources into a StreamBuffer.

    Usage::

        ingestion = StreamingIngestion(buffer_size=2000)
        ingestion.register_source(PollingSource(name="weibo", url="..."))
        ingestion.start()  # blocks, polls in loop

    MVP: synchronous httpx/requests polling. No async/WebSocket yet.
    """

    def __init__(self, buffer_size: int = 1000) -> None:
        self._sources: list[PollingSource] = []
        self._buffer = StreamBuffer(max_size=buffer_size)
        self._running = False
        self._fetch_fn: Optional[Callable[[PollingSource], list[Any]]] = None

    @property
    def buffer(self) -> StreamBuffer:
        """Access the underlying stream buffer."""
        return self._buffer

    def register_source(self, source: PollingSource) -> None:
        """Register a polling source."""
        self._sources.append(source)
        logger.info("Registered polling source: %s (%s)", source.name, source.source_id)

    def set_fetch_fn(self, fn: Callable[[PollingSource], list[Any]]) -> None:
        """Set custom fetch function. Default uses requests."""
        self._fetch_fn = fn

    def _default_fetch(self, source: PollingSource) -> list[Any]:
        """Default fetch using requests library."""
        try:
            import requests
        except ImportError:
            logger.warning("requests not installed, skipping fetch for %s", source.name)
            return []

        try:
            resp = requests.get(
                source.url,
                headers=source.headers or None,
                params=source.params or None,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            # Expect list of items; wrap single item
            if isinstance(data, list):
                return data
            return [data]
        except Exception as exc:
            logger.warning("Fetch failed for %s: %s", source.name, exc)
            return []

    def poll_once(self) -> int:
        """Poll all enabled sources once. Returns total items collected."""
        fetch = self._fetch_fn or self._default_fetch
        total = 0

        for source in self._sources:
            if not source.enabled:
                continue

            try:
                items = fetch(source)
                if items:
                    self._buffer.extend(items)
                    total += len(items)
                    logger.debug("Polled %d items from %s", len(items), source.name)
            except Exception as exc:
                logger.warning("Error polling %s: %s", source.name, exc)
                continue

        return total

    def start(self, max_cycles: Optional[int] = None) -> None:
        """Start polling loop. Blocks until stopped or max_cycles reached.

        Parameters
        ----------
        max_cycles:
            Maximum number of poll cycles. None = infinite (until stop()).
        """
        self._running = True
        cycle = 0

        logger.info(
            "Streaming ingestion started: %d sources, buffer capacity %d",
            len(self._sources),
            self._buffer.capacity,
        )

        while self._running:
            if max_cycles is not None and cycle >= max_cycles:
                break

            collected = self.poll_once()
            if collected:
                logger.info("Cycle %d: collected %d items", cycle, collected)

            cycle += 1

            # Sleep until next cycle (use shortest interval among sources)
            intervals = [s.poll_interval_sec for s in self._sources if s.enabled]
            sleep_sec = min(intervals) if intervals else 60
            time.sleep(sleep_sec)

        self._running = False
        logger.info("Streaming ingestion stopped after %d cycles", cycle)

    def stop(self) -> None:
        """Signal the polling loop to stop after current cycle."""
        self._running = False
