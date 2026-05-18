"""Tests for file naming rules and ID generation."""

import pytest

from synapse.core.naming import (
    decision_dir,
    generate_id,
    position_filename,
    thesis_dir,
    watchlist_filename,
)


class TestGenerateId:
    """Tests for generate_id()."""

    def test_starts_with_prefix(self):
        result = generate_id("ths")
        assert result.startswith("ths_")

    def test_total_length_10(self):
        """ths (3) + _ (1) + hex (6) = 10."""
        result = generate_id("ths")
        assert len(result) == 10

    def test_hex_is_hexadecimal(self):
        result = generate_id("ths")
        hex_part = result.split("_")[1]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_unique_ids(self):
        ids = {generate_id("ths") for _ in range(100)}
        assert len(ids) == 100

    def test_different_prefixes(self):
        dec_id = generate_id("dec")
        assert dec_id.startswith("dec_")
        assert len(dec_id) == 10

    def test_sig_prefix(self):
        sig_id = generate_id("sig")
        assert sig_id.startswith("sig_")


class TestThesisDir:
    """Tests for thesis_dir()."""

    def test_basic(self):
        result = thesis_dir("ths_7f8c91", "consumer-recovery")
        assert result == "ths_7f8c91_consumer-recovery"

    def test_multiple_words_slug(self):
        result = thesis_dir("ths_abc123", "ai-chip-supply-chain")
        assert result == "ths_abc123_ai-chip-supply-chain"


class TestDecisionDir:
    """Tests for decision_dir()."""

    def test_buy(self):
        result = decision_dir("20260518", "buy", "600519")
        assert result == "dec_20260518_buy_600519"

    def test_sell(self):
        result = decision_dir("20260601", "sell", "000858")
        assert result == "dec_20260601_sell_000858"


class TestWatchlistFilename:
    """Tests for watchlist_filename()."""

    def test_basic(self):
        result = watchlist_filename("600519", "attention-spike")
        assert result == "wl_600519_attention-spike.yaml"

    def test_yaml_extension(self):
        result = watchlist_filename("000858", "sector-rotation")
        assert result.endswith(".yaml")


class TestPositionFilename:
    """Tests for position_filename()."""

    def test_cn_a(self):
        result = position_filename("CN_A", "600519")
        assert result == "pos_CN_A_600519.yaml"

    def test_yaml_extension(self):
        result = position_filename("CN_A", "000858")
        assert result.endswith(".yaml")
