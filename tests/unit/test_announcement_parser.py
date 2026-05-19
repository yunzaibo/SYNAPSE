"""Tests for AnnouncementParser -- Chinese financial announcement parsing.

Covers: metric extraction, period detection, approximation markers,
edge cases, frozen dataclass behavior, confidence scoring.
"""

from __future__ import annotations

import pytest

from synapse.nlp.schemas import TextDocument
from synapse.nlp.announcement_parser import (
    AnnouncementParser,
    AnnouncementResult,
    FinancialMetric,
    PeriodInfo,
    _extract_sentences_by_keywords,
)
from synapse.nlp.patterns.financial_patterns import (
    detect_period,
    extract_approximation_markers,
    METRIC_PATTERNS,
    ALL_PATTERNS,
)
from synapse.nlp.text_preprocessor import TextPreprocessor


# ---------------------------------------------------------------------------
# Sample texts for testing
# ---------------------------------------------------------------------------

STANDARD_EARNINGS_TEXT = (
    "贵州茅台2024年第三季度报告。"
    "报告期内公司实现营业收入1,234.56亿元，同比增长15.3%。"
    "归属于上市公司股东的净利润为608.28亿元，同比增长13.5%。"
    "基本每股收益为48.42元。"
    "加权平均净资产收益率为32.15%。"
    "销售毛利率为91.87%。"
    "公司经营性现金流为523.41亿元。"
    "总资产为2,876.54亿元。"
)

APPROX_TEXT = (
    "公司2024年年度报告。"
    "营业收入约为1,500亿元，净利润超过200亿元。"
    "近三个月ROE达到25.6%。"
    "毛利率不足45%。"
)

QUARTERLY_TEXTS = {
    "Q1": "2024年第一季度报告 营业收入100亿元",
    "Q2": "2024年第二季度报告 营业收入200亿元",
    "Q3": "2024年第三季度报告 营业收入300亿元",
    "Q4": "2024年第四季度报告 营业收入400亿元",
}

ANNUAL_TEXT = "2024年年度报告 营业收入500亿元"
SEMI_ANNUAL_TEXT = "2024年半年度报告 营业收入250亿元"
MID_YEAR_TEXT = "2024年中期报告 营业收入250亿元"

GROWTH_TEXT = (
    "公司业绩增长显著，营收创新高，净利润大幅上升。"
    "毛利率同比增加5个百分点。"
)

RISK_TEXT = (
    "公司面临市场风险，营收下降，净利润亏损扩大。"
    "经营承压，毛利率恶化。"
)


# ---------------------------------------------------------------------------
# Financial metric extraction tests
# ---------------------------------------------------------------------------


class TestMetricExtraction:
    """Test financial metric extraction from announcement text."""

    def test_extract_revenue(self) -> None:
        """Revenue is extracted from standard earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-001")
        result = parser.parse(doc)

        revenue_metrics = [m for m in result.metrics if m.name == "revenue"]
        assert len(revenue_metrics) >= 1
        assert revenue_metrics[0].value is not None
        assert revenue_metrics[0].value > 0

    def test_extract_net_profit(self) -> None:
        """Net profit is extracted from standard earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-002")
        result = parser.parse(doc)

        profit_metrics = [m for m in result.metrics if m.name == "net_profit"]
        assert len(profit_metrics) >= 1
        assert profit_metrics[0].value is not None

    def test_extract_eps(self) -> None:
        """EPS is extracted from standard earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-003")
        result = parser.parse(doc)

        eps_metrics = [m for m in result.metrics if m.name == "eps"]
        assert len(eps_metrics) >= 1
        assert eps_metrics[0].value is not None
        assert eps_metrics[0].value > 0

    def test_extract_roe(self) -> None:
        """ROE is extracted from standard earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-004")
        result = parser.parse(doc)

        roe_metrics = [m for m in result.metrics if m.name == "roe"]
        assert len(roe_metrics) >= 1
        assert roe_metrics[0].value is not None

    def test_extract_gross_margin(self) -> None:
        """Gross margin is extracted from standard earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-005")
        result = parser.parse(doc)

        margin_metrics = [m for m in result.metrics if m.name == "gross_margin"]
        assert len(margin_metrics) >= 1
        assert margin_metrics[0].value is not None

    def test_extract_five_plus_metrics(self) -> None:
        """At least 5 different metric types are extracted from earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-006")
        result = parser.parse(doc)

        metric_names = {m.name for m in result.metrics}
        assert len(metric_names) >= 5
        assert "revenue" in metric_names
        assert "net_profit" in metric_names
        assert "eps" in metric_names
        assert "roe" in metric_names
        assert "gross_margin" in metric_names


# ---------------------------------------------------------------------------
# Period detection tests
# ---------------------------------------------------------------------------


class TestPeriodDetection:
    """Test reporting period detection."""

    def test_detect_q1(self) -> None:
        """Q1 period is detected from quarterly text."""
        result = detect_period(QUARTERLY_TEXTS["Q1"])
        assert result is not None
        assert result["year"] == "2024"
        assert result["period_type"] == "Q1"

    def test_detect_q2(self) -> None:
        """Q2 period is detected from quarterly text."""
        result = detect_period(QUARTERLY_TEXTS["Q2"])
        assert result is not None
        assert result["period_type"] == "Q2"

    def test_detect_q3(self) -> None:
        """Q3 period is detected from quarterly text."""
        result = detect_period(QUARTERLY_TEXTS["Q3"])
        assert result is not None
        assert result["period_type"] == "Q3"

    def test_detect_q4(self) -> None:
        """Q4 period is detected from quarterly text."""
        result = detect_period(QUARTERLY_TEXTS["Q4"])
        assert result is not None
        assert result["period_type"] == "Q4"

    def test_detect_annual(self) -> None:
        """Annual period is detected from annual report text."""
        result = detect_period(ANNUAL_TEXT)
        assert result is not None
        assert result["year"] == "2024"
        assert result["period_type"] == "annual"

    def test_detect_semi_annual(self) -> None:
        """Semi-annual period is detected."""
        result = detect_period(SEMI_ANNUAL_TEXT)
        assert result is not None
        assert result["period_type"] == "semi_annual"

    def test_period_in_parser_output(self) -> None:
        """Parser outputs correct PeriodInfo for Q3 earnings text."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-period")
        result = parser.parse(doc)

        assert result.period_info is not None
        assert result.period_info.year == "2024"
        assert result.period_info.period_type == "Q3"
        assert "Q3" in result.period_info.period_label


# ---------------------------------------------------------------------------
# Approximation marker tests
# ---------------------------------------------------------------------------


class TestApproximationMarkers:
    """Test approximation marker extraction and preservation."""

    def test_extract_approx_markers(self) -> None:
        """Approximation markers are extracted from text."""
        markers = extract_approximation_markers(APPROX_TEXT)
        assert "约" in markers
        assert "超" in markers
        assert "近" in markers
        assert "不足" in markers

    def test_approx_in_parser_result(self) -> None:
        """Parser preserves approximation markers in result."""
        parser = AnnouncementParser()
        doc = TextDocument(text=APPROX_TEXT, doc_id="test-approx")
        result = parser.parse(doc)

        assert len(result.approximation_markers) > 0
        assert "约" in result.approximation_markers

    def test_metric_approximation_field(self) -> None:
        """Individual metrics capture their approximation markers."""
        parser = AnnouncementParser()
        doc = TextDocument(text=APPROX_TEXT, doc_id="test-approx2")
        result = parser.parse(doc)

        approx_metrics = [m for m in result.metrics if m.approximation is not None]
        assert len(approx_metrics) > 0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test parser behavior with edge cases."""

    def test_empty_text(self) -> None:
        """Empty text returns empty result with no exception."""
        parser = AnnouncementParser()
        doc = TextDocument(text="", doc_id="test-empty")
        result = parser.parse(doc)

        assert isinstance(result, AnnouncementResult)
        assert len(result.metrics) == 0
        assert result.period_info is None
        assert result.confidence == 0.0

    def test_malformed_text(self) -> None:
        """Malformed text returns result without exception."""
        parser = AnnouncementParser()
        doc = TextDocument(text="!!!@@@###$$$%%%", doc_id="test-malformed")
        result = parser.parse(doc)

        assert isinstance(result, AnnouncementResult)
        assert len(result.metrics) == 0

    def test_no_period_text(self) -> None:
        """Text without period info returns None period_info."""
        parser = AnnouncementParser()
        doc = TextDocument(
            text="公司实现营业收入100亿元。", doc_id="test-noperiod"
        )
        result = parser.parse(doc)

        assert result.period_info is None

    def test_abbreviation_expansion(self) -> None:
        """Abbreviations are expanded before metric extraction."""
        text_with_abbr = "公司营收100亿元，净利20亿元，EPS为1.5元"
        parser = AnnouncementParser()
        doc = TextDocument(text=text_with_abbr, doc_id="test-abbr")
        result = parser.parse(doc)

        # Should still extract metrics despite abbreviations
        assert len(result.metrics) >= 2


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------


class TestFrozenDataclass:
    """Test that dataclasses are properly frozen and round-trip."""

    def test_announcement_result_frozen(self) -> None:
        """AnnouncementResult is frozen (immutable)."""
        result = AnnouncementResult(confidence=0.9)
        with pytest.raises(AttributeError):
            result.confidence = 0.5  # type: ignore[misc]

    def test_financial_metric_frozen(self) -> None:
        """FinancialMetric is frozen (immutable)."""
        metric = FinancialMetric(name="revenue", value=100.0)
        with pytest.raises(AttributeError):
            metric.name = "profit"  # type: ignore[misc]

    def test_period_info_frozen(self) -> None:
        """PeriodInfo is frozen (immutable)."""
        info = PeriodInfo(year="2024", period_type="Q3")
        with pytest.raises(AttributeError):
            info.year = "2025"  # type: ignore[misc]

    def test_announcement_result_to_dict_from_dict(self) -> None:
        """AnnouncementResult round-trips through to_dict/from_dict."""
        original = AnnouncementResult(
            metrics=(
                FinancialMetric(name="revenue", value=1234.56, confidence=0.9),
                FinancialMetric(name="net_profit", value=608.28, confidence=0.85),
            ),
            period_info=PeriodInfo(year="2024", period_type="Q3", period_label="2024 Q3"),
            growth_highlights=("revenue grew 15%",),
            risk_factors=("market risk",),
            entities=(),
            approximation_markers=("约",),
            confidence=0.75,
            processing_time_ms=42.5,
        )

        d = original.to_dict()
        restored = AnnouncementResult.from_dict(d)

        assert restored.confidence == original.confidence
        assert len(restored.metrics) == 2
        assert restored.metrics[0].name == "revenue"
        assert restored.metrics[0].value == 1234.56
        assert restored.period_info is not None
        assert restored.period_info.year == "2024"
        assert restored.growth_highlights == ("revenue grew 15%",)
        assert restored.approximation_markers == ("约",)

    def test_financial_metric_to_dict_from_dict(self) -> None:
        """FinancialMetric round-trips through to_dict/from_dict."""
        original = FinancialMetric(
            name="eps", value=48.42, raw_text="EPS为48.42元",
            confidence=0.9, approximation="约"
        )
        d = original.to_dict()
        restored = FinancialMetric.from_dict(d)

        assert restored.name == "eps"
        assert restored.value == 48.42
        assert restored.raw_text == "EPS为48.42元"
        assert restored.approximation == "约"


# ---------------------------------------------------------------------------
# Confidence scoring tests
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Test confidence score computation."""

    def test_confidence_with_metrics(self) -> None:
        """Confidence is higher when more metrics are found."""
        parser = AnnouncementParser()
        doc_full = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-conf-full")
        doc_empty = TextDocument(text="公司公告", doc_id="test-conf-empty")

        result_full = parser.parse(doc_full)
        result_empty = parser.parse(doc_empty)

        assert result_full.confidence > result_empty.confidence

    def test_confidence_range(self) -> None:
        """Confidence score is always in [0.0, 1.0]."""
        parser = AnnouncementParser()
        doc = TextDocument(text=STANDARD_EARNINGS_TEXT, doc_id="test-conf-range")
        result = parser.parse(doc)

        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Growth / risk extraction tests
# ---------------------------------------------------------------------------


class TestGrowthRiskExtraction:
    """Test growth highlights and risk factor extraction."""

    def test_growth_highlights(self) -> None:
        """Growth-related sentences are extracted."""
        parser = AnnouncementParser()
        doc = TextDocument(text=GROWTH_TEXT, doc_id="test-growth")
        result = parser.parse(doc)

        assert len(result.growth_highlights) > 0

    def test_risk_factors(self) -> None:
        """Risk-related sentences are extracted."""
        parser = AnnouncementParser()
        doc = TextDocument(text=RISK_TEXT, doc_id="test-risk")
        result = parser.parse(doc)

        assert len(result.risk_factors) > 0


# ---------------------------------------------------------------------------
# Pattern registry tests
# ---------------------------------------------------------------------------


class TestPatternRegistry:
    """Test that the pattern registry has sufficient coverage."""

    def test_pattern_count(self) -> None:
        """At least 20 regex patterns are defined."""
        assert len(ALL_PATTERNS) >= 20

    def test_metric_categories_covered(self) -> None:
        """Core metric categories are all present in the registry."""
        expected_categories = {
            "revenue", "net_profit", "eps", "roe", "gross_margin",
        }
        assert expected_categories.issubset(set(METRIC_PATTERNS.keys()))

    def test_all_patterns_compiled(self) -> None:
        """All patterns are compiled regex objects."""
        for pattern in ALL_PATTERNS:
            assert hasattr(pattern.pattern, "search")
            assert hasattr(pattern.pattern, "findall")


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Integration test for the full parsing pipeline."""

    def test_full_earnings_parse(self) -> None:
        """Full pipeline parses standard earnings text correctly."""
        parser = AnnouncementParser()
        doc = TextDocument(
            text=STANDARD_EARNINGS_TEXT,
            doc_id="integration-001",
            source_type="announcement",
        )
        result = parser.parse(doc)

        # Verify result type
        assert isinstance(result, AnnouncementResult)

        # Verify metrics extracted
        assert len(result.metrics) >= 5
        metric_names = {m.name for m in result.metrics}
        assert "revenue" in metric_names
        assert "net_profit" in metric_names
        assert "eps" in metric_names
        assert "roe" in metric_names
        assert "gross_margin" in metric_names

        # Verify period detected
        assert result.period_info is not None
        assert result.period_info.period_type == "Q3"

        # Verify processing time recorded
        assert result.processing_time_ms >= 0

        # Verify confidence is reasonable
        assert 0.3 <= result.confidence <= 1.0
