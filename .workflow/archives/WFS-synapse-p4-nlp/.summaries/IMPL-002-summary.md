# Task: IMPL-002 Financial Sentiment Lexicon

## Implementation Summary

### Files Created
- `synapse/nlp/lexicon/__init__.py`: Lexicon sub-package init with lazy imports for all public API
- `synapse/nlp/lexicon/sentiment_dict.yaml`: 515 Chinese financial sentiment terms across 7 categories
- `synapse/nlp/lexicon/loader.py`: LexiconLoader with YAML loading, schema validation, memory cache
- `synapse/nlp/lexicon/negation.py`: NegationDetector with context window-based negation detection
- `synapse/nlp/lexicon/degree.py`: DegreeModifier with 3-level intensity scaling
- `synapse/nlp/lexicon/scorer.py`: EnhancedLexiconAnalyzer extending social.py LexiconAnalyzer
- `tests/unit/test_sentiment_lexicon.py`: 44 unit tests covering all components

### Files Modified
- `synapse/nlp/__init__.py`: Added lazy imports for lexicon components (EnhancedLexiconAnalyzer, LexiconLoader, etc.)

### Content Added

**TermEntry** (`synapse/nlp/lexicon/loader.py`): Frozen dataclass for a single sentiment term entry
- Fields: term, sentiment, score, category, negation_sensitive, context_window
- to_dict()/from_dict() round-trip serialization

**LexiconMeta** (`synapse/nlp/lexicon/loader.py`): Frozen dataclass for lexicon metadata
- Fields: version, description, total_terms, category_counts, load_time_ms

**LexiconLoader** (`synapse/nlp/lexicon/loader.py`): YAML-based lexicon loader
- load(path) -> (dict[str, TermEntry], LexiconMeta): loads and validates YAML
- load_terms(path) -> dict[str, TermEntry]: convenience method
- add_custom_terms(terms_dict, custom_terms): runtime term addition
- clear_cache(): invalidates in-memory cache
- Schema validation: required fields, sentiment values, score range, category values

**NegationDetector** (`synapse/nlp/lexicon/negation.py`): Context window-based negation detection
- detect(text, term, term_start) -> NegationResult: full result with marker details
- detect_all(text, term_positions) -> list[NegationResult]: batch detection
- is_negated(text, term, term_start) -> bool: quick boolean check
- Handles 5 single-char markers (不/没/未/非/无) + 10 multi-char markers
- Exclusion list prevents false positives (e.g. "非" in "非常" is not negation)

**DegreeModifier** (`synapse/nlp/lexicon/degree.py`): Intensity modifier detection
- detect(text, term, term_start) -> DegreeResult: full result with level and multiplier
- detect_all(text, term_positions) -> list[DegreeResult]: batch detection
- get_multiplier(text, term, term_start) -> float: quick multiplier lookup
- 3 levels: strong (1.5x), moderate (1.0x), weak (0.5x)
- 23 strong markers, 10 moderate markers, 12 weak markers

**EnhancedLexiconAnalyzer** (`synapse/nlp/lexicon/scorer.py`): Extended sentiment scorer
- Inherits from LexiconAnalyzer (synapse/event/social.py)
- score(text) -> float: negation-aware, degree-modified scoring in [-1.0, 1.0]
- score_with_breakdown(text) -> ScoreBreakdown: detailed per-term breakdown
- score_by_category(text) -> dict[str, float]: category-level aggregation
- from_yaml(path) -> EnhancedLexiconAnalyzer: classmethod for custom YAML
- add_term(entry) / remove_term(term): runtime lexicon modification
- list_terms(category) -> list[TermEntry]: term enumeration

**ScoreBreakdown** (`synapse/nlp/lexicon/scorer.py`): Detailed scoring result
- Fields: text, raw_score, final_score, matched_terms, negation_flips, degree_adjustments
- to_dict()/from_dict() round-trip serialization

### Lexicon Statistics
- **Total terms**: 515
- **Categories**: growth(81), decline(73), risk(63), opportunity(51), market(60), regulatory(52), neutral(135)
- **Sentiments**: bullish(185), bearish(194), neutral(132)
- **Format**: YAML with version, description, and per-entry schema

## Outputs for Dependent Tasks

### Available Components
```python
# Import from synapse.nlp.lexicon (preferred)
from synapse.nlp.lexicon import EnhancedLexiconAnalyzer, LexiconLoader, TermEntry
from synapse.nlp.lexicon import NegationDetector, DegreeModifier, ScoreBreakdown

# Or from synapse.nlp (top-level)
from synapse.nlp import EnhancedLexiconAnalyzer, LexiconLoader
```

### Integration Points
- **EnhancedLexiconAnalyzer**: Drop-in replacement for LexiconAnalyzer with negation/degree awareness
- **LexiconLoader**: Load custom YAML lexicons for domain-specific tuning
- **TermEntry**: Schema for adding/removing terms at runtime
- **ScoreBreakdown**: Detailed scoring for debugging and analysis

### Usage Examples
```python
from synapse.nlp.lexicon import EnhancedLexiconAnalyzer

# Basic scoring (backward-compatible with LexiconAnalyzer)
analyzer = EnhancedLexiconAnalyzer()
score = analyzer.score("业绩超预期，高增长")  # > 0

# Negation-aware scoring
score = analyzer.score("不超预期")  # < 0 (flipped)

# Degree-modified scoring
score = analyzer.score("非常高增长")  # amplified by 1.5x

# Detailed breakdown
breakdown = analyzer.score_with_breakdown("业绩超预期")
print(breakdown.final_score, breakdown.negation_flips)

# Category-level analysis
cats = analyzer.score_by_category("业绩超预期，高风险")
# {'growth': 0.85, 'risk': -0.8}

# Custom YAML lexicon
analyzer = EnhancedLexiconAnalyzer.from_yaml("my_lexicon.yaml")

# Runtime term management
from synapse.nlp.lexicon import TermEntry
analyzer.add_term(TermEntry(term="custom", sentiment="bullish", score=0.9, category="growth"))
analyzer.remove_term("custom")
```

## Status: Complete
