"""AnnouncementParser -- Structured extraction pipeline for Chinese financial announcements.

Parses earnings reports, prospectuses, and board resolutions into structured data.
Uses TextPreprocessor for abbreviation expansion and regex-based metric extraction.

Part of P4 Chinese Financial NLP Layer (F-037).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from synapse.nlp.schemas import NEREntity, TextDocument
from synapse.nlp.text_preprocessor import (
    TextPreprocessor,
    _scale_factor,
    _NUMBER_PATTERN,
)
from synapse.nlp.patterns.financial_patterns import (
    METRIC_PATTERNS,
    ALL_PATTERNS,
    NumberPattern,
    detect_period,
    extract_approximation_markers,
)
from synapse.nlp.ner_engine import NEREngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Number extraction helper
# ---------------------------------------------------------------------------


def _extract_number(text: str) -> Optional[float]:
    """Extract the first numeric value from text.

    Handles Chinese units (亿/万/etc) and comma-separated numbers.
    """
    import re as _re

    # Try Chinese unit pattern first: number + 亿/万/etc
    m = _NUMBER_PATTERN.search(text)
    if m:
        num_str, unit = m.group(1), m.group(2)
        return float(num_str.replace(",", "")) * _scale_factor(unit)

    # Try comma-separated number with optional unit
    m_comma = _re.search(r"([+-]?\d[\d,]*(?:\.\d+)?)\s*(万亿|亿|千万|百万|万|千|百)?", text)
    if m_comma:
        num_str = m_comma.group(1).replace(",", "")
        unit = m_comma.group(2) or ""
        return float(num_str) * _scale_factor(unit)

    # Try plain number
    m_plain = _re.search(r"[+-]?\d+(?:\.\d+)?", text)
    if m_plain:
        return float(m_plain.group(0))

    return None


# ---------------------------------------------------------------------------
# PeriodInfo frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PeriodInfo:
    """Reporting period information extracted from announcement.

    Attributes
    ----------
    year:
        Reporting year (e.g. "2024").
    period_type:
        Period type: "Q1", "Q2", "Q3", "Q4", "annual", "semi_annual".
    period_label:
        Human-readable label (e.g. "2024 Q3", "2024 annual").
    """

    year: str = ""
    period_type: str = ""
    period_label: str = ""

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "period_type": self.period_type,
            "period_label": self.period_label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PeriodInfo:
        return cls(
            year=data.get("year", ""),
            period_type=data.get("period_type", ""),
            period_label=data.get("period_label", ""),
        )


# ---------------------------------------------------------------------------
# FinancialMetric frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinancialMetric:
    """A single extracted financial metric.

    Attributes
    ----------
    name:
        Standard metric name (e.g. "revenue", "net_profit").
    value:
        Extracted numeric value (in base unit, e.g. yuan).
    raw_text:
        Original text span from which the value was extracted.
    confidence:
        Extraction confidence in [0.0, 1.0].
    approximation:
        Approximation marker if present (e.g. "约", "超"), else None.
    """

    name: str = ""
    value: Optional[float] = None
    raw_text: str = ""
    confidence: float = 0.0
    approximation: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "approximation": self.approximation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FinancialMetric:
        return cls(
            name=data.get("name", ""),
            value=data.get("value"),
            raw_text=data.get("raw_text", ""),
            confidence=float(data.get("confidence", 0.0)),
            approximation=data.get("approximation"),
        )


# ---------------------------------------------------------------------------
# AnnouncementResult frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnnouncementResult:
    """Structured result from parsing a financial announcement.

    Attributes
    ----------
    metrics:
        Extracted financial metrics (revenue, net_profit, eps, roe, etc.).
    period_info:
        Detected reporting period (Q1/Q2/Q3/Q4/annual).
    growth_highlights:
        Key growth highlights mentioned in the text.
    risk_factors:
        Risk factors mentioned in the text.
    entities:
        NER-extracted entities (company, auditor, personnel).
    approximation_markers:
        Approximation markers found (约/超/近/etc).
    confidence:
        Overall extraction confidence in [0.0, 1.0].
    processing_time_ms:
        Time taken to process in milliseconds.
    """

    metrics: tuple[FinancialMetric, ...] = ()
    period_info: Optional[PeriodInfo] = None
    growth_highlights: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    entities: tuple[NEREntity, ...] = ()
    approximation_markers: tuple[str, ...] = ()
    confidence: float = 0.0
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "period_info": self.period_info.to_dict() if self.period_info else None,
            "growth_highlights": list(self.growth_highlights),
            "risk_factors": list(self.risk_factors),
            "entities": [e.to_dict() for e in self.entities],
            "approximation_markers": list(self.approximation_markers),
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AnnouncementResult:
        metrics = tuple(
            FinancialMetric.from_dict(m) for m in data.get("metrics", [])
        )
        period_data = data.get("period_info")
        period_info = PeriodInfo.from_dict(period_data) if period_data else None
        entities = tuple(
            NEREntity.from_dict(e) for e in data.get("entities", [])
        )
        return cls(
            metrics=metrics,
            period_info=period_info,
            growth_highlights=tuple(data.get("growth_highlights", [])),
            risk_factors=tuple(data.get("risk_factors", [])),
            entities=entities,
            approximation_markers=tuple(data.get("approximation_markers", [])),
            confidence=float(data.get("confidence", 0.0)),
            processing_time_ms=float(data.get("processing_time_ms", 0.0)),
        )


# ---------------------------------------------------------------------------
# Growth / risk sentence extraction helpers
# ---------------------------------------------------------------------------

_GROWTH_KEYWORDS = (
    "增长", "提升", "上升", "创新高", "翻倍", "大幅",
    "显著", "突破", "超预期", "回暖", "加速", "扩张",
)

_RISK_KEYWORDS = (
    "风险", "下降", "亏损", "下滑", "减少", "不利",
    "不确定", "承压", "萎缩", "恶化", "警示", "警惕",
)


def _extract_sentences_by_keywords(
    text: str, keywords: tuple[str, ...], max_sentences: int = 5
) -> list[str]:
    """Extract sentences containing any of the given keywords."""
    # Split by common sentence delimiters in Chinese text
    sentences = re.split(r"[。；\n]", text)
    matched: list[str] = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if any(kw in s for kw in keywords):
            matched.append(s)
            if len(matched) >= max_sentences:
                break
    return matched


# ---------------------------------------------------------------------------
# AnnouncementParser
# ---------------------------------------------------------------------------


class AnnouncementParser:
    """Structured extraction pipeline for Chinese financial announcements.

    Pipeline stages:
    1. TextPreprocessor.expand_abbreviations
    2. Regex metric extraction (20+ patterns)
    3. Period detection (Q1/Q2/Q3/Q4/annual)
    4. NER entity extraction (company/auditor/personnel)
    5. Approximation marker preservation
    6. Confidence scoring
    """

    def __init__(
        self,
        preprocessor: Optional[TextPreprocessor] = None,
        ner_engine: Optional[NEREngine] = None,
    ) -> None:
        self._preprocessor = preprocessor or TextPreprocessor()
        self._ner_engine = ner_engine or NEREngine(preprocessor=self._preprocessor)

    def parse(self, doc: TextDocument) -> AnnouncementResult:
        """Parse a financial announcement document into structured data.

        Parameters
        ----------
        doc:
            Input TextDocument with Chinese financial text.

        Returns
        -------
        AnnouncementResult with extracted metrics, period, entities, etc.
        """
        start_time = time.monotonic()

        if not doc.text:
            return AnnouncementResult(processing_time_ms=0.0)

        # Stage 1: Preprocess text (abbreviation expansion + number normalization)
        preprocessed = self._preprocessor.preprocess(doc.text)
        expanded_text = preprocessed.expanded

        # Stage 2: Extract financial metrics via regex patterns
        metrics = self._extract_metrics(doc.text, expanded_text)

        # Stage 3: Detect reporting period
        period_info = self._detect_period(doc.text)

        # Stage 4: Extract NER entities
        ner_result = self._ner_engine.recognize(doc)
        entities = ner_result.entities

        # Stage 5: Collect approximation markers
        approx_markers = tuple(preprocessed.approximation_markers)

        # Stage 6: Extract growth highlights and risk factors
        growth_highlights = tuple(
            _extract_sentences_by_keywords(doc.text, _GROWTH_KEYWORDS)
        )
        risk_factors = tuple(
            _extract_sentences_by_keywords(doc.text, _RISK_KEYWORDS)
        )

        # Stage 7: Compute confidence score
        confidence = self._compute_confidence(metrics, period_info, entities)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return AnnouncementResult(
            metrics=tuple(metrics),
            period_info=period_info,
            growth_highlights=growth_highlights,
            risk_factors=risk_factors,
            entities=entities,
            approximation_markers=approx_markers,
            confidence=confidence,
            processing_time_ms=round(elapsed_ms, 2),
        )

    # ------------------------------------------------------------------
    # Metric extraction
    # ------------------------------------------------------------------

    def _extract_metrics(
        self, original: str, expanded: str
    ) -> list[FinancialMetric]:
        """Extract financial metrics from text using regex patterns.

        Searches both original and expanded text, keeping the first match
        per metric name with highest confidence.
        """
        metrics_map: dict[str, FinancialMetric] = {}

        for pattern in ALL_PATTERNS:
            # Search expanded text first (abbreviations resolved), fallback to original
            expanded_match = pattern.pattern.search(expanded)
            original_match = pattern.pattern.search(original)

            match = expanded_match or original_match
            if not match:
                continue

            matched_text = match.group(0)
            value = _extract_number(matched_text)

            # Detect approximation marker in the matched text
            approx = self._detect_approx_in_span(matched_text)

            # Confidence: higher for expanded text matches
            conf = 0.85 if expanded_match is not None else 0.80

            metric = FinancialMetric(
                name=pattern.metric_name,
                value=value,
                raw_text=matched_text,
                confidence=conf,
                approximation=approx,
            )

            # Keep first match per metric name (earliest pattern wins)
            if pattern.metric_name not in metrics_map:
                metrics_map[pattern.metric_name] = metric

        return list(metrics_map.values())

    @staticmethod
    def _detect_approx_in_span(text: str) -> Optional[str]:
        """Detect approximation marker within a text span."""
        # Check from longest markers first to avoid partial matches
        for marker in ("超过", "不足", "接近", "大概", "估计", "预计", "左右", "约", "超", "近", "逾"):
            if marker in text:
                return marker
        return None

    # ------------------------------------------------------------------
    # Period detection
    # ------------------------------------------------------------------

    def _detect_period(self, text: str) -> Optional[PeriodInfo]:
        """Detect reporting period from text."""
        result = detect_period(text)
        if not result:
            return None

        year = result["year"]
        ptype = result["period_type"]
        label_map = {
            "annual": f"{year} annual",
            "Q1": f"{year} Q1",
            "Q2": f"{year} Q2",
            "Q3": f"{year} Q3",
            "Q4": f"{year} Q4",
            "semi_annual": f"{year} semi-annual",
        }
        return PeriodInfo(
            year=year,
            period_type=ptype,
            period_label=label_map.get(ptype, f"{year} {ptype}"),
        )

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        metrics: list[FinancialMetric],
        period_info: Optional[PeriodInfo],
        entities: tuple[NEREntity, ...],
    ) -> float:
        """Compute overall extraction confidence.

        Scoring:
        - 0.3 base for having text
        - Up to 0.3 for metrics found (0.06 per metric, max 5)
        - 0.2 for period detected
        - 0.2 for entities found
        """
        score = 0.0

        # Metrics contribution (up to 0.3)
        metric_count = len(metrics)
        score += min(metric_count * 0.06, 0.3)

        # Period detection contribution (0.2)
        if period_info is not None:
            score += 0.2

        # Entity contribution (0.2)
        if entities:
            score += min(len(entities) * 0.05, 0.2)

        return min(score, 1.0)
