"""NEREngine -- Chinese financial Named Entity Recognition engine.

Dictionary-based NER with fuzzy ticker linking. Recognizes 5 entity types:
company, person, product, institution, metric.

Part of P4 Chinese Financial NLP Layer (F-041).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from synapse.nlp.schemas import NEREntity, NERResult, TextDocument
from synapse.nlp.text_preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fuzzy matching threshold
# ---------------------------------------------------------------------------

FUZZY_MATCH_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# NEREngine
# ---------------------------------------------------------------------------

@dataclass
class NEREngine:
    """Dictionary-based Chinese financial NER engine.

    Chains five recognizers:
    1. Company name dictionary lookup
    2. Metric dictionary lookup
    3. Person name pattern matching
    4. Institution pattern matching
    5. Product pattern matching

    After recognition, links company entities to stock tickers via fuzzy matching.
    """

    preprocessor: TextPreprocessor = field(default_factory=TextPreprocessor)

    def recognize(self, doc: TextDocument) -> NERResult:
        """Recognize named entities in a text document.

        Parameters
        ----------
        doc:
            Input TextDocument with Chinese financial text.

        Returns
        -------
        NERResult with all recognized entities.
        """
        start_time = time.monotonic()

        if not doc.text:
            return NERResult(doc_id=doc.doc_id, entities=(), processing_time_ms=0.0)

        text = doc.text
        entities: list[NEREntity] = []

        # Step 1: Preprocess (abbreviation expansion for better matching)
        preprocessed = self.preprocessor.preprocess(text)

        # Step 2: Run recognizers (on original text for correct offsets)
        entities.extend(self._recognize_companies(text))
        entities.extend(self._recognize_metrics(text))
        entities.extend(self._recognize_persons(text))
        entities.extend(self._recognize_institutions(text))
        entities.extend(self._recognize_products(text))

        # Step 3: Deduplicate overlapping spans (keep highest confidence)
        entities = self._deduplicate_entities(entities)

        # Step 4: Link company entities to tickers via fuzzy matching
        entities = self._link_tickers(entities)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return NERResult(
            doc_id=doc.doc_id,
            entities=tuple(entities),
            processing_time_ms=round(elapsed_ms, 2),
        )

    # ------------------------------------------------------------------
    # Company recognizer
    # ------------------------------------------------------------------

    def _recognize_companies(self, text: str) -> list[NEREntity]:
        """Recognize company names using dictionary lookup.

        Searches for longest match first to avoid partial matches.
        """
        from synapse.nlp.dict.company_dict import COMPANY_NAMES, get_ticker

        entities: list[NEREntity] = []
        # Sort by name length descending for longest-match-first
        sorted_names = sorted(COMPANY_NAMES.keys(), key=len, reverse=True)

        for name in sorted_names:
            start = 0
            while True:
                idx = text.find(name, start)
                if idx == -1:
                    break
                end = idx + len(name)

                # Check if this span overlaps with an already-found entity
                overlaps = False
                for existing in entities:
                    if self._spans_overlap(idx, end, existing.start_offset, existing.end_offset):
                        overlaps = True
                        break

                if not overlaps:
                    ticker = get_ticker(name)
                    entities.append(
                        NEREntity(
                            surface_form=name,
                            entity_type="company",
                            start_offset=idx,
                            end_offset=end,
                            confidence=0.95,
                            linked_ticker=ticker,
                            normalized_name=None,
                        )
                    )
                start = idx + 1

        return entities

    # ------------------------------------------------------------------
    # Metric recognizer
    # ------------------------------------------------------------------

    def _recognize_metrics(self, text: str) -> list[NEREntity]:
        """Recognize financial metrics using dictionary lookup."""
        from synapse.nlp.dict.metric_dict import METRIC_ALIASES, get_standard_name

        entities: list[NEREntity] = []
        # Sort by alias length descending
        sorted_aliases = sorted(METRIC_ALIASES.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            start = 0
            while True:
                idx = text.find(alias, start)
                if idx == -1:
                    break
                end = idx + len(alias)

                overlaps = False
                for existing in entities:
                    if self._spans_overlap(idx, end, existing.start_offset, existing.end_offset):
                        overlaps = True
                        break

                if not overlaps:
                    standard_name = get_standard_name(alias)
                    entities.append(
                        NEREntity(
                            surface_form=alias,
                            entity_type="metric",
                            start_offset=idx,
                            end_offset=end,
                            confidence=0.90,
                            linked_ticker=None,
                            normalized_name=standard_name,
                        )
                    )
                start = idx + 1

        return entities

    # ------------------------------------------------------------------
    # Person recognizer
    # ------------------------------------------------------------------

    def _recognize_persons(self, text: str) -> list[NEREntity]:
        """Recognize person names using suffix-based pattern matching."""
        from synapse.nlp.dict.person_patterns import (
            has_person_suffix,
            find_generic_persons,
        )

        entities: list[NEREntity] = []

        # Role-based matching (higher confidence)
        for name, start, end in has_person_suffix(text):
            entities.append(
                NEREntity(
                    surface_form=name,
                    entity_type="person",
                    start_offset=start,
                    end_offset=end,
                    confidence=0.85,
                    linked_ticker=None,
                    normalized_name=None,
                )
            )

        # Generic context-based matching (lower confidence)
        for name, start, end in find_generic_persons(text):
            # Only add if not already found by role-based matching
            overlaps = False
            for existing in entities:
                if self._spans_overlap(start, end, existing.start_offset, existing.end_offset):
                    overlaps = True
                    break
            if not overlaps:
                entities.append(
                    NEREntity(
                        surface_form=name,
                        entity_type="person",
                        start_offset=start,
                        end_offset=end,
                        confidence=0.70,
                        linked_ticker=None,
                        normalized_name=None,
                    )
                )

        return entities

    # ------------------------------------------------------------------
    # Institution recognizer
    # ------------------------------------------------------------------

    def _recognize_institutions(self, text: str) -> list[NEREntity]:
        """Recognize institutions using regex pattern matching."""
        from synapse.nlp.dict.person_patterns import INSTITUTION_PATTERNS

        entities: list[NEREntity] = []
        for pattern in INSTITUTION_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                surface = match.group(0)

                overlaps = False
                for existing in entities:
                    if self._spans_overlap(start, end, existing.start_offset, existing.end_offset):
                        overlaps = True
                        break

                if not overlaps:
                    entities.append(
                        NEREntity(
                            surface_form=surface,
                            entity_type="institution",
                            start_offset=start,
                            end_offset=end,
                            confidence=0.92,
                            linked_ticker=None,
                            normalized_name=None,
                        )
                    )

        return entities

    # ------------------------------------------------------------------
    # Product recognizer
    # ------------------------------------------------------------------

    def _recognize_products(self, text: str) -> list[NEREntity]:
        """Recognize products using regex pattern matching."""
        from synapse.nlp.dict.person_patterns import PRODUCT_PATTERNS

        entities: list[NEREntity] = []
        for pattern in PRODUCT_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                surface = match.group(0)

                overlaps = False
                for existing in entities:
                    if self._spans_overlap(start, end, existing.start_offset, existing.end_offset):
                        overlaps = True
                        break

                if not overlaps:
                    entities.append(
                        NEREntity(
                            surface_form=surface,
                            entity_type="product",
                            start_offset=start,
                            end_offset=end,
                            confidence=0.80,
                            linked_ticker=None,
                            normalized_name=None,
                        )
                    )

        return entities

    # ------------------------------------------------------------------
    # Ticker linking (fuzzy matching)
    # ------------------------------------------------------------------

    def _link_tickers(self, entities: list[NEREntity]) -> list[NEREntity]:
        """Link company entities to tickers via fuzzy matching.

        For entities that already have a ticker (exact match in dictionary),
        keep it. For unmatched companies, attempt fuzzy matching against
        all known company names.
        """
        from synapse.nlp.dict.company_dict import COMPANY_NAMES

        # Build a reverse lookup: ticker -> list of names
        ticker_to_names: dict[str, list[str]] = {}
        for name, ticker in COMPANY_NAMES.items():
            ticker_to_names.setdefault(ticker, []).append(name)

        linked: list[NEREntity] = []
        for entity in entities:
            if entity.entity_type != "company" or entity.linked_ticker is not None:
                linked.append(entity)
                continue

            # Try fuzzy matching against all company names
            best_ticker: Optional[str] = None
            best_score: float = 0.0

            for name, ticker in COMPANY_NAMES.items():
                score = SequenceMatcher(None, entity.surface_form, name).ratio()
                if score > best_score and score >= FUZZY_MATCH_THRESHOLD:
                    best_score = score
                    best_ticker = ticker

            if best_ticker is not None:
                # Create new entity with linked ticker and adjusted confidence
                linked.append(
                    NEREntity(
                        surface_form=entity.surface_form,
                        entity_type=entity.entity_type,
                        start_offset=entity.start_offset,
                        end_offset=entity.end_offset,
                        confidence=min(entity.confidence, best_score),
                        linked_ticker=best_ticker,
                        normalized_name=entity.normalized_name,
                    )
                )
            else:
                linked.append(entity)

        return linked

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _spans_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
        """Check if two character spans overlap."""
        return start1 < end2 and start2 < end1

    @staticmethod
    def _deduplicate_entities(entities: list[NEREntity]) -> list[NEREntity]:
        """Deduplicate overlapping entity spans, keeping highest confidence.

        When two entities overlap, keep the one with higher confidence.
        If same confidence, prefer the longer span.
        """
        if not entities:
            return []

        # Sort by start_offset, then by confidence descending, then by length descending
        sorted_entities = sorted(
            entities,
            key=lambda e: (e.start_offset, -e.confidence, -(e.end_offset - e.start_offset)),
        )

        result: list[NEREntity] = []
        for entity in sorted_entities:
            overlaps = False
            for existing in result:
                if NEREngine._spans_overlap(
                    entity.start_offset, entity.end_offset,
                    existing.start_offset, existing.end_offset,
                ):
                    overlaps = True
                    break
            if not overlaps:
                result.append(entity)

        return result
