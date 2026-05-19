"""AspectDetector -- Keyword-based financial aspect identification.

Identifies financial aspects (earnings, management, market, regulatory, risk)
in text segments using keyword matching. Returns (aspect, sentence) pairs
for downstream per-aspect sentiment analysis.

Part of P4 Chinese Financial NLP Layer (F-039).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Aspect keyword dictionaries
# ---------------------------------------------------------------------------

ASPECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "earnings": (
        "业绩", "利润", "营收", "净利", "营收增长", "净利润", "盈利", "亏损",
        "毛利", "毛利率", "净利率", "ROE", "EPS", "每股收益", "扣非",
        "归母净利", "业绩增长", "业绩下滑", "超预期", "不及预期", "扭亏",
        "增利", "降利", "分红", "派息", "股息", "年报", "季报", "中报",
        "财报", "业绩预告", "业绩快报", "预增", "预减", "预亏", "预盈",
    ),
    "management": (
        "管理层", "CEO", "董事长", "总经理", "总裁", "高管", "董事",
        "监事", "独立董事", "实控人", "控股股东", "大股东", "创始人",
        "换届", "辞职", "罢免", "任命", "增持", "减持", "质押",
        "回购", "股权转让", "股权激励", "员工持股", "定增", "增发",
    ),
    "market": (
        "市场", "股价", "估值", "市盈率", "PE", "PB", "市值",
        "成交量", "换手率", "涨停", "跌停", "大涨", "大跌", "暴涨",
        "暴跌", "反弹", "回调", "突破", "破位", "新高", "新低",
        "北向资金", "主力", "资金流入", "资金流出", "融资融券",
        "量价齐升", "放量", "缩量", "金叉", "死叉", "板块", "行业",
        "大盘", "指数", "沪深", "创业板", "科创板", "港股通",
    ),
    "regulatory": (
        "政策", "监管", "合规", "法规", "条例", "办法", "通知",
        "意见", "规定", "证监会", "银保监", "央行", "发改委",
        "工信部", "财政部", "税务", "关税", "反垄断", "审查",
        "处罚", "罚款", "警告", "责令", "整改", "退市", "ST",
        "暂停上市", "终止上市", "注册制", "核准制", "IPO",
        "再融资", "减持新规", "印花税", "降准", "降息",
    ),
    "risk": (
        "风险", "诉讼", "处罚", "违规", "暴雷", "爆雷", "踩雷",
        "商誉减值", "坏账", "应收", "质押风险", "债务", "违约",
        "信用风险", "流动性风险", "市场风险", "操作风险", "合规风险",
        "黑天鹅", "灰犀牛", "不确定性", "承压", "下行", "衰退",
        "萧条", "崩盘", "闪崩", "爆仓", "清盘", "破产", "重整",
        "诉讼纠纷", "仲裁", "监管约谈", "立案调查",
    ),
}


# ---------------------------------------------------------------------------
# AspectResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectResult:
    """Result of aspect detection for a single text segment.

    Attributes
    ----------
    aspect:
        Identified financial aspect (e.g. "earnings", "market").
    sentence:
        The text segment where the aspect was detected.
    keyword:
        The matched keyword that triggered detection.
    """

    aspect: str = ""
    sentence: str = ""
    keyword: str = ""

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect,
            "sentence": self.sentence,
            "keyword": self.keyword,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AspectResult:
        return cls(
            aspect=data.get("aspect", ""),
            sentence=data.get("sentence", ""),
            keyword=data.get("keyword", ""),
        )


# ---------------------------------------------------------------------------
# AspectDetector
# ---------------------------------------------------------------------------

# Sentence splitter: Chinese period, semicolon, newline, or comma followed by space
_SENTENCE_SPLIT_RE = re.compile(r"[。；\n]+|，\s*")


@dataclass(frozen=True, slots=True)
class AspectDetector:
    """Keyword-based financial aspect detector.

    Identifies financial aspects in text segments using keyword matching.
    Supports 5 aspects: earnings, management, market, regulatory, risk.

    Usage::

        detector = AspectDetector()
        results = detector.detect("业绩大幅增长超预期，股价涨停")
        # -> [AspectResult(aspect="earnings", ...), AspectResult(aspect="market", ...)]

    Attributes
    ----------
    aspect_keywords:
        Mapping of aspect name to keyword tuples. Can be customized.
    min_keyword_length:
        Minimum keyword length to match (default 2).
    """

    aspect_keywords: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(ASPECT_KEYWORDS)
    )
    min_keyword_length: int = 2

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences for per-segment analysis.

        Parameters
        ----------
        text:
            Input Chinese text.

        Returns
        -------
        List of non-empty sentence strings.
        """
        if not text:
            return []
        parts = _SENTENCE_SPLIT_RE.split(text)
        return [p.strip() for p in parts if p.strip()]

    def detect_aspects(self, text: str) -> list[tuple[str, str]]:
        """Detect financial aspects in text.

        Parameters
        ----------
        text:
            Chinese financial text to analyze.

        Returns
        -------
        List of (aspect, sentence) pairs. Each pair indicates that the
        aspect was identified in the given sentence segment.
        """
        results: list[tuple[str, str]] = []

        for sentence in self._split_sentences(text):
            for aspect, keywords in self.aspect_keywords.items():
                for kw in keywords:
                    if len(kw) < self.min_keyword_length:
                        continue
                    if kw in sentence:
                        results.append((aspect, sentence))
                        break  # One match per aspect per sentence is enough

        return results

    def detect(self, text: str) -> list[AspectResult]:
        """Detect aspects with full detail (aspect, sentence, keyword).

        Parameters
        ----------
        text:
            Chinese financial text to analyze.

        Returns
        -------
        List of AspectResult with aspect name, matched sentence, and keyword.
        """
        results: list[AspectResult] = []

        for sentence in self._split_sentences(text):
            for aspect, keywords in self.aspect_keywords.items():
                for kw in keywords:
                    if len(kw) < self.min_keyword_length:
                        continue
                    if kw in sentence:
                        results.append(AspectResult(
                            aspect=aspect,
                            sentence=sentence,
                            keyword=kw,
                        ))
                        break  # One match per aspect per sentence

        return results

    def detect_single(self, text: str) -> list[str]:
        """Detect which aspects are present in text (unique aspect names).

        Parameters
        ----------
        text:
            Chinese financial text to analyze.

        Returns
        -------
        Sorted list of unique aspect names found.
        """
        seen: set[str] = set()
        for sentence in self._split_sentences(text):
            for aspect, keywords in self.aspect_keywords.items():
                if aspect in seen:
                    continue
                for kw in keywords:
                    if len(kw) < self.min_keyword_length:
                        continue
                    if kw in sentence:
                        seen.add(aspect)
                        break
        return sorted(seen)

    def supported_aspects(self) -> list[str]:
        """Return list of supported aspect names.

        Returns
        -------
        Sorted list of aspect names.
        """
        return sorted(self.aspect_keywords.keys())
