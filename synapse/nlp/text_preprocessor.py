"""TextPreprocessor -- Chinese financial text normalization.

Handles abbreviation expansion, number normalization (亿/万 to float),
and approximation marker extraction for downstream NER processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Abbreviation dictionary (50+ financial term expansions)
# ---------------------------------------------------------------------------

ABBREVIATIONS: dict[str, str] = {
    # Revenue / profit
    "营收": "营业收入",
    "净利": "净利润",
    "扣非": "扣除非经常性损益",
    "归母": "归属于母公司所有者",
    "归母净利": "归属于母公司所有者的净利润",
    "扣非净利": "扣除非经常性损益后的净利润",
    "毛利": "毛利润",
    "营业利润": "营业利润",
    "利润总额": "利润总额",
    "净利润率": "净利润率",
    # Balance sheet
    "净资产": "股东权益",
    "总资产": "资产总额",
    "总负债": "负债总额",
    "流动资产": "流动资产",
    "固定资产": "固定资产",
    "无形资产": "无形资产",
    "商誉": "商誉",
    # Cash flow
    "经营性现金流": "经营活动产生的现金流量净额",
    "投资性现金流": "投资活动产生的现金流量净额",
    "筹资性现金流": "筹资活动产生的现金流量净额",
    "自由现金流": "企业自由现金流量",
    # Financial ratios
    "ROE": "净资产收益率",
    "ROA": "总资产收益率",
    "ROIC": "投入资本回报率",
    "EPS": "每股收益",
    "PE": "市盈率",
    "PB": "市净率",
    "PS": "市销率",
    "PEG": "市盈率相对盈利增长比率",
    "EBITDA": "息税折旧摊销前利润",
    "EV": "企业价值",
    "FCFF": "企业自由现金流量",
    "FCFE": "股权自由现金流量",
    "DPS": "每股股利",
    "BVPS": "每股净资产",
    # Market
    "A股": "A股市场",
    "港股": "香港股票市场",
    "美股": "美国股票市场",
    "北向资金": "沪港通和深港通北向资金",
    "北向": "沪港通和深港通北向资金",
    "南向资金": "沪港通和深港通南向资金",
    "融资融券": "融资融券交易",
    "两融": "融资融券交易",
    "大宗交易": "大宗交易",
    "定增": "定向增发",
    "增发": "增发",
    "配股": "配股",
    "回购": "股份回购",
    "减持": "股份减持",
    "增持": "股份增持",
    "质押": "股权质押",
    # Industry / sector
    "新能源": "新能源行业",
    "半导体": "半导体行业",
    "芯片": "芯片行业",
    "医药": "医药行业",
    "消费": "消费行业",
    "科技": "科技行业",
    "金融": "金融行业",
    "地产": "房地产行业",
    "白酒": "白酒行业",
    "光伏": "光伏行业",
    "锂电": "锂电池行业",
    "储能": "储能行业",
    "军工": "军工行业",
}

# ---------------------------------------------------------------------------
# Number normalization patterns
# ---------------------------------------------------------------------------

# Pattern: number + (亿|万|千|百) suffix
_NUMBER_PATTERN = re.compile(
    r"([+-]?\d+(?:\.\d+)?)\s*(亿|万亿|百万|千万|万|千|百)"
)


def _scale_factor(unit: str) -> float:
    """Return the multiplier for a Chinese number unit."""
    mapping = {
        "万亿": 1e12,
        "亿": 1e8,
        "千万": 1e7,
        "百万": 1e6,
        "万": 1e4,
        "千": 1e3,
        "百": 1e2,
    }
    return mapping.get(unit, 1.0)


# ---------------------------------------------------------------------------
# Approximation markers
# ---------------------------------------------------------------------------

APPROXIMATION_MARKERS = {"约", "超", "近", "逾", "不足", "不足", "接近", "大概", "估计", "预计"}


# ---------------------------------------------------------------------------
# PreprocessedText result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PreprocessedText:
    """Result of text preprocessing.

    Attributes
    ----------
    original:
        Original input text.
    expanded:
        Text with abbreviations expanded and numbers normalized.
    normalized_numbers:
        Mapping of normalized number strings to their float values.
    approximation_markers:
        List of approximation markers found in the text.
    """

    original: str = ""
    expanded: str = ""
    normalized_numbers: dict[str, float] = field(default_factory=dict)
    approximation_markers: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "expanded": self.expanded,
            "normalized_numbers": dict(self.normalized_numbers),
            "approximation_markers": list(self.approximation_markers),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PreprocessedText:
        return cls(
            original=data.get("original", ""),
            expanded=data.get("expanded", ""),
            normalized_numbers=data.get("normalized_numbers", {}),
            approximation_markers=tuple(data.get("approximation_markers", [])),
        )


# ---------------------------------------------------------------------------
# TextPreprocessor
# ---------------------------------------------------------------------------

@dataclass
class TextPreprocessor:
    """Chinese financial text preprocessor.

    Performs abbreviation expansion, number normalization, and
    approximation marker extraction.
    """

    abbreviations: dict[str, str] = field(default_factory=lambda: dict(ABBREVIATIONS))

    def expand_abbreviations(self, text: str) -> str:
        """Expand financial abbreviations in text.

        Parameters
        ----------
        text:
            Input text potentially containing abbreviations.

        Returns
        -------
        Text with abbreviations replaced by full forms.
        """
        if not text:
            return text

        result = text
        # Sort by length descending to avoid partial matches (e.g. "归母" before "归母净利")
        for abbr, full in sorted(self.abbreviations.items(), key=lambda x: len(x[0]), reverse=True):
            result = result.replace(abbr, full)
        return result

    def normalize_numbers(self, text: str) -> tuple[str, dict[str, float]]:
        """Normalize Chinese number expressions to float values.

        Parameters
        ----------
        text:
            Input text with Chinese number expressions.

        Returns
        -------
        Tuple of (normalized text, mapping of original expression to float value).
        """
        if not text:
            return text, {}

        normalized_map: dict[str, float] = {}

        def _replace_match(m: re.Match) -> str:
            num_str, unit = m.group(1), m.group(2)
            value = float(num_str) * _scale_factor(unit)
            original = m.group(0)
            normalized_map[original] = value
            return str(value)

        result = _NUMBER_PATTERN.sub(_replace_match, text)
        return result, normalized_map

    def extract_approximation_markers(self, text: str) -> list[str]:
        """Extract approximation markers from text.

        Parameters
        ----------
        text:
            Input text.

        Returns
        -------
        List of approximation markers found (preserving order of appearance).
        """
        if not text:
            return []

        markers: list[str] = []
        for marker in APPROXIMATION_MARKERS:
            if marker in text and marker not in markers:
                markers.append(marker)
        return markers

    def preprocess(self, text: str) -> PreprocessedText:
        """Run full preprocessing pipeline on text.

        Parameters
        ----------
        text:
            Input Chinese financial text.

        Returns
        -------
        PreprocessedText with expanded text, normalized numbers, and markers.
        """
        if not text:
            return PreprocessedText(original="", expanded="", normalized_numbers={}, approximation_markers=())

        # Step 1: Expand abbreviations
        expanded = self.expand_abbreviations(text)

        # Step 2: Normalize numbers
        expanded_with_numbers, normalized_numbers = self.normalize_numbers(expanded)

        # Step 3: Extract approximation markers from original text
        markers = self.extract_approximation_markers(text)

        return PreprocessedText(
            original=text,
            expanded=expanded_with_numbers,
            normalized_numbers=normalized_numbers,
            approximation_markers=tuple(markers),
        )
