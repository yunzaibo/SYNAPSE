"""PolicyUnderstander -- Structured extraction from Chinese regulatory documents.

Pipeline: Issuing body detection -> Document type classification ->
Effective date extraction -> Key change identification ->
Sector mapping -> Sentiment impact scoring.

Part of P4 Chinese Financial NLP Layer (F-040 Policy Document Understander).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from synapse.nlp.schemas import TextDocument
from synapse.nlp.policy_patterns import (
    classify_document_type,
    detect_issuing_body,
    extract_effective_date,
    extract_key_changes,
)
from synapse.nlp.sector_mapper import SectorMapper, SectorMatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PolicyResult frozen dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PolicyResult:
    """Structured result from policy document analysis.

    Attributes
    ----------
    issuing_body:
        Standardized issuing body identifier (PBOC, CSRC, State_Council, or unknown).
    document_type:
        Document type: monetary_policy, regulatory_rule, guidance, or enforcement.
    effective_date:
        ISO date string (YYYY-MM-DD) or None if not found.
    key_changes:
        Tuple of key regulatory change descriptions.
    affected_sectors:
        Tuple of affected sector names.
    sentiment_impact:
        Dict mapping sector name to sentiment label (bullish/bearish/neutral).
    """

    issuing_body: str = "unknown"
    document_type: str = "guidance"
    effective_date: Optional[str] = None
    key_changes: tuple[str, ...] = ()
    affected_sectors: tuple[str, ...] = ()
    sentiment_impact: dict[str, str] = field(default_factory=dict)
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "issuing_body": self.issuing_body,
            "document_type": self.document_type,
            "effective_date": self.effective_date,
            "key_changes": list(self.key_changes),
            "affected_sectors": list(self.affected_sectors),
            "sentiment_impact": dict(self.sentiment_impact),
            "processing_time_ms": self.processing_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PolicyResult:
        return cls(
            issuing_body=data.get("issuing_body", "unknown"),
            document_type=data.get("document_type", "guidance"),
            effective_date=data.get("effective_date"),
            key_changes=tuple(data.get("key_changes", [])),
            affected_sectors=tuple(data.get("affected_sectors", [])),
            sentiment_impact=data.get("sentiment_impact", {}),
            processing_time_ms=float(data.get("processing_time_ms", 0.0)),
        )


# ---------------------------------------------------------------------------
# Sentiment impact keywords (simple rule-based)
# ---------------------------------------------------------------------------

_BULLISH_KEYWORDS: frozenset[str] = frozenset({
    "下调", "降低", "放宽", "支持", "鼓励", "利好", "促进",
    "优化", "减免", "补贴", "激励", "便利",
})

_BEARISH_KEYWORDS: frozenset[str] = frozenset({
    "上调", "提高", "收紧", "限制", "禁止", "处罚", "整顿",
    "加强监管", "严查", "暂停", "取消",
})


def _estimate_sector_sentiment(text: str, sector: str, sector_keywords: tuple[str, ...]) -> str:
    """Estimate sentiment impact for a specific sector.

    Parameters
    ----------
    text:
        Full policy document text.
    sector:
        Sector name.
    sector_keywords:
        Keywords associated with this sector.

    Returns
    -------
    "bullish", "bearish", or "neutral".
    """
    # Extract sentences mentioning this sector
    sector_sentences: list[str] = []
    for sentence in text.replace("。", "\n").replace("；", "\n").replace("，", "\n").split("\n"):
        if any(kw in sentence for kw in sector_keywords):
            sector_sentences.append(sentence)

    if not sector_sentences:
        return "neutral"

    combined = "".join(sector_sentences)

    bullish_count = sum(1 for kw in _BULLISH_KEYWORDS if kw in combined)
    bearish_count = sum(1 for kw in _BEARISH_KEYWORDS if kw in combined)

    if bullish_count > bearish_count:
        return "bullish"
    if bearish_count > bullish_count:
        return "bearish"
    return "neutral"


# ---------------------------------------------------------------------------
# PolicyUnderstander
# ---------------------------------------------------------------------------

@dataclass
class PolicyUnderstander:
    """Chinese regulatory document understanding pipeline.

    Pipeline:
    1. Issuing body detection (PBOC/CSRC/State Council)
    2. Document type classification
    3. Effective date extraction
    4. Key regulatory change identification
    5. Sector mapping (8+ sectors)
    6. Sentiment impact per sector

    Usage::

        understander = PolicyUnderstander()
        result = understander.understand(TextDocument(text="中国人民银行决定..."))
        assert result.issuing_body == "PBOC"
    """

    sector_mapper: SectorMapper = field(default_factory=SectorMapper)

    def understand(self, doc: TextDocument) -> PolicyResult:
        """Analyze a policy document and extract structured metadata.

        Parameters
        ----------
        doc:
            Input TextDocument containing policy text.

        Returns
        -------
        PolicyResult with all extracted fields.
        """
        start = time.monotonic()

        if not doc.text:
            return PolicyResult(processing_time_ms=0.0)

        text = doc.text

        # Step 1: Detect issuing body
        issuing_match = detect_issuing_body(text)

        # Step 2: Classify document type
        doc_type = classify_document_type(text)

        # Step 3: Extract effective date
        eff_date = extract_effective_date(text)

        # Step 4: Extract key changes
        changes = extract_key_changes(text)

        # Step 5: Map to affected sectors
        sector_matches = self.sector_mapper.map_to_sectors(text)
        affected_sectors = tuple(m.sector for m in sector_matches)

        # Step 6: Estimate sentiment impact per sector
        sentiment_impact: dict[str, str] = {}
        for match in sector_matches:
            # Get sector keywords from the mapper's dictionary
            from synapse.nlp.sector_mapper import SECTOR_KEYWORDS
            sector_kws = SECTOR_KEYWORDS.get(match.sector, ())
            sentiment_impact[match.sector] = _estimate_sector_sentiment(
                text, match.sector, sector_kws
            )

        elapsed_ms = (time.monotonic() - start) * 1000

        return PolicyResult(
            issuing_body=issuing_match.body,
            document_type=doc_type,
            effective_date=eff_date,
            key_changes=changes,
            affected_sectors=affected_sectors,
            sentiment_impact=sentiment_impact,
            processing_time_ms=round(elapsed_ms, 2),
        )
