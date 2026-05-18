"""Tests for Market Semantics (T+1, price limits, suspension)."""

from datetime import date
from decimal import Decimal

import pytest

from synapse.core.market.semantics import (
    price_limit,
    is_suspended,
    validate_t1_settlement,
    SymbolType,
)


class TestPriceLimit:
    """Tests for price_limit()."""

    def test_main_board(self):
        assert price_limit("主板") == Decimal("0.10")

    def test_gem(self):
        assert price_limit("创业板") == Decimal("0.20")

    def test_star_market(self):
        assert price_limit("科创板") == Decimal("0.20")

    def test_st_stock(self):
        assert price_limit("ST") == Decimal("0.05")

    def test_bse(self):
        assert price_limit("北交所") == Decimal("0.30")

    def test_enum_input(self):
        assert price_limit(SymbolType.MAIN) == Decimal("0.10")
        assert price_limit(SymbolType.GEM) == Decimal("0.20")

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="Unknown symbol type"):
            price_limit("Invalid")

    def test_invalid_chinese_type(self):
        # Test with an invalid Chinese symbol type
        with pytest.raises(ValueError, match="Unknown symbol type"):
            price_limit("中小板")


class TestT1Settlement:
    """Tests for validate_t1_settlement()."""

    def test_sell_next_trading_day(self):
        # Buy on 2026-01-05 (Mon), sell on 2026-01-06 (Tue)
        assert validate_t1_settlement(date(2026, 1, 5), date(2026, 1, 6)) is True

    def test_sell_same_day_rejected(self):
        # Buy and sell on same day
        assert validate_t1_settlement(date(2026, 1, 5), date(2026, 1, 5)) is False

    def test_sell_after_holiday(self):
        # Buy on 2026-01-02 (Holiday), earliest sell is 2026-01-05 (Mon)
        assert validate_t1_settlement(date(2026, 1, 2), date(2026, 1, 5)) is True

    def test_sell_before_buy_raises(self):
        with pytest.raises(ValueError, match="sell_date.*cannot be before buy_date"):
            validate_t1_settlement(date(2026, 1, 6), date(2026, 1, 5))

    def test_sell_on_friday_buy_thursday(self):
        # Buy 2026-01-08 (Thu), sell 2026-01-09 (Fri)
        assert validate_t1_settlement(date(2026, 1, 8), date(2026, 1, 9)) is True


class TestIsSuspended:
    """Tests for is_suspended()."""

    def test_not_suspended(self):
        assert is_suspended("000001.SZ", date(2026, 1, 5)) is False

    def test_suspended_with_dates(self):
        suspended = {date(2026, 1, 5), date(2026, 1, 6)}
        assert is_suspended("000001.SZ", date(2026, 1, 5), suspended) is True
        assert is_suspended("000001.SZ", date(2026, 1, 7), suspended) is False

    def test_no_suspension_data(self):
        # No suspension data provided
        assert is_suspended("000001.SZ", date(2026, 1, 5), None) is False
