"""Tests for ReportSummarizer -- Chinese analyst research report summarization.

Covers: rating extraction, target price, thesis summary, key points,
risk factors, title detection, analyst/institution extraction,
edge cases, frozen dataclass behavior, to_dict/from_dict round-trip.
"""

from __future__ import annotations

import pytest

from synapse.nlp.report_patterns import (
    ReportRating,
    RATING_KEYWORDS,
    SECTION_MARKERS,
    count_all_patterns,
    count_by_category,
)
from synapse.nlp.report_summarizer import (
    ReportSummarizer,
    ResearchReportResult,
)
from synapse.nlp.schemas import TextDocument


# ---------------------------------------------------------------------------
# Sample research report texts
# ---------------------------------------------------------------------------

FULL_REPORT = (
    "中信证券深度研究报告\n"
    "分析师：张明 S1010521010001\n"
    "投资评级：买入\n"
    "目标价：50.00元\n"
    "\n"
    "投资要点\n"
    "· 公司业绩持续增长，盈利能力稳定\n"
    "· 行业景气度回升，市场份额提升\n"
    "· 新产品线贡献增量收入\n"
    "\n"
    "投资摘要\n"
    "公司作为行业龙头，受益于行业景气度回升。"
    "我们预计未来三年业绩将保持15%以上的复合增长率。"
    "当前估值合理，维持买入评级。\n"
    "\n"
    "风险提示\n"
    "若宏观经济下行，可能导致需求萎缩。\n"
    "行业竞争加剧，可能影响公司毛利率。\n"
)

BUY_RATING_TEXT = (
    "华泰证券研究报告\n"
    "投资评级：买入\n"
    "给予买入评级，目标价60元。"
)

HOLD_RATING_TEXT = (
    "中金公司行业研究报告\n"
    "评级建议：中性\n"
    "维持中性评级。"
)

SELL_RATING_TEXT = (
    "国泰君安研究报告\n"
    "投资评级：卖出\n"
    "下调至卖出评级。"
)

OVERWEIGHT_TEXT = (
    "海通证券研究报告\n"
    "评级建议：增持\n"
    "优于大市评级。"
)

UNDERWEIGHT_TEXT = (
    "招商证券研究报告\n"
    "投资评级：减持\n"
    "弱于大市。"
)

THESIS_TEXT = (
    "投资摘要\n"
    "公司核心竞争力突出，市场份额持续扩大。"
    "新产品放量带来业绩弹性，估值具备安全边际。"
    "预计2025年净利润增长20%。\n"
    "风险提示\n"
    "市场需求不及预期。"
)

KEY_POINTS_TEXT = (
    "核心观点\n"
    "1. 公司业绩超预期，营收同比增长25%\n"
    "2. 毛利率提升3个百分点，盈利能力改善\n"
    "3. 新产品贡献增量，打开成长空间\n"
    "4. 行业政策利好，景气度持续回升\n"
)

RISKS_TEXT = (
    "风险提示\n"
    "若原材料价格上涨，可能压缩公司利润空间。\n"
    "行业竞争加剧，市场份额面临挑战。\n"
    "海外市场需求波动，出口业务承压。\n"
)

TARGET_PRICE_RANGE_TEXT = (
    "目标价：45.00 - 55.00元\n"
    "维持买入评级。"
)

NO_RATING_TEXT = (
    "这是一份关于某公司的分析报告。\n"
    "公司业绩表现良好，未来前景可期。\n"
)

EMPTY_TEXT = ""


# ---------------------------------------------------------------------------
# Pattern count tests
# ---------------------------------------------------------------------------


class TestPatternCounts:
    """Verify pattern counts meet minimum requirements."""

    def test_total_patterns_at_least_15(self) -> None:
        """Total structure patterns must be at least 15."""
        assert count_all_patterns() >= 15

    def test_pattern_categories_covered(self) -> None:
        """All required categories have patterns."""
        counts = count_by_category()
        assert counts["title"] >= 2
        assert counts["author"] >= 1
        assert counts["institution"] >= 1
        assert counts["rating"] >= 1
        assert counts["target_price"] >= 1
        assert counts["section_markers"] >= 3

    def test_all_rating_types_covered(self) -> None:
        """All 5 rating types have keyword mappings."""
        expected = {"buy", "hold", "sell", "overweight", "underweight"}
        actual = {r.value for r in RATING_KEYWORDS.values()}
        assert expected == actual

    def test_section_markers_covered(self) -> None:
        """Required section markers exist."""
        assert "conclusion" in SECTION_MARKERS
        assert "key_points" in SECTION_MARKERS
        assert "risks" in SECTION_MARKERS


# ---------------------------------------------------------------------------
# Rating extraction tests
# ---------------------------------------------------------------------------


class TestRatingExtraction:
    """Test investment rating extraction from report text."""

    def test_extract_buy_rating(self) -> None:
        """'买入' rating maps to buy."""
        doc = TextDocument(text=BUY_RATING_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating == ReportRating.BUY

    def test_extract_hold_rating(self) -> None:
        """'中性' rating maps to hold."""
        doc = TextDocument(text=HOLD_RATING_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating == ReportRating.HOLD

    def test_extract_sell_rating(self) -> None:
        """'卖出' rating maps to sell."""
        doc = TextDocument(text=SELL_RATING_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating == ReportRating.SELL

    def test_extract_overweight_rating(self) -> None:
        """'增持' rating maps to overweight."""
        doc = TextDocument(text=OVERWEIGHT_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating == ReportRating.OVERWEIGHT

    def test_extract_underweight_rating(self) -> None:
        """'减持' rating maps to underweight."""
        doc = TextDocument(text=UNDERWEIGHT_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating == ReportRating.UNDERWEIGHT

    def test_no_rating_returns_none(self) -> None:
        """Text without rating keyword returns None."""
        doc = TextDocument(text=NO_RATING_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating is None


# ---------------------------------------------------------------------------
# Target price extraction tests
# ---------------------------------------------------------------------------


class TestTargetPriceExtraction:
    """Test target price extraction from report text."""

    def test_extract_target_price(self) -> None:
        """Extract standard target price '50.00元'."""
        doc = TextDocument(text=FULL_REPORT)
        result = ReportSummarizer().summarize(doc)
        assert result.target_price == 50.0

    def test_extract_target_price_range(self) -> None:
        """Extract target price range as midpoint."""
        doc = TextDocument(text=TARGET_PRICE_RANGE_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.target_price == 50.0

    def test_no_target_price_returns_none(self) -> None:
        """Text without target price returns None."""
        doc = TextDocument(text=NO_RATING_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.target_price is None


# ---------------------------------------------------------------------------
# Thesis summary tests
# ---------------------------------------------------------------------------


class TestThesisSummary:
    """Test thesis summary extraction."""

    def test_thesis_summary_not_empty(self) -> None:
        """Thesis summary is extracted from conclusion section."""
        doc = TextDocument(text=THESIS_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.thesis_summary != ""

    def test_thesis_summary_within_length(self) -> None:
        """Thesis summary stays within ~50-word limit."""
        doc = TextDocument(text=FULL_REPORT)
        result = ReportSummarizer().summarize(doc)
        # 200 chars is approximately 50 Chinese words
        assert len(result.thesis_summary) <= 200

    def test_thesis_summary_multiple_sentences(self) -> None:
        """Thesis summary contains content from 1-3 sentences."""
        doc = TextDocument(text=THESIS_TEXT)
        result = ReportSummarizer().summarize(doc)
        # thesis_summary is built from first 1-3 extracted sentences
        # It should contain substantive content (not just a fragment)
        assert len(result.thesis_summary) >= 10


# ---------------------------------------------------------------------------
# Key points extraction tests
# ---------------------------------------------------------------------------


class TestKeyPointsExtraction:
    """Test key investment point extraction."""

    def test_key_points_extracted(self) -> None:
        """Key points are extracted from bullet/numbered lists."""
        doc = TextDocument(text=KEY_POINTS_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert len(result.key_points) >= 2

    def test_key_points_are_strings(self) -> None:
        """Each key point is a non-empty string."""
        doc = TextDocument(text=KEY_POINTS_TEXT)
        result = ReportSummarizer().summarize(doc)
        for point in result.key_points:
            assert isinstance(point, str)
            assert len(point) >= 5


# ---------------------------------------------------------------------------
# Risk factor extraction tests
# ---------------------------------------------------------------------------


class TestRiskFactorExtraction:
    """Test risk factor identification."""

    def test_risk_factors_extracted(self) -> None:
        """Risk factors are extracted from risk section."""
        doc = TextDocument(text=RISKS_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert len(result.risk_factors) >= 1

    def test_risk_factors_are_strings(self) -> None:
        """Each risk factor is a non-empty string."""
        doc = TextDocument(text=RISKS_TEXT)
        result = ReportSummarizer().summarize(doc)
        for risk in result.risk_factors:
            assert isinstance(risk, str)
            assert len(risk) >= 5


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text_returns_defaults(self) -> None:
        """Empty text returns default ResearchReportResult."""
        doc = TextDocument(text=EMPTY_TEXT)
        result = ReportSummarizer().summarize(doc)
        assert result.report_title == ""
        assert result.rating is None
        assert result.target_price is None
        assert result.thesis_summary == ""
        assert result.key_points == ()
        assert result.risk_factors == ()

    def test_full_report_all_fields(self) -> None:
        """Full report populates multiple fields."""
        doc = TextDocument(text=FULL_REPORT)
        result = ReportSummarizer().summarize(doc)
        assert result.rating == ReportRating.BUY
        assert result.target_price == 50.0
        assert result.key_points != ()
        assert result.risk_factors != ()

    def test_institution_extracted(self) -> None:
        """Institution name is extracted from header."""
        doc = TextDocument(text=FULL_REPORT)
        result = ReportSummarizer().summarize(doc)
        assert result.institution != ""


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------


class TestFrozenDataclass:
    """Test ResearchReportResult is a proper frozen dataclass."""

    def test_frozen_immutable(self) -> None:
        """ResearchReportResult is immutable (frozen=True)."""
        result = ResearchReportResult(report_title="test")
        with pytest.raises(AttributeError):
            result.report_title = "changed"  # type: ignore[misc]

    def test_slots_attribute(self) -> None:
        """ResearchReportResult uses __slots__."""
        assert hasattr(ResearchReportResult, "__slots__")

    def test_equality(self) -> None:
        """Two identical results are equal."""
        r1 = ResearchReportResult(
            report_title="test", rating=ReportRating.BUY
        )
        r2 = ResearchReportResult(
            report_title="test", rating=ReportRating.BUY
        )
        assert r1 == r2

    def test_inequality(self) -> None:
        """Different results are not equal."""
        r1 = ResearchReportResult(report_title="a")
        r2 = ResearchReportResult(report_title="b")
        assert r1 != r2


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trip tests
# ---------------------------------------------------------------------------


class TestSerialization:
    """Test to_dict / from_dict round-trip serialization."""

    def test_round_trip_with_all_fields(self) -> None:
        """Round-trip preserves all fields."""
        original = ResearchReportResult(
            report_title="贵州茅台深度研究",
            analyst_name="张明",
            institution="中信证券",
            rating=ReportRating.BUY,
            target_price=50.0,
            thesis_summary="公司业绩持续增长。",
            key_points=("点一", "点二"),
            risk_factors=("风险一",),
        )
        data = original.to_dict()
        restored = ResearchReportResult.from_dict(data)
        assert restored == original

    def test_round_trip_with_none_fields(self) -> None:
        """Round-trip preserves None fields."""
        original = ResearchReportResult()
        data = original.to_dict()
        restored = ResearchReportResult.from_dict(data)
        assert restored == original

    def test_round_trip_from_report(self) -> None:
        """Round-trip from summarize() output."""
        doc = TextDocument(text=FULL_REPORT)
        original = ReportSummarizer().summarize(doc)
        data = original.to_dict()
        restored = ResearchReportResult.from_dict(data)
        assert restored.report_title == original.report_title
        assert restored.rating == original.rating
        assert restored.target_price == original.target_price
        assert restored.key_points == original.key_points
        assert restored.risk_factors == original.risk_factors

    def test_dict_contains_expected_keys(self) -> None:
        """to_dict output contains all expected keys."""
        result = ResearchReportResult()
        data = result.to_dict()
        expected_keys = {
            "report_title", "analyst_name", "institution",
            "rating", "target_price", "thesis_summary",
            "key_points", "risk_factors",
        }
        assert expected_keys == set(data.keys())

    def test_rating_serialized_as_string(self) -> None:
        """Rating is serialized as string value in to_dict."""
        result = ResearchReportResult(rating=ReportRating.BUY)
        data = result.to_dict()
        assert data["rating"] == "buy"

    def test_rating_none_serialized(self) -> None:
        """None rating is serialized as None."""
        result = ResearchReportResult(rating=None)
        data = result.to_dict()
        assert data["rating"] is None
