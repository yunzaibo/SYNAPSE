"""Metric Dictionary -- Financial metric abbreviations and standard names.

METRIC_ALIASES maps abbreviations and aliases to their standard Chinese names.
Used for dictionary-based NER metric recognition.
"""

from __future__ import annotations


# Format: {abbreviation/alias: standard_name}
METRIC_ALIASES: dict[str, str] = {
    # Profitability
    "ROE": "净资产收益率",
    "净资产收益率": "净资产收益率",
    "ROA": "总资产收益率",
    "总资产收益率": "总资产收益率",
    "ROIC": "投入资本回报率",
    "投入资本回报率": "投入资本回报率",
    "毛利率": "毛利率",
    "净利率": "净利率",
    "净利润率": "净利润率",
    "营业利润率": "营业利润率",
    # Per share
    "EPS": "每股收益",
    "每股收益": "每股收益",
    "基本每股收益": "基本每股收益",
    "稀释每股收益": "稀释每股收益",
    "每股净资产": "每股净资产",
    "BVPS": "每股净资产",
    "每股经营现金流": "每股经营现金流",
    "每股未分配利润": "每股未分配利润",
    "每股股利": "每股股利",
    "DPS": "每股股利",
    # Valuation
    "PE": "市盈率",
    "市盈率": "市盈率",
    "PE(TTM)": "市盈率(TTM)",
    "动态市盈率": "动态市盈率",
    "静态市盈率": "静态市盈率",
    "PB": "市净率",
    "市净率": "市净率",
    "PS": "市销率",
    "市销率": "市销率",
    "PEG": "市盈率相对盈利增长比率",
    "EV": "企业价值",
    "EV/EBITDA": "企业价值/息税折旧摊销前利润",
    "EBITDA": "息税折旧摊销前利润",
    "FCFF": "企业自由现金流量",
    "FCFE": "股权自由现金流量",
    # Growth
    "营收增长率": "营收增长率",
    "净利润增长率": "净利润增长率",
    "扣非净利润增长率": "扣非净利润增长率",
    "营收同比": "营收同比增长率",
    "净利同比": "净利润同比增长率",
    # Balance sheet
    "资产负债率": "资产负债率",
    "流动比率": "流动比率",
    "速动比率": "速动比率",
    "产权比率": "产权比率",
    "有息负债率": "有息负债率",
    # Cash flow
    "经营性现金流": "经营活动产生的现金流量净额",
    "投资性现金流": "投资活动产生的现金流量净额",
    "筹资性现金流": "筹资活动产生的现金流量净额",
    "自由现金流": "企业自由现金流量",
    "现金流覆盖率": "现金流覆盖率",
    # Dividend
    "股息率": "股息率",
    "分红率": "分红率",
    "派息率": "派息率",
    # Revenue / Profit
    "营收": "营业收入",
    "营业收入": "营业收入",
    "净利润": "净利润",
    "归母净利润": "归属于母公司所有者的净利润",
    "扣非净利润": "扣除非经常性损益后的净利润",
    "毛利润": "毛利润",
    "营业利润": "营业利润",
    "利润总额": "利润总额",
    # Market
    "总市值": "总市值",
    "流通市值": "流通市值",
    "换手率": "换手率",
    "振幅": "振幅",
    "量比": "量比",
    "委比": "委比",
}


def get_standard_name(alias: str) -> str | None:
    """Look up the standard name for a metric alias.

    Parameters
    ----------
    alias:
        Metric abbreviation or alias.

    Returns
    -------
    Standard metric name or None if not found.
    """
    return METRIC_ALIASES.get(alias)


def get_all_aliases() -> list[str]:
    """Return all metric aliases in the dictionary.

    Returns
    -------
    List of metric alias strings.
    """
    return list(METRIC_ALIASES.keys())
