"""Tests for PolicyUnderstander -- F-040 Policy Document Understander.

Covers: issuing body detection, effective date extraction, document type
classification, sector mapping, key changes, sentiment impact, frozen
dataclass behavior, serialization round-trips, and edge cases.
14 test methods.
"""

from __future__ import annotations

import pytest

from synapse.nlp.schemas import TextDocument
from synapse.nlp.policy_understander import PolicyResult, PolicyUnderstander
from synapse.nlp.policy_patterns import (
    IssuingBodyMatch,
    classify_document_type,
    detect_issuing_body,
    extract_effective_date,
    extract_key_changes,
)
from synapse.nlp.sector_mapper import SectorMapper, SectorMatch


# ---------------------------------------------------------------------------
# PolicyResult frozen dataclass
# ---------------------------------------------------------------------------

class TestPolicyResult:
    """Tests for PolicyResult frozen dataclass."""

    def test_frozen_and_slots(self) -> None:
        """PolicyResult must be frozen and use slots."""
        result = PolicyResult(issuing_body="PBOC")
        with pytest.raises(AttributeError):
            result.issuing_body = "CSRC"  # type: ignore[misc]

    def test_default_values(self) -> None:
        result = PolicyResult()
        assert result.issuing_body == "unknown"
        assert result.document_type == "guidance"
        assert result.effective_date is None
        assert result.key_changes == ()
        assert result.affected_sectors == ()
        assert result.sentiment_impact == {}
        assert result.processing_time_ms == 0.0

    def test_to_dict_roundtrip(self) -> None:
        original = PolicyResult(
            issuing_body="PBOC",
            document_type="monetary_policy",
            effective_date="2026-06-01",
            key_changes=("下调存款准备金率",),
            affected_sectors=("banking",),
            sentiment_impact={"banking": "bullish"},
            processing_time_ms=1.5,
        )
        d = original.to_dict()
        restored = PolicyResult.from_dict(d)
        assert restored.issuing_body == original.issuing_body
        assert restored.document_type == original.document_type
        assert restored.effective_date == original.effective_date
        assert restored.key_changes == original.key_changes
        assert restored.affected_sectors == original.affected_sectors
        assert restored.sentiment_impact == original.sentiment_impact

    def test_to_dict_types(self) -> None:
        """to_dict must return plain lists, not tuples."""
        result = PolicyResult(
            key_changes=("a", "b"),
            affected_sectors=("banking",),
        )
        d = result.to_dict()
        assert isinstance(d["key_changes"], list)
        assert isinstance(d["affected_sectors"], list)
        assert isinstance(d["sentiment_impact"], dict)


# ---------------------------------------------------------------------------
# Issuing body detection
# ---------------------------------------------------------------------------

class TestIssuingBodyDetection:
    """Tests for issuing body detection."""

    def test_pboc_full_name(self) -> None:
        result = detect_issuing_body("中国人民银行决定下调存款准备金率")
        assert result.body == "PBOC"
        assert result.matched_keyword == "中国人民银行"

    def test_pboc_abbreviation(self) -> None:
        result = detect_issuing_body("央行宣布降息")
        assert result.body == "PBOC"
        assert result.matched_keyword == "央行"

    def test_csrc_full_name(self) -> None:
        result = detect_issuing_body("中国证券监督管理委员会发布IPO新规")
        assert result.body == "CSRC"
        assert result.matched_keyword == "中国证券监督管理委员会"

    def test_csrc_short_name(self) -> None:
        result = detect_issuing_body("证监会发布上市公司管理办法")
        assert result.body == "CSRC"

    def test_state_council(self) -> None:
        result = detect_issuing_body("国务院关于促进资本市场发展的通知")
        assert result.body == "State_Council"

    def test_unknown_body(self) -> None:
        result = detect_issuing_body("某公司发布公告")
        assert result.body == "unknown"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Effective date extraction
# ---------------------------------------------------------------------------

class TestEffectiveDateExtraction:
    """Tests for effective date extraction."""

    def test_date_chinese_format(self) -> None:
        text = "本办法自2026年6月1日起施行"
        result = extract_effective_date(text)
        assert result == "2026-06-01"

    def test_date_label_format(self) -> None:
        text = "生效日期：2025-12-31"
        result = extract_effective_date(text)
        assert result == "2025-12-31"

    def test_date_no_match(self) -> None:
        text = "本规定自公布之日起施行"
        result = extract_effective_date(text)
        assert result == "upon_publish"


# ---------------------------------------------------------------------------
# Document type classification
# ---------------------------------------------------------------------------

class TestDocumentTypeClassification:
    """Tests for document type classification."""

    def test_monetary_policy(self) -> None:
        text = "中国人民银行决定下调存款准备金率0.5个百分点"
        assert classify_document_type(text) == "monetary_policy"

    def test_enforcement(self) -> None:
        text = "对某证券公司处以罚款行政处罚"
        assert classify_document_type(text) == "enforcement"

    def test_regulatory_rule(self) -> None:
        text = "证券公司合规管理办法实施细则"
        assert classify_document_type(text) == "regulatory_rule"

    def test_guidance_default(self) -> None:
        text = "关于进一步做好某项工作的通知"
        assert classify_document_type(text) == "guidance"


# ---------------------------------------------------------------------------
# Sector mapping
# ---------------------------------------------------------------------------

class TestSectorMapping:
    """Tests for sector mapping via SectorMapper."""

    def test_banking_sector(self) -> None:
        mapper = SectorMapper()
        matches = mapper.map_to_sectors("央行下调存款准备金率，利好银行板块")
        sectors = [m.sector for m in matches]
        assert "banking" in sectors

    def test_multiple_sectors(self) -> None:
        mapper = SectorMapper()
        matches = mapper.map_to_sectors(
            "房地产和银行相关政策调整，股市可能受影响"
        )
        sectors = [m.sector for m in matches]
        assert "banking" in sectors
        assert "real_estate" in sectors

    def test_sector_names_convenience(self) -> None:
        mapper = SectorMapper()
        names = mapper.map_to_sector_names("能源价格改革，光伏行业受益")
        assert "energy" in names

    def test_empty_text(self) -> None:
        mapper = SectorMapper()
        assert mapper.map_to_sectors("") == []

    def test_no_match(self) -> None:
        mapper = SectorMapper()
        assert mapper.map_to_sectors("今天天气真好") == []


# ---------------------------------------------------------------------------
# Key change extraction
# ---------------------------------------------------------------------------

class TestKeyChangeExtraction:
    """Tests for key change extraction."""

    def test_extract_change(self) -> None:
        text = "自2026年6月1日起调整存款准备金率政策施行"
        changes = extract_key_changes(text)
        assert len(changes) >= 1

    def test_no_changes(self) -> None:
        text = "今天天气很好"
        changes = extract_key_changes(text)
        assert changes == ()


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestPolicyUnderstanderPipeline:
    """Integration tests for the full PolicyUnderstander pipeline."""

    def test_pboc_document(self) -> None:
        understander = PolicyUnderstander()
        doc = TextDocument(
            text="中国人民银行决定自2026年6月1日起下调存款准备金率0.5个百分点，"
                 "以支持实体经济发展。商业银行信贷投放将增加。",
            doc_id="doc-001",
        )
        result = understander.understand(doc)
        assert result.issuing_body == "PBOC"
        assert result.effective_date == "2026-06-01"
        assert "banking" in result.affected_sectors

    def test_csrc_document(self) -> None:
        understander = PolicyUnderstander()
        doc = TextDocument(
            text="中国证监会发布证券公司管理办法，加强券商合规管理。",
            doc_id="doc-002",
        )
        result = understander.understand(doc)
        assert result.issuing_body == "CSRC"
        assert result.document_type == "regulatory_rule"
        assert "securities" in result.affected_sectors

    def test_state_council_document(self) -> None:
        understander = PolicyUnderstander()
        doc = TextDocument(
            text="国务院办公厅关于促进房地产市场平稳健康发展的通知",
            doc_id="doc-003",
        )
        result = understander.understand(doc)
        assert result.issuing_body == "State_Council"
        assert "real_estate" in result.affected_sectors

    def test_empty_document(self) -> None:
        understander = PolicyUnderstander()
        result = understander.understand(TextDocument(text=""))
        assert result.issuing_body == "unknown"
        assert result.processing_time_ms == 0.0

    def test_sentiment_impact(self) -> None:
        understander = PolicyUnderstander()
        doc = TextDocument(
            text="中国人民银行下调存款准备金率，支持银行信贷投放，利好银行业。",
            doc_id="doc-004",
        )
        result = understander.understand(doc)
        assert result.sentiment_impact.get("banking") == "bullish"

    def test_to_dict_from_dict_roundtrip(self) -> None:
        understander = PolicyUnderstander()
        doc = TextDocument(
            text="中国人民银行决定自2026年7月1日起调整存款准备金率",
            doc_id="doc-005",
        )
        result = understander.understand(doc)
        d = result.to_dict()
        restored = PolicyResult.from_dict(d)
        assert restored.issuing_body == result.issuing_body
        assert restored.document_type == result.document_type
        assert restored.effective_date == result.effective_date
        assert restored.affected_sectors == result.affected_sectors
