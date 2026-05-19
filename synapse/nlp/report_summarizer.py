"""ReportSummarizer -- Chinese analyst research report summarization.

Extracts key viewpoints, investment theses, and structured data from
Chinese analyst research reports. Pipeline:
1. TextPreprocessor -- abbreviation expansion and normalization
2. NEREngine -- analyst/institution entity recognition
3. Structure parsing -- title, sections, rating, target price
4. Thesis summary generation -- extractive summarization from conclusion
5. Key points extraction -- bullet/numbered list items
6. Risk factor identification -- risk section extraction

Part of P4 Chinese Financial NLP Layer (F-038).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from synapse.nlp.ner_engine import NEREngine
from synapse.nlp.report_patterns import (
    ALL_AUTHOR_PATTERNS,
    ALL_INSTITUTION_PATTERNS,
    ALL_RATING_PATTERNS,
    ALL_TARGET_PRICE_PATTERNS,
    ALL_TITLE_PATTERNS,
    BULLET_PATTERNS,
    RATING_KEYWORDS,
    RISK_SENTENCE_PATTERN,
    SECTION_MARKERS,
    ReportRating,
)
from synapse.nlp.schemas import TextDocument

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Maximum thesis summary length (in Chinese characters, ~50 words)
# ---------------------------------------------------------------------------

_MAX_THESIS_LENGTH: int = 200
_MAX_KEY_POINTS: int = 5
_MAX_RISK_FACTORS: int = 5


# ---------------------------------------------------------------------------
# ResearchReportResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ResearchReportResult:
    """Structured output from research report summarization.

    Attributes
    ----------
    report_title:
        Detected report title (e.g. "贵州茅台深度研究报告").
    analyst_name:
        Author / analyst name extracted via NER.
    institution:
        Brokerage or research institution name.
    rating:
        Investment rating as a ReportRating enum value. None if not detected.
    target_price:
        Target price in CNY. None if not present.
    thesis_summary:
        Concise 1-3 sentence investment thesis (within ~50 words).
    key_points:
        Tuple of key investment points (3-5 items).
    risk_factors:
        Tuple of identified risk factors.
    """

    report_title: str = ""
    analyst_name: str = ""
    institution: str = ""
    rating: Optional[ReportRating] = None
    target_price: Optional[float] = None
    thesis_summary: str = ""
    key_points: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "report_title": self.report_title,
            "analyst_name": self.analyst_name,
            "institution": self.institution,
            "rating": self.rating.value if self.rating else None,
            "target_price": self.target_price,
            "thesis_summary": self.thesis_summary,
            "key_points": list(self.key_points),
            "risk_factors": list(self.risk_factors),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResearchReportResult:
        """Deserialize from dictionary."""
        rating_raw = data.get("rating")
        rating = ReportRating(rating_raw) if rating_raw else None
        return cls(
            report_title=data.get("report_title", ""),
            analyst_name=data.get("analyst_name", ""),
            institution=data.get("institution", ""),
            rating=rating,
            target_price=(
                float(data["target_price"])
                if data.get("target_price") is not None
                else None
            ),
            thesis_summary=data.get("thesis_summary", ""),
            key_points=tuple(data.get("key_points", [])),
            risk_factors=tuple(data.get("risk_factors", [])),
        )


# ---------------------------------------------------------------------------
# ReportSummarizer
# ---------------------------------------------------------------------------

@dataclass
class ReportSummarizer:
    """Chinese analyst research report summarizer.

    Extracts structured data from research reports including rating,
    target price, thesis summary, key points, and risk factors.

    Usage::

        summarizer = ReportSummarizer()
        result = summarizer.summarize(doc)
        print(result.rating)           # ReportRating.BUY
        print(result.target_price)     # 50.0

    Attributes
    ----------
    ner_engine:
        NEREngine for analyst/institution entity recognition.
    """

    ner_engine: NEREngine = field(default_factory=NEREngine)

    def summarize(self, doc: TextDocument) -> ResearchReportResult:
        """Summarize a research report document.

        Parameters
        ----------
        doc:
            Input TextDocument with research report text.

        Returns
        -------
        ResearchReportResult with extracted fields.
        """
        start = time.monotonic()

        if not doc.text:
            return ResearchReportResult()

        text = doc.text

        # Step 1: Extract report title
        title = self._extract_title(text)

        # Step 2: Extract analyst and institution via NER
        analyst_name, institution = self._extract_analyst_and_institution(text, doc)

        # Step 3: Extract rating
        rating = self._extract_rating(text)

        # Step 4: Extract target price
        target_price = self._extract_target_price(text)

        # Step 5: Generate thesis summary
        thesis_summary = self._extract_thesis_summary(text)

        # Step 6: Extract key points
        key_points = self._extract_key_points(text)

        # Step 7: Identify risk factors
        risk_factors = self._extract_risk_factors(text)

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "Report summarized in %.1f ms: title=%r, rating=%s, price=%s",
            elapsed_ms, title, rating, target_price,
        )

        return ResearchReportResult(
            report_title=title,
            analyst_name=analyst_name,
            institution=institution,
            rating=rating,
            target_price=target_price,
            thesis_summary=thesis_summary,
            key_points=key_points,
            risk_factors=risk_factors,
        )

    # ------------------------------------------------------------------
    # Title extraction
    # ------------------------------------------------------------------

    def _extract_title(self, text: str) -> str:
        """Extract report title from text using title patterns."""
        best_title = ""
        best_priority = -1

        for pattern in ALL_TITLE_PATTERNS:
            match = pattern.pattern.search(text[:500])  # title in first 500 chars
            if match and pattern.priority > best_priority:
                # Use the full match as the title
                candidate = match.group(0).strip()
                if len(candidate) >= 4:
                    best_title = candidate
                    best_priority = pattern.priority

        return best_title

    # ------------------------------------------------------------------
    # Analyst / institution extraction
    # ------------------------------------------------------------------

    def _extract_analyst_and_institution(
        self, text: str, doc: TextDocument
    ) -> tuple[str, str]:
        """Extract analyst name and institution from text.

        Uses regex patterns first, then falls back to NER engine
        for entity recognition.
        """
        analyst_name = ""
        institution = ""

        # Try analyst pattern matching
        for pattern in ALL_AUTHOR_PATTERNS:
            match = pattern.pattern.search(text[:1000])
            if match:
                analyst_name = match.group(1).strip()
                break

        # Try institution pattern matching
        for pattern in ALL_INSTITUTION_PATTERNS:
            match = pattern.pattern.search(text[:1000])
            if match:
                institution = match.group(1).strip()
                break

        # Fallback to NER if regex didn't find them
        if not analyst_name or not institution:
            ner_result = self.ner_engine.recognize(doc)
            for entity in ner_result.entities:
                if not analyst_name and entity.entity_type == "person":
                    analyst_name = entity.surface_form
                if not institution and entity.entity_type == "institution":
                    institution = entity.surface_form

        return analyst_name, institution

    # ------------------------------------------------------------------
    # Rating extraction
    # ------------------------------------------------------------------

    def _extract_rating(self, text: str) -> Optional[ReportRating]:
        """Extract investment rating from text using rating patterns."""
        # Try explicit rating patterns first
        for pattern in ALL_RATING_PATTERNS:
            match = pattern.pattern.search(text)
            if match:
                rating_text = match.group(1).strip()
                # Look up in rating keywords
                rating = RATING_KEYWORDS.get(rating_text)
                if rating is not None:
                    return rating

        # Fallback: scan text for any rating keyword
        for keyword, rating in RATING_KEYWORDS.items():
            if keyword in text:
                return rating

        return None

    # ------------------------------------------------------------------
    # Target price extraction
    # ------------------------------------------------------------------

    def _extract_target_price(self, text: str) -> Optional[float]:
        """Extract target price from text using price patterns."""
        for pattern in ALL_TARGET_PRICE_PATTERNS:
            match = pattern.pattern.search(text)
            if match:
                groups = match.groups()
                # Handle range pattern (group 1 = low, group 2 = high)
                if len(groups) >= 2 and groups[1]:
                    try:
                        low = float(groups[0].replace(",", ""))
                        high = float(groups[1].replace(",", ""))
                        return (low + high) / 2.0
                    except (ValueError, TypeError):
                        pass
                # Standard single price
                try:
                    price_str = groups[0].replace(",", "")
                    return float(price_str)
                except (ValueError, TypeError):
                    pass

        # Fallback: look for price pattern in full text
        price_match = re.search(
            r"(?:目标价|目标价格|目标位)[：:\s]*([\d,.]+)", text
        )
        if price_match:
            try:
                return float(price_match.group(1).replace(",", ""))
            except (ValueError, TypeError):
                pass

        return None

    # ------------------------------------------------------------------
    # Thesis summary extraction
    # ------------------------------------------------------------------

    def _extract_thesis_summary(self, text: str) -> str:
        """Extract thesis summary from conclusion section.

        Uses extractive summarization: finds the conclusion section,
        then takes the first 1-3 sentences.
        """
        conclusion_text = self._find_section_text(text, "conclusion")

        if not conclusion_text:
            # Try to find a general summary area
            conclusion_text = self._find_section_text(text, "key_points")

        if not conclusion_text:
            return ""

        # Split into sentences and take first 1-3
        sentences = self._split_sentences(conclusion_text)
        if not sentences:
            return ""

        # Build summary within word limit
        summary_parts: list[str] = []
        total_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if total_length + len(sentence) > _MAX_THESIS_LENGTH:
                break
            summary_parts.append(sentence)
            total_length += len(sentence)
            if len(summary_parts) >= 3:
                break

        return "".join(summary_parts)

    # ------------------------------------------------------------------
    # Key points extraction
    # ------------------------------------------------------------------

    def _extract_key_points(self, text: str) -> tuple[str, ...]:
        """Extract key investment points from bullet/numbered lists."""
        points: list[str] = []

        # First try to find the key_points section
        section_text = self._find_section_text(text, "key_points")
        if not section_text:
            section_text = self._find_section_text(text, "investment_highlights")

        if section_text:
            # Extract from bullet patterns
            for bullet_pattern in BULLET_PATTERNS:
                for match in bullet_pattern.finditer(section_text):
                    point = match.group(1).strip()
                    if len(point) >= 5 and len(points) < _MAX_KEY_POINTS:
                        points.append(point)

            # If no bullets found, split by newlines as fallback
            if not points:
                lines = section_text.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if len(line) >= 5 and len(points) < _MAX_KEY_POINTS:
                        points.append(line)

        # Fallback: scan full text for bullet patterns
        if not points:
            for bullet_pattern in BULLET_PATTERNS:
                for match in bullet_pattern.finditer(text):
                    point = match.group(1).strip()
                    if len(point) >= 5 and len(points) < _MAX_KEY_POINTS:
                        if point not in points:
                            points.append(point)

        return tuple(points)

    # ------------------------------------------------------------------
    # Risk factor extraction
    # ------------------------------------------------------------------

    def _extract_risk_factors(self, text: str) -> tuple[str, ...]:
        """Extract risk factors from risk section."""
        risks: list[str] = []

        # Find the risk section
        risk_text = self._find_section_text(text, "risks")

        if risk_text:
            # Extract sentences that mention risk keywords
            sentences = self._split_sentences(risk_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) >= 5 and len(risks) < _MAX_RISK_FACTORS:
                    risks.append(sentence)

            # Fallback: use bullet patterns
            if not risks:
                for bullet_pattern in BULLET_PATTERNS:
                    for match in bullet_pattern.finditer(risk_text):
                        risk = match.group(1).strip()
                        if len(risk) >= 5 and len(risks) < _MAX_RISK_FACTORS:
                            risks.append(risk)

        # Fallback: scan full text for risk sentences
        if not risks:
            for match in RISK_SENTENCE_PATTERN.finditer(text):
                risk = match.group(0).strip()
                if len(risk) >= 5 and len(risks) < _MAX_RISK_FACTORS:
                    if risk not in risks:
                        risks.append(risk)

        return tuple(risks)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_section_text(text: str, section_name: str) -> str:
        """Find text content of a named section.

        Searches for the section marker at line boundaries, then extracts
        text until the next section marker or end of text.

        Parameters
        ----------
        text:
            Full report text.
        section_name:
            Section key in SECTION_MARKERS (e.g. "conclusion", "risks").

        Returns
        -------
        Text content of the section, or empty string if not found.
        """
        marker = SECTION_MARKERS.get(section_name)
        if marker is None:
            return ""

        # Find the marker, but only at line boundaries (start of text or after \n)
        match = None
        for m in marker.pattern.finditer(text):
            pos = m.start()
            if pos == 0 or text[pos - 1] == "\n":
                match = m
                break

        if not match:
            return ""

        start = match.end()

        # Find the next section marker (at line boundaries) to determine section end
        end = len(text)
        for other_name, other_marker in SECTION_MARKERS.items():
            if other_name == section_name:
                continue
            for other_match in other_marker.pattern.finditer(text[start:]):
                other_pos = start + other_match.start()
                abs_pos = other_pos
                if abs_pos == 0 or text[abs_pos - 1] == "\n":
                    if other_pos < end:
                        end = other_pos
                    break

        return text[start:end].strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split Chinese text into sentences.

        Uses Chinese punctuation (。！？) as delimiters.
        """
        parts = re.split(r"[。！？]+", text)
        return [p.strip() for p in parts if p.strip()]
