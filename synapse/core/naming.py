"""File naming rules and ID generation for research objects.

Naming conventions from 01_Research_Object_Schema.md:
- ID format: <prefix>_<6-char hex>
- Thesis dir: ths_<id>_<slug>/
- Decision dir: dec_<date>_<action>_<symbol>/
- Watchlist: wl_<symbol>_<reason>.yaml
- Position: pos_<market>_<symbol>.yaml
"""

from __future__ import annotations

import uuid


def generate_id(prefix: str) -> str:
    """Generate a globally unique ID: prefix + '_' + 6-char hex.

    Args:
        prefix: Object type prefix (e.g. 'ths', 'dec', 'sig', 'rsk').

    Returns:
        String like 'ths_7f8c91'.
    """
    hex_part = uuid.uuid4().hex[:6]
    return f"{prefix}_{hex_part}"


def thesis_dir(thesis_id: str, slug: str) -> str:
    """Generate thesis directory name.

    Args:
        thesis_id: ID like 'ths_7f8c91'.
        slug: Human-readable slug like 'consumer-recovery'.

    Returns:
        Directory name like 'ths_7f8c91_consumer-recovery'.
    """
    return f"{thesis_id}_{slug}"


def decision_dir(date: str, action: str, symbol: str) -> str:
    """Generate decision directory name.

    Args:
        date: Date string like '20260518'.
        action: Action like 'buy' or 'sell'.
        symbol: Security symbol like '600519'.

    Returns:
        Directory name like 'dec_20260518_buy_600519'.
    """
    return f"dec_{date}_{action}_{symbol}"


def watchlist_filename(symbol: str, reason: str) -> str:
    """Generate watchlist entry filename.

    Args:
        symbol: Security symbol like '600519'.
        reason: Short reason like 'attention-spike'.

    Returns:
        Filename like 'wl_600519_attention-spike.yaml'.
    """
    return f"wl_{symbol}_{reason}.yaml"


def position_filename(market: str, symbol: str) -> str:
    """Generate position filename.

    Args:
        market: Market code like 'CN_A'.
        symbol: Security symbol like '600519'.

    Returns:
        Filename like 'pos_CN_A_600519.yaml'.
    """
    return f"pos_{market}_{symbol}.yaml"
