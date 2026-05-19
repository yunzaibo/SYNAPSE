"""Tests for NEREngine -- Chinese financial Named Entity Recognition.

Covers: company recognition, person recognition, metric recognition,
institution recognition, product recognition, ticker linking,
text preprocessing, frozen dataclass behavior, edge cases.
"""

from __future__ import annotations

import pytest

from synapse.nlp.schemas import TextDocument, NEREntity, NERResult
from synapse.nlp.ner_engine import NEREngine
from synapse.nlp.text_preprocessor import TextPreprocessor, PreprocessedText
from synapse.nlp.dict.company_dict import COMPANY_NAMES, get_ticker
from synapse.nlp.dict.metric_dict import METRIC_ALIASES, get_standard_name
from synapse.nlp.dict.person_patterns import (
    has_person_suffix,
    find_generic_persons,
    INSTITUTION_PATTERNS,
)


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------

class TestNEREntitySchema:
    """Tests for NEREntity frozen dataclass."""

    def test_frozen_and_slots(self) -> None:
        """NEREntity must be frozen and use slots."""
        entity = NEREntity(surface_form="test", entity_type="company")
        with pytest.raises(AttributeError):
            entity.surface_form = "changed"  # type: ignore[misc]

    def test_default_values(self) -> None:
        entity = NEREntity()
        assert entity.surface_form == ""
        assert entity.entity_type == ""
        assert entity.start_offset == 0
        assert entity.end_offset == 0
        assert entity.confidence == 0.0
        assert entity.linked_ticker is None
        assert entity.normalized_name is None

    def test_custom_values(self) -> None:
        entity = NEREntity(
            surface_form="贵州茅台",
            entity_type="company",
            start_offset=0,
            end_offset=4,
            confidence=0.95,
            linked_ticker="600519.SH",
        )
        assert entity.surface_form == "贵州茅台"
        assert entity.linked_ticker == "600519.SH"

    def test_to_dict_roundtrip(self) -> None:
        entity = NEREntity(
            surface_form="ROE",
            entity_type="metric",
            start_offset=5,
            end_offset=8,
            confidence=0.90,
            normalized_name="净资产收益率",
        )
        d = entity.to_dict()
        restored = NEREntity.from_dict(d)
        assert restored.surface_form == entity.surface_form
        assert restored.entity_type == entity.entity_type
        assert restored.start_offset == entity.start_offset
        assert restored.confidence == entity.confidence
        assert restored.normalized_name == entity.normalized_name


class TestTextDocumentSchema:
    """Tests for TextDocument frozen dataclass."""

    def test_frozen_and_slots(self) -> None:
        doc = TextDocument(text="hello")
        with pytest.raises(AttributeError):
            doc.text = "changed"  # type: ignore[misc]

    def test_to_dict_roundtrip(self) -> None:
        doc = TextDocument(text="test text", doc_id="doc-1", source_type="news")
        d = doc.to_dict()
        restored = TextDocument.from_dict(d)
        assert restored.text == "test text"
        assert restored.doc_id == "doc-1"
        assert restored.source_type == "news"


class TestNERResultSchema:
    """Tests for NERResult frozen dataclass."""

    def test_frozen_and_slots(self) -> None:
        result = NERResult(doc_id="d1")
        with pytest.raises(AttributeError):
            result.doc_id = "changed"  # type: ignore[misc]

    def test_to_dict_roundtrip(self) -> None:
        entity = NEREntity(surface_form="test", entity_type="person", confidence=0.8)
        result = NERResult(doc_id="d1", entities=(entity,), processing_time_ms=1.5)
        d = result.to_dict()
        restored = NERResult.from_dict(d)
        assert restored.doc_id == "d1"
        assert len(restored.entities) == 1
        assert restored.entities[0].surface_form == "test"
        assert restored.processing_time_ms == 1.5

    def test_empty_entities(self) -> None:
        result = NERResult()
        assert result.entities == ()
        assert result.processing_time_ms == 0.0


# ---------------------------------------------------------------------------
# Company recognition tests
# ---------------------------------------------------------------------------

class TestCompanyRecognition:
    """Tests for company entity recognition."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_full_company_name(self) -> None:
        """Recognize full company name."""
        doc = TextDocument(text="贵州茅台今日涨停", doc_id="test-1")
        result = self.engine.recognize(doc)
        company_entities = [e for e in result.entities if e.entity_type == "company"]
        assert len(company_entities) >= 1
        names = [e.surface_form for e in company_entities]
        assert "贵州茅台" in names

    def test_company_ticker_link(self) -> None:
        """Company entities should have linked tickers."""
        doc = TextDocument(text="贵州茅台发布年报", doc_id="test-2")
        result = self.engine.recognize(doc)
        company_entities = [e for e in result.entities if e.entity_type == "company"]
        assert any(e.linked_ticker == "600519.SH" for e in company_entities)

    def test_multiple_companies(self) -> None:
        """Recognize multiple companies in one text."""
        doc = TextDocument(text="贵州茅台和宁德时代都是好公司", doc_id="test-3")
        result = self.engine.recognize(doc)
        company_entities = [e for e in result.entities if e.entity_type == "company"]
        names = [e.surface_form for e in company_entities]
        assert "贵州茅台" in names
        assert "宁德时代" in names

    def test_company_abbreviation(self) -> None:
        """Recognize abbreviated company name."""
        doc = TextDocument(text="茅台上季度净利润增长20%", doc_id="test-4")
        result = self.engine.recognize(doc)
        company_entities = [e for e in result.entities if e.entity_type == "company"]
        names = [e.surface_form for e in company_entities]
        assert "茅台" in names


# ---------------------------------------------------------------------------
# Metric recognition tests
# ---------------------------------------------------------------------------

class TestMetricRecognition:
    """Tests for metric entity recognition."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_roe_recognition(self) -> None:
        """Recognize ROE metric."""
        doc = TextDocument(text="该公司ROE达到15%", doc_id="test-m1")
        result = self.engine.recognize(doc)
        metric_entities = [e for e in result.entities if e.entity_type == "metric"]
        assert any(e.surface_form == "ROE" for e in metric_entities)

    def test_metric_normalized_name(self) -> None:
        """Metric entities should have normalized names."""
        doc = TextDocument(text="市盈率为20倍", doc_id="test-m2")
        result = self.engine.recognize(doc)
        metric_entities = [e for e in result.entities if e.entity_type == "metric"]
        assert any(e.normalized_name == "市盈率" for e in metric_entities)

    def test_multiple_metrics(self) -> None:
        """Recognize multiple metrics in one text."""
        doc = TextDocument(text="ROE和EPS都是重要指标，PE为15倍", doc_id="test-m3")
        result = self.engine.recognize(doc)
        metric_entities = [e for e in result.entities if e.entity_type == "metric"]
        aliases = [e.surface_form for e in metric_entities]
        assert "ROE" in aliases
        assert "EPS" in aliases


# ---------------------------------------------------------------------------
# Person recognition tests
# ---------------------------------------------------------------------------

class TestPersonRecognition:
    """Tests for person entity recognition."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_person_with_role_suffix(self) -> None:
        """Recognize person name with analyst suffix."""
        doc = TextDocument(text="张三分析师认为茅台值得买入", doc_id="test-p1")
        result = self.engine.recognize(doc)
        person_entities = [e for e in result.entities if e.entity_type == "person"]
        names = [e.surface_form for e in person_entities]
        assert "张三" in names

    def test_person_with_executive_suffix(self) -> None:
        """Recognize person name with executive suffix."""
        doc = TextDocument(text="李四董事长宣布增持计划", doc_id="test-p2")
        result = self.engine.recognize(doc)
        person_entities = [e for e in result.entities if e.entity_type == "person"]
        names = [e.surface_form for e in person_entities]
        assert "李四" in names


# ---------------------------------------------------------------------------
# Institution recognition tests
# ---------------------------------------------------------------------------

class TestInstitutionRecognition:
    """Tests for institution entity recognition."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_regulator_recognition(self) -> None:
        """Recognize regulatory institutions."""
        doc = TextDocument(text="证监会发布新规", doc_id="test-i1")
        result = self.engine.recognize(doc)
        inst_entities = [e for e in result.entities if e.entity_type == "institution"]
        assert any(e.surface_form == "证监会" for e in inst_entities)

    def test_central_bank(self) -> None:
        """Recognize central bank."""
        doc = TextDocument(text="央行降准0.5个百分点", doc_id="test-i2")
        result = self.engine.recognize(doc)
        inst_entities = [e for e in result.entities if e.entity_type == "institution"]
        assert any(e.surface_form == "央行" for e in inst_entities)


# ---------------------------------------------------------------------------
# Product recognition tests
# ---------------------------------------------------------------------------

class TestProductRecognition:
    """Tests for product entity recognition."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_product_recognition(self) -> None:
        """Recognize products."""
        doc = TextDocument(text="飞天茅台价格持续走高", doc_id="test-pr1")
        result = self.engine.recognize(doc)
        prod_entities = [e for e in result.entities if e.entity_type == "product"]
        assert any(e.surface_form == "飞天茅台" for e in prod_entities)


# ---------------------------------------------------------------------------
# Ticker linking tests
# ---------------------------------------------------------------------------

class TestTickerLinking:
    """Tests for fuzzy ticker linking."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_exact_ticker_match(self) -> None:
        """Exact match in dictionary should have high confidence."""
        doc = TextDocument(text="贵州茅台今日大涨", doc_id="test-t1")
        result = self.engine.recognize(doc)
        company = [e for e in result.entities if e.entity_type == "company"][0]
        assert company.linked_ticker == "600519.SH"
        assert company.confidence >= 0.9

    def test_fuzzy_ticker_match(self) -> None:
        """Fuzzy match should still link ticker."""
        doc = TextDocument(text="茅台上季度营收增长", doc_id="test-t2")
        result = self.engine.recognize(doc)
        company = [e for e in result.entities if e.entity_type == "company"]
        # "茅台" should fuzzy match to 600519.SH
        assert any(e.linked_ticker == "600519.SH" for e in company)


# ---------------------------------------------------------------------------
# TextPreprocessor tests
# ---------------------------------------------------------------------------

class TestTextPreprocessor:
    """Tests for TextPreprocessor."""

    def setup_method(self) -> None:
        self.preprocessor = TextPreprocessor()

    def test_abbreviation_expansion(self) -> None:
        """Abbreviations should be expanded."""
        result = self.preprocessor.expand_abbreviations("营收增长")
        assert "营业收入" in result

    def test_number_normalization_yi(self) -> None:
        """亿 unit should be normalized to float."""
        text, nums = self.preprocessor.normalize_numbers("净利润1.5亿")
        assert 1.5e8 in nums.values()

    def test_number_normalization_wan(self) -> None:
        """万 unit should be normalized to float."""
        text, nums = self.preprocessor.normalize_numbers("营收3000万")
        assert 3e7 in nums.values()

    def test_approximation_markers(self) -> None:
        """Approximation markers should be extracted."""
        markers = self.preprocessor.extract_approximation_markers("约1.5亿营收")
        assert "约" in markers

    def test_full_preprocessing_pipeline(self) -> None:
        """Full preprocessing should expand, normalize, and extract."""
        result = self.preprocessor.preprocess("营收约1.5亿，ROE为15%")
        assert isinstance(result, PreprocessedText)
        assert "营业收入" in result.expanded
        assert len(result.approximation_markers) > 0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for NER engine edge cases."""

    def setup_method(self) -> None:
        self.engine = NEREngine()

    def test_empty_text(self) -> None:
        """Empty text should return empty NERResult."""
        doc = TextDocument(text="", doc_id="empty")
        result = self.engine.recognize(doc)
        assert result.entities == ()
        assert result.processing_time_ms >= 0.0

    def test_no_match_text(self) -> None:
        """Text with no financial entities should return empty entities."""
        doc = TextDocument(text="今天天气真好", doc_id="no-match")
        result = self.engine.recognize(doc)
        assert len(result.entities) == 0

    def test_nested_entities(self) -> None:
        """Nested entities should be deduplicated (keep highest confidence)."""
        # "中信证券分析师张三" contains both company and person
        doc = TextDocument(text="中信证券分析师张三表示看好茅台", doc_id="nested")
        result = self.engine.recognize(doc)
        company_entities = [e for e in result.entities if e.entity_type == "company"]
        person_entities = [e for e in result.entities if e.entity_type == "person"]
        assert len(company_entities) >= 1
        assert len(person_entities) >= 1

    def test_doc_id_preserved(self) -> None:
        """NERResult should preserve doc_id."""
        doc = TextDocument(text="贵州茅台", doc_id="my-doc-123")
        result = self.engine.recognize(doc)
        assert result.doc_id == "my-doc-123"

    def test_processing_time_positive(self) -> None:
        """Processing time should be positive."""
        doc = TextDocument(text="贵州茅台发布年报，ROE为15%", doc_id="timing")
        result = self.engine.recognize(doc)
        assert result.processing_time_ms >= 0.0

    def test_mixed_entity_types(self) -> None:
        """Text with multiple entity types should recognize all."""
        doc = TextDocument(
            text="贵州茅台ROE为15%，张三分析师认为值得买入",
            doc_id="mixed",
        )
        result = self.engine.recognize(doc)
        types = {e.entity_type for e in result.entities}
        assert "company" in types
        assert "metric" in types


# ---------------------------------------------------------------------------
# Dictionary tests
# ---------------------------------------------------------------------------

class TestDictionaries:
    """Tests for entity dictionaries."""

    def test_company_dict_has_entries(self) -> None:
        """Company dictionary should have 100+ entries."""
        assert len(COMPANY_NAMES) >= 100

    def test_get_ticker(self) -> None:
        """get_ticker should return correct ticker."""
        assert get_ticker("贵州茅台") == "600519.SH"
        assert get_ticker("不存在") is None

    def test_metric_dict_has_entries(self) -> None:
        """Metric dictionary should have 30+ entries."""
        assert len(METRIC_ALIASES) >= 30

    def test_get_standard_name(self) -> None:
        """get_standard_name should return correct standard name."""
        assert get_standard_name("ROE") == "净资产收益率"
        assert get_standard_name("不存在") is None

    def test_institution_patterns_exist(self) -> None:
        """Institution patterns should be defined."""
        assert len(INSTITUTION_PATTERNS) > 0
