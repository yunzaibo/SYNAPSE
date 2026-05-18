"""Tests for SecurityIdentity (ADR-007)."""

import pytest

from synapse.core.identity import SecurityIdentity


class TestSecurityIdentity:
    """Tests for composite security identity."""

    def test_create_from_components(self):
        si = SecurityIdentity(market="CN_A", exchange="SH", ticker="600519")
        assert si.security_id == "cn.sh.600519"

    def test_create_from_ticker_factory(self):
        si = SecurityIdentity.from_ticker("CN_A", "SH", "600519")
        assert si.security_id == "cn.sh.600519"

    def test_market_lowercased(self):
        si = SecurityIdentity(market="CN_A", exchange="SH", ticker="600519")
        assert si.market == "cn"

    def test_exchange_lowercased(self):
        si = SecurityIdentity(market="CN_A", exchange="SH", ticker="600519")
        assert si.exchange == "sh"

    def test_ticker_preserved(self):
        si = SecurityIdentity(market="CN_A", exchange="SZ", ticker="000858")
        assert si.ticker == "000858"

    def test_sz_exchange(self):
        si = SecurityIdentity(market="CN_A", exchange="SZ", ticker="000858")
        assert si.security_id == "cn.sz.000858"

    def test_from_string(self):
        si = SecurityIdentity.from_string("cn.sh.600519")
        assert si.market == "cn"
        assert si.exchange == "sh"
        assert si.ticker == "600519"
        assert si.security_id == "cn.sh.600519"

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid security_id format"):
            SecurityIdentity.from_string("invalid")

    def test_frozen(self):
        si = SecurityIdentity(market="CN_A", exchange="SH", ticker="600519")
        with pytest.raises(AttributeError):
            si.market = "us"

    def test_str(self):
        si = SecurityIdentity(market="CN_A", exchange="SH", ticker="600519")
        assert str(si) == "cn.sh.600519"
