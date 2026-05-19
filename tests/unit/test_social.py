"""Unit tests for social.py — SocialMediaSignal, LexiconAnalyzer, collect_from_source."""

import pytest
from datetime import datetime

from synapse.event.social import (
    SocialMediaSignal,
    LexiconAnalyzer,
    collect_from_source,
    POSITIVE_LEXICON,
    NEGATIVE_LEXICON,
)


# ---------------------------------------------------------------------------
# SocialMediaSignal schema
# ---------------------------------------------------------------------------

class TestSocialMediaSignal:
    """Tests for SocialMediaSignal dataclass."""

    def test_default_values(self) -> None:
        sig = SocialMediaSignal()
        assert sig.signal_id.startswith("soc-")
        assert sig.platform == ""
        assert sig.sentiment_score == 0.0
        assert sig.collected_at is not None

    def test_custom_values(self) -> None:
        sig = SocialMediaSignal(
            platform="weibo",
            ticker="600519.SH",
            content="利好茅台",
            sentiment_score=0.5,
            engagement_count=100,
        )
        assert sig.platform == "weibo"
        assert sig.ticker == "600519.SH"
        assert sig.engagement_count == 100

    def test_score_range_validation(self) -> None:
        with pytest.raises(ValueError, match="sentiment_score must be in"):
            SocialMediaSignal(sentiment_score=1.5)
        with pytest.raises(ValueError, match="sentiment_score must be in"):
            SocialMediaSignal(sentiment_score=-1.5)

    def test_to_dict(self) -> None:
        sig = SocialMediaSignal(platform="xueqiu", ticker="000001.SZ")
        d = sig.to_dict()
        assert d["platform"] == "xueqiu"
        assert d["ticker"] == "000001.SZ"
        assert "signal_id" in d
        assert "collected_at" in d

    def test_from_dict(self) -> None:
        data = {
            "signal_id": "soc-test",
            "platform": "eastmoney",
            "ticker": "601318.SH",
            "content": "大涨",
            "sentiment_score": 0.7,
            "engagement_count": 50,
            "collected_at": "2026-05-19T10:00:00",
        }
        sig = SocialMediaSignal.from_dict(data)
        assert sig.signal_id == "soc-test"
        assert sig.platform == "eastmoney"
        assert sig.sentiment_score == 0.7

    def test_boundary_scores(self) -> None:
        sig_max = SocialMediaSignal(sentiment_score=1.0)
        assert sig_max.sentiment_score == 1.0
        sig_min = SocialMediaSignal(sentiment_score=-1.0)
        assert sig_min.sentiment_score == -1.0


# ---------------------------------------------------------------------------
# LexiconAnalyzer
# ---------------------------------------------------------------------------

class TestLexiconAnalyzer:
    """Tests for LexiconAnalyzer scoring."""

    def setup_method(self) -> None:
        self.analyzer = LexiconAnalyzer()

    def test_positive_text(self) -> None:
        score = self.analyzer.score("利好茅台，涨停板，大涨")
        assert score > 0

    def test_negative_text(self) -> None:
        score = self.analyzer.score("利空跌停，暴跌崩盘")
        assert score < 0

    def test_neutral_text(self) -> None:
        score = self.analyzer.score("今天天气不错")
        assert score == 0.0

    def test_empty_text(self) -> None:
        assert self.analyzer.score("") == 0.0

    def test_score_range(self) -> None:
        score = self.analyzer.score("利好涨停大涨暴涨飙升突破新高强势")
        assert -1.0 <= score <= 1.0

    def test_score_batch(self) -> None:
        texts = ["利好涨停", "利空跌停", "今天周一"]
        scores = self.analyzer.score_batch(texts)
        assert len(scores) == 3
        assert scores[0] > 0
        assert scores[1] < 0
        assert scores[2] == 0.0

    def test_lexicon_sizes(self) -> None:
        assert len(POSITIVE_LEXICON) >= 50
        assert len(NEGATIVE_LEXICON) >= 52

    def test_denominator_not_zero(self) -> None:
        # Empty text should not cause division by zero
        assert self.analyzer.score("") == 0.0
        # Text with no lexicon matches
        assert self.analyzer.score("hello world") == 0.0


# ---------------------------------------------------------------------------
# collect_from_source factory
# ---------------------------------------------------------------------------

class TestCollectFromSource:
    """Tests for collect_from_source factory."""

    def test_basic_collection(self) -> None:
        signals = collect_from_source(
            platform="weibo",
            ticker="600519.SH",
            raw_texts=["利好茅台", "利空消息"],
        )
        assert len(signals) == 2
        assert all(s.platform == "weibo" for s in signals)
        assert all(s.ticker == "600519.SH" for s in signals)

    def test_engagement_counts(self) -> None:
        signals = collect_from_source(
            platform="xueqiu",
            ticker="000001.SZ",
            raw_texts=["text1", "text2", "text3"],
            engagement_counts=[10, 20, 30],
        )
        assert signals[0].engagement_count == 10
        assert signals[1].engagement_count == 20
        assert signals[2].engagement_count == 30

    def test_missing_engagement_defaults_zero(self) -> None:
        signals = collect_from_source(
            platform="eastmoney",
            ticker="601318.SH",
            raw_texts=["text"],
        )
        assert signals[0].engagement_count == 0

    def test_empty_texts(self) -> None:
        signals = collect_from_source(
            platform="weibo",
            ticker="600519.SH",
            raw_texts=[],
        )
        assert len(signals) == 0
