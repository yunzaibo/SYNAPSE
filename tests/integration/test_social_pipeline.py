"""Integration tests for social.py + streaming.py pipeline.

Tests the full flow: collect_from_source -> StreamBuffer -> StreamingIngestion.
"""

import pytest
from unittest.mock import MagicMock

from synapse.event.social import collect_from_source, LexiconAnalyzer
from synapse.event.streaming import PollingSource, StreamBuffer, StreamingIngestion


class TestSocialStreamingPipeline:
    """Integration: social collection -> streaming buffer pipeline."""

    def test_collect_to_buffer(self) -> None:
        """Collect signals from source, feed into StreamBuffer."""
        signals = collect_from_source(
            platform="weibo",
            ticker="600519.SH",
            raw_texts=["利好涨停", "利空跌停", "中性消息"],
            engagement_counts=[100, 50, 10],
        )

        buf = StreamBuffer(max_size=100)
        buf.extend(signals)
        assert buf.size == 3

        drained = buf.drain()
        assert len(drained) == 3
        assert drained[0].sentiment_score > 0  # bullish
        assert drained[1].sentiment_score < 0  # bearish

    def test_multi_platform_collection(self) -> None:
        """Collect from multiple platforms, merge into single buffer."""
        weibo_signals = collect_from_source(
            platform="weibo",
            ticker="600519.SH",
            raw_texts=["利好"],
        )
        xueqiu_signals = collect_from_source(
            platform="xueqiu",
            ticker="600519.SH",
            raw_texts=["大涨"],
        )

        buf = StreamBuffer()
        buf.extend(weibo_signals)
        buf.extend(xueqiu_signals)

        assert buf.size == 2
        platforms = {s.platform for s in buf.drain()}
        assert platforms == {"weibo", "xueqiu"}

    def test_streaming_with_social_sources(self) -> None:
        """StreamingIngestion with mock social data sources."""
        ing = StreamingIngestion(buffer_size=500)

        weibo_source = PollingSource(
            source_id="weibo",
            name="weibo_search",
            url="https://api.weibo.com/search",
        )
        xueqiu_source = PollingSource(
            source_id="xueqiu",
            name="xueqiu_stock",
            url="https://xueqiu.com/statuses",
        )
        ing.register_source(weibo_source)
        ing.register_source(xueqiu_source)

        # Mock fetch returns social media content
        weibo_data = [
            {"content": "利好茅台涨停", "engagement": 200},
            {"content": "利空消息", "engagement": 50},
        ]
        xueqiu_data = [
            {"content": "突破新高", "engagement": 100},
        ]

        call_count = 0

        def mock_fetch(source: PollingSource) -> list:
            nonlocal call_count
            call_count += 1
            if source.source_id == "weibo":
                return weibo_data
            return xueqiu_data

        ing.set_fetch_fn(mock_fetch)
        count = ing.poll_once()

        assert count == 3
        assert ing.buffer.size == 3

    def test_lexicon_score_in_pipeline(self) -> None:
        """Verify lexicon scoring flows correctly through pipeline."""
        analyzer = LexiconAnalyzer()

        texts = [
            "利好涨停暴涨飙升",  # very bullish
            "利空暴跌崩盘跌停",  # very bearish
            "今天周一",          # neutral
        ]

        signals = collect_from_source(
            platform="news",
            ticker="000001.SZ",
            raw_texts=texts,
        )

        scores = [s.sentiment_score for s in signals]
        assert scores[0] > 0.5   # strong bullish
        assert scores[1] < -0.5  # strong bearish
        assert scores[2] == 0.0  # neutral

    def test_buffer_bounded_eviction(self) -> None:
        """Verify buffer evicts oldest when full during pipeline."""
        buf = StreamBuffer(max_size=3)

        for i in range(5):
            signals = collect_from_source(
                platform="test",
                ticker="TEST.SH",
                raw_texts=[f"text_{i}"],
            )
            buf.extend(signals)

        assert buf.size == 3
        drained = buf.drain()
        # Should contain items 2, 3, 4 (oldest evicted)
        assert drained[0].content == "text_2"
        assert drained[2].content == "text_4"
