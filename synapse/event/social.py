"""Social Media Sentiment -- Lexicon-based Chinese financial sentiment analysis.

Provides SocialMediaSignal schema, LexiconAnalyzer with domain-specific
positive/negative lexicons, and a collect_from_source factory for
polling-based social media signal collection.

Part of P4 Real-time & Social Sentiment (F-007).
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass
class SocialMediaSignal:
    """Schema for a single social media sentiment signal.

    Attributes
    ----------
    signal_id:
        Unique identifier (auto-generated if empty).
    platform:
        Source platform, e.g. "weibo", "xueqiu", "eastmoney", "news".
    ticker:
        Related stock ticker (e.g. "600519.SH").
    content:
        Raw text content from the social media post.
    sentiment_score:
        Lexicon-based sentiment in [-1.0, 1.0]. Positive = bullish, negative = bearish.
    engagement_count:
        Number of likes/comments/shares (relevance proxy).
    source_url:
        Original URL of the post (optional).
    collected_at:
        Timestamp when this signal was collected.
    """

    platform: str = ""
    ticker: str = ""
    content: str = ""
    sentiment_score: float = 0.0
    engagement_count: int = 0
    source_url: str = ""
    collected_at: Optional[datetime] = None
    signal_id: str = ""

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = f"soc-{uuid.uuid4().hex[:8]}"
        if self.collected_at is None:
            self.collected_at = datetime.now()
        if not (-1.0 <= self.sentiment_score <= 1.0):
            raise ValueError(
                f"sentiment_score must be in [-1.0, 1.0], got {self.sentiment_score}"
            )

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "platform": self.platform,
            "ticker": self.ticker,
            "content": self.content,
            "sentiment_score": self.sentiment_score,
            "engagement_count": self.engagement_count,
            "source_url": self.source_url,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SocialMediaSignal:
        return cls(
            signal_id=data.get("signal_id", ""),
            platform=data.get("platform", ""),
            ticker=data.get("ticker", ""),
            content=data.get("content", ""),
            sentiment_score=float(data.get("sentiment_score", 0.0)),
            engagement_count=int(data.get("engagement_count", 0)),
            source_url=data.get("source_url", ""),
            collected_at=(
                datetime.fromisoformat(data["collected_at"])
                if data.get("collected_at")
                else None
            ),
        )


# ---------------------------------------------------------------------------
# Lexicon Analyzer
# ---------------------------------------------------------------------------

# Domain-specific positive lexicon for A-share financial sentiment (50+ terms)
POSITIVE_LEXICON: list[str] = [
    # Strong bullish
    "利好", "涨停", "大涨", "暴涨", "飙升", "突破", "新高", "强势",
    "放量", "金叉", "量价齐升", "站上", "连板", "龙头", "妖股", "打板",
    # Moderate bullish
    "上涨", "反弹", "回升", "走强", "拉升", "冲高", "飘红", "翻红",
    "增持", "回购", "超预期", "扭亏", "业绩增长", "净利润增长", "营收增长",
    "景气", "复苏", "回暖", "好转", "改善", "提升", "加仓", "北向流入",
    "主力", "资金流入", "底部", "企稳", "止跌", "触底", "低估", "超跌",
    "政策利好", "刺激", "看多",
]

# Domain-specific negative lexicon for A-share financial sentiment (52+ terms)
NEGATIVE_LEXICON: list[str] = [
    # Strong bearish
    "利空", "跌停", "大跌", "暴跌", "崩盘", "闪崩", "破位", "新低",
    "死叉", "缩量", "套牢", "割肉", "踩雷", "爆仓", "崩盘",
    # Moderate bearish
    "下跌", "回调", "回落", "走弱", "跳水", "冲高回落", "飘绿", "翻绿",
    "减持", "质押", "亏损", "业绩下滑", "净利润下降", "营收下降",
    "风险", "担忧", "不确定", "承压", "疲软", "低迷", "冷淡", "萧条",
    "监管", "处罚", "退市", "ST", "暂停上市", "终止上市",
    "资金流出", "主力出逃", "北向流出", "减仓", "清仓", "割肉",
    "黑天鹅", "灰犀牛", "雷暴", "暴雷", "爆雷",
]


@dataclass
class LexiconAnalyzer:
    """Lexicon-based Chinese financial sentiment analyzer.

    Scoring formula: (pos_count - neg_count) / (pos_count + neg_count + 1)
    Output range: [-1.0, 1.0]
    The +1 denominator prevents division by zero on empty text.

    Attributes
    ----------
    positive_lexicon:
        List of bullish/positive terms.
    negative_lexicon:
        List of bearish/negative terms.
    """

    positive_lexicon: list[str] = field(default_factory=lambda: list(POSITIVE_LEXICON))
    negative_lexicon: list[str] = field(default_factory=lambda: list(NEGATIVE_LEXICON))

    def score(self, text: str) -> float:
        """Score text sentiment using lexicon matching.

        Parameters
        ----------
        text:
            Chinese text to analyze.

        Returns
        -------
        float in [-1.0, 1.0]. Positive = bullish, negative = bearish.
        """
        if not text:
            return 0.0

        pos_count = sum(1 for term in self.positive_lexicon if term in text)
        neg_count = sum(1 for term in self.negative_lexicon if term in text)

        return (pos_count - neg_count) / (pos_count + neg_count + 1)

    def score_batch(self, texts: list[str]) -> list[float]:
        """Score multiple texts. Returns list of scores in same order."""
        return [self.score(t) for t in texts]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def collect_from_source(
    platform: str,
    ticker: str,
    raw_texts: list[str],
    engagement_counts: Optional[list[int]] = None,
) -> list[SocialMediaSignal]:
    """Factory: create SocialMediaSignal list from raw texts.

    Parameters
    ----------
    platform:
        Source platform name (e.g. "weibo", "xueqiu").
    ticker:
        Related stock ticker.
    raw_texts:
        List of raw text content.
    engagement_counts:
        Optional engagement counts (likes/comments). Defaults to 0.

    Returns
    -------
    List of SocialMediaSignal with lexicon-scored sentiment.
    """
    analyzer = LexiconAnalyzer()
    signals: list[SocialMediaSignal] = []

    for i, text in enumerate(raw_texts):
        engagement = engagement_counts[i] if engagement_counts and i < len(engagement_counts) else 0
        score = analyzer.score(text)
        signals.append(
            SocialMediaSignal(
                platform=platform,
                ticker=ticker,
                content=text,
                sentiment_score=score,
                engagement_count=engagement,
            )
        )

    logger.info("Collected %d signals from %s for %s", len(signals), platform, ticker)
    return signals
