"""Tests for Object Validation (TASK-003)."""

import pytest

from synapse.core.validation import validate_object, validate_required_fields
from synapse.core.schemas.base import BaseSchema, ObjectStatus, SourceType, CreatorType, MarketContext
from synapse.core.schemas.thesis import Thesis, Confidence
from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.schemas.watchlist import WatchlistEntry


class TestValidateObject:
    def test_valid_object(self):
        th = Thesis(id="ths_valid01", title="有效 Thesis")
        errors = validate_object(th)
        assert errors == []

    def test_empty_id(self):
        th = Thesis(id="")
        errors = validate_object(th)
        assert any("id" in e for e in errors)

    def test_valid_status(self):
        for status in ObjectStatus:
            th = Thesis(id="ths_test", status=status)
            errors = validate_object(th)
            assert errors == []

    def test_valid_source_type(self):
        for st in SourceType:
            th = Thesis(id="ths_test", source_type=st)
            errors = validate_object(th)
            assert errors == []

    def test_valid_created_by(self):
        for cb in CreatorType:
            th = Thesis(id="ths_test", created_by=cb)
            errors = validate_object(th)
            assert errors == []

    def test_empty_schema_version(self):
        th = Thesis(id="ths_test", schema_version="")
        errors = validate_object(th)
        assert any("schema_version" in e for e in errors)

    def test_valid_market_context(self):
        mc = MarketContext(research_date="2026-05-18", market_date="2026-05-18")
        th = Thesis(id="ths_test", market_context=mc)
        errors = validate_object(th)
        assert errors == []


class TestValidateRequiredFields:
    def test_all_fields_present(self):
        th = Thesis(id="ths_test", title="测试", thesis_statement="测试陈述")
        errors = validate_required_fields(th, ["id", "title", "thesis_statement"])
        assert errors == []

    def test_missing_title(self):
        th = Thesis(id="ths_test", title="")
        errors = validate_required_fields(th, ["id", "title"])
        assert len(errors) == 1
        assert "title" in errors[0]

    def test_missing_thesis_statement(self):
        th = Thesis(id="ths_test", thesis_statement="")
        errors = validate_required_fields(th, ["thesis_statement"])
        assert len(errors) == 1
        assert "thesis_statement" in errors[0]

    def test_missing_multiple_fields(self):
        th = Thesis(id="ths_test", title="", thesis_statement="")
        errors = validate_required_fields(th, ["title", "thesis_statement"])
        assert len(errors) == 2

    def test_none_field(self):
        th = Thesis(id="ths_test", topic_id=None)
        errors = validate_required_fields(th, ["topic_id"])
        assert len(errors) == 1

    def test_list_field_empty(self):
        th = Thesis(id="ths_test", related_securities=[])
        errors = validate_required_fields(th, ["related_securities"])
        assert len(errors) == 1

    def test_no_required_fields(self):
        th = Thesis(id="ths_test")
        errors = validate_required_fields(th, [])
        assert errors == []
