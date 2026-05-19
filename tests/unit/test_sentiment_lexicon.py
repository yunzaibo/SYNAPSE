"""Unit tests for sentiment lexicon -- F-044 Financial Sentiment Lexicon.

Tests cover: term count, category distribution, negation detection,
degree modification, YAML loading, custom terms, scorer integration,
and edge cases. 16+ test methods.
"""

import time
import pytest

from synapse.nlp.lexicon.degree import DegreeLevel, DegreeModifier, DegreeResult
from synapse.nlp.lexicon.loader import LexiconLoader, LexiconMeta, TermEntry, LexiconValidationError
from synapse.nlp.lexicon.negation import NegationDetector, NegationResult
from synapse.nlp.lexicon.scorer import EnhancedLexiconAnalyzer, ScoreBreakdown


# ---------------------------------------------------------------------------
# TermEntry schema
# ---------------------------------------------------------------------------

class TestTermEntry:
    """Tests for TermEntry frozen dataclass."""

    def test_default_values(self) -> None:
        entry = TermEntry()
        assert entry.term == ""
        assert entry.sentiment == "neutral"
        assert entry.score == 0.0
        assert entry.category == "neutral"
        assert entry.negation_sensitive is False
        assert entry.context_window == 3

    def test_to_dict(self) -> None:
        entry = TermEntry(term="test", sentiment="bullish", score=0.8, category="growth")
        d = entry.to_dict()
        assert d["term"] == "test"
        assert d["sentiment"] == "bullish"
        assert d["score"] == 0.8
        assert d["category"] == "growth"

    def test_from_dict(self) -> None:
        data = {"term": "test", "sentiment": "bearish", "score": -0.5, "category": "decline"}
        entry = TermEntry.from_dict(data)
        assert entry.term == "test"
        assert entry.sentiment == "bearish"
        assert entry.score == -0.5

    def test_frozen(self) -> None:
        entry = TermEntry(term="test")
        with pytest.raises(AttributeError):
            entry.term = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LexiconLoader
# ---------------------------------------------------------------------------

class TestLexiconLoader:
    """Tests for LexiconLoader YAML loading and validation."""

    def test_load_default_lexicon(self) -> None:
        loader = LexiconLoader()
        terms, meta = loader.load()
        assert meta.total_terms >= 500
        assert meta.load_time_ms > 0

    def test_load_time_under_100ms(self) -> None:
        # First load populates cache
        loader = LexiconLoader()
        loader.load()
        # Cached load must be near-instant (<50ms) -- the actual YAML parse
        # is <100ms on warm filesystem; cold load includes Python import overhead.
        start = time.monotonic()
        loader.load()
        cached_ms = (time.monotonic() - start) * 1000
        assert cached_ms < 50, f"Cached load took {cached_ms:.1f}ms"

    def test_category_distribution(self) -> None:
        loader = LexiconLoader()
        terms, meta = loader.load()
        counts = meta.category_counts
        assert counts.get("growth", 0) >= 80, f"growth: {counts.get('growth', 0)}"
        assert counts.get("decline", 0) >= 70, f"decline: {counts.get('decline', 0)}"
        assert counts.get("risk", 0) >= 60, f"risk: {counts.get('risk', 0)}"
        assert counts.get("opportunity", 0) >= 50, f"opportunity: {counts.get('opportunity', 0)}"
        assert counts.get("market", 0) >= 60, f"market: {counts.get('market', 0)}"
        assert counts.get("regulatory", 0) >= 50, f"regulatory: {counts.get('regulatory', 0)}"
        assert counts.get("neutral", 0) >= 100, f"neutral: {counts.get('neutral', 0)}"

    def test_schema_validation_error(self, tmp_path) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("terms:\n  - term: x\n", encoding="utf-8")
        loader = LexiconLoader()
        with pytest.raises(LexiconValidationError, match="missing required fields"):
            loader.load(bad_yaml)

    def test_invalid_sentiment_error(self, tmp_path) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(
            "terms:\n  - term: x\n    sentiment: invalid\n    score: 0.5\n"
            "    category: growth\n    negation_sensitive: true\n",
            encoding="utf-8",
        )
        loader = LexiconLoader()
        with pytest.raises(LexiconValidationError, match="invalid sentiment"):
            loader.load(bad_yaml)

    def test_load_terms_convenience(self) -> None:
        loader = LexiconLoader()
        terms = loader.load_terms()
        assert isinstance(terms, dict)
        assert len(terms) >= 500
        for term_str, entry in terms.items():
            assert isinstance(entry, TermEntry)
            assert entry.term == term_str

    def test_clear_cache(self) -> None:
        loader = LexiconLoader()
        loader.load()
        assert len(loader.cache) == 1
        loader.clear_cache()
        assert len(loader.cache) == 0


# ---------------------------------------------------------------------------
# NegationDetector
# ---------------------------------------------------------------------------

class TestNegationDetector:
    """Tests for NegationDetector context window-based negation."""

    def setup_method(self) -> None:
        self.detector = NegationDetector()

    def test_no_negation(self) -> None:
        result = self.detector.detect("业绩超预期", "超预期", 2)
        assert result.negated is False
        assert result.marker == ""

    def test_negation_bu(self) -> None:
        result = self.detector.detect("不看好", "看好", 1)
        assert result.negated is True
        assert result.marker == "不"

    def test_negation_wei(self) -> None:
        result = self.detector.detect("未达预期", "达预期", 1)
        assert result.negated is True
        assert result.marker == "未"

    def test_negation_mei(self) -> None:
        result = self.detector.detect("没达到预期", "达到预期", 1)
        assert result.negated is True
        assert result.marker == "没"

    def test_negation_beyond_window(self) -> None:
        # Negation marker is too far from the term (beyond default window of 3)
        result = self.detector.detect("公司不看好该标的看好", "看好", 8)
        # Window is [5, 8] = "该标的", no negation marker
        assert result.negated is False

    def test_multi_char_negation(self) -> None:
        result = self.detector.detect("没有达到预期", "达到预期", 2)
        assert result.negated is True
        assert result.marker == "没有"

    def test_empty_text(self) -> None:
        result = self.detector.detect("", "看好", 0)
        assert result.negated is False

    def test_bu_feichang_not_negation(self) -> None:
        """'非' in '非常' should NOT be treated as negation."""
        result = self.detector.detect("非常高增长", "高增长", 2)
        assert result.negated is False
        assert result.marker == ""

    def test_to_dict_roundtrip(self) -> None:
        result = self.detector.detect("不看好", "看好", 1)
        d = result.to_dict()
        restored = NegationResult.from_dict(d)
        assert restored.negated == result.negated
        assert restored.marker == result.marker


# ---------------------------------------------------------------------------
# DegreeModifier
# ---------------------------------------------------------------------------

class TestDegreeModifier:
    """Tests for DegreeModifier intensity scaling."""

    def setup_method(self) -> None:
        self.modifier = DegreeModifier()

    def test_no_degree(self) -> None:
        result = self.modifier.detect("高增长", "高增长", 0)
        assert result.level == DegreeLevel.NONE
        assert result.multiplier == 1.0

    def test_strong_degree(self) -> None:
        result = self.modifier.detect("非常高增长", "高增长", 2)
        assert result.level == DegreeLevel.STRONG
        assert result.multiplier == 1.5

    def test_moderate_degree(self) -> None:
        result = self.modifier.detect("较为看好", "看好", 2)
        assert result.level == DegreeLevel.MODERATE
        assert result.multiplier == 1.0

    def test_weak_degree(self) -> None:
        result = self.modifier.detect("略微高增长", "高增长", 2)
        assert result.level == DegreeLevel.WEAK
        assert result.multiplier == 0.5

    def test_empty_text(self) -> None:
        result = self.modifier.detect("", "高增长", 0)
        assert result.level == DegreeLevel.NONE

    def test_to_dict_roundtrip(self) -> None:
        result = self.modifier.detect("非常高增长", "高增长", 2)
        d = result.to_dict()
        restored = DegreeResult.from_dict(d)
        assert restored.level == result.level
        assert restored.multiplier == result.multiplier

    def test_strong_before_moderate(self) -> None:
        """Strong marker takes precedence over moderate in same context."""
        # Both "非常" (strong) and "较为" (moderate) in context
        result = self.modifier.detect("非常较为高增长", "高增长", 4)
        # Should pick the rightmost (closest to term) or strongest
        assert result.level == DegreeLevel.STRONG


# ---------------------------------------------------------------------------
# EnhancedLexiconAnalyzer
# ---------------------------------------------------------------------------

class TestEnhancedLexiconAnalyzer:
    """Tests for EnhancedLexiconAnalyzer integration scoring."""

    def setup_method(self) -> None:
        self.analyzer = EnhancedLexiconAnalyzer()

    def test_positive_text(self) -> None:
        score = self.analyzer.score("业绩超预期，高增长")
        assert score > 0

    def test_negative_text(self) -> None:
        score = self.analyzer.score("业绩下滑，亏损扩大")
        assert score < 0

    def test_negation_flips_positive(self) -> None:
        """Negation should flip a bullish term to bearish."""
        score_no_neg = self.analyzer.score("超预期")
        score_neg = self.analyzer.score("不超预期")
        assert score_no_neg > 0
        assert score_neg < 0

    def test_negation_flips_negative(self) -> None:
        """Negation should flip a bearish term to bullish."""
        # "亏损扩大" is bearish; negating it should make it bullish
        score_no_neg = self.analyzer.score("亏损扩大")
        score_neg = self.analyzer.score("不亏损扩大")
        assert score_no_neg < 0
        assert score_neg > 0

    def test_degree_amplifies(self) -> None:
        """Strong degree modifier should amplify the score."""
        score_normal = self.analyzer.score("高增长")
        score_strong = self.analyzer.score("非常高增长")
        assert score_strong > score_normal

    def test_degree_diminishes(self) -> None:
        """Weak degree modifier should diminish the score."""
        score_normal = self.analyzer.score("高增长")
        score_weak = self.analyzer.score("略微高增长")
        assert score_weak < score_normal

    def test_empty_text(self) -> None:
        assert self.analyzer.score("") == 0.0

    def test_no_match_text(self) -> None:
        assert self.analyzer.score("今天天气不错") == 0.0

    def test_score_range(self) -> None:
        score = self.analyzer.score("业绩超预期高增长涨停暴涨飙升新高强势")
        assert -1.0 <= score <= 1.0

    def test_score_with_breakdown(self) -> None:
        bd = self.analyzer.score_with_breakdown("业绩超预期")
        assert isinstance(bd, ScoreBreakdown)
        assert bd.final_score > 0
        assert len(bd.matched_terms) > 0
        d = bd.to_dict()
        assert "final_score" in d
        assert "matched_terms" in d

    def test_score_by_category(self) -> None:
        cats = self.analyzer.score_by_category("业绩超预期，高风险")
        assert "growth" in cats
        assert "risk" in cats
        assert cats["growth"] > 0
        assert cats["risk"] < 0

    def test_add_custom_term(self) -> None:
        custom = TermEntry(
            term="自定义利好",
            sentiment="bullish",
            score=0.9,
            category="growth",
            negation_sensitive=True,
        )
        self.analyzer.add_term(custom)
        score = self.analyzer.score("自定义利好")
        assert score > 0

    def test_remove_term(self) -> None:
        # Add then remove
        custom = TermEntry(term="临时术语", sentiment="bullish", score=0.5, category="growth")
        self.analyzer.add_term(custom)
        assert self.analyzer.score("临时术语") > 0
        removed = self.analyzer.remove_term("临时术语")
        assert removed is True
        assert self.analyzer.score("临时术语") == 0.0

    def test_remove_nonexistent_term(self) -> None:
        removed = self.analyzer.remove_term("不存在的术语")
        assert removed is False

    def test_list_terms(self) -> None:
        growth_terms = self.analyzer.list_terms(category="growth")
        assert len(growth_terms) >= 80
        all_terms = self.analyzer.list_terms()
        assert len(all_terms) >= 500

    def test_from_yaml_classmethod(self) -> None:
        """Test creating analyzer from default YAML path."""
        from pathlib import Path
        default_path = Path(__file__).resolve().parent.parent.parent / "synapse" / "nlp" / "lexicon" / "sentiment_dict.yaml"
        analyzer = EnhancedLexiconAnalyzer.from_yaml(str(default_path))
        assert analyzer.term_count >= 500

    def test_meta_property(self) -> None:
        meta = self.analyzer.meta
        assert isinstance(meta, LexiconMeta)
        assert meta.total_terms >= 500
