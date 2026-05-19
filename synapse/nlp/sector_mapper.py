"""SectorMapper -- Map policy keywords to affected financial sectors.

Identifies 8+ sectors (banking, insurance, securities, real_estate,
technology, healthcare, energy, consumer) from Chinese regulatory text
using keyword-based matching.

Part of P4 Chinese Financial NLP Layer (F-040 Policy Document Understander).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Sector keyword dictionary
# ---------------------------------------------------------------------------

SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "banking": (
        "银行", "存款", "贷款", "信贷", "商业银行", "政策性银行",
        "存款准备金", "存贷款", "净息差", "不良贷款", "拨备",
    ),
    "insurance": (
        "保险", "保险公司", "寿险", "车险", "健康险", "再保险",
        "偿付能力", "保费", "保单", "理赔", "银保监",
    ),
    "securities": (
        "证券", "券商", "交易所", "上市", "IPO", "股票",
        "基金", "资管", "投行", "经纪", "自营业务", "融资融券",
    ),
    "real_estate": (
        "房地产", "楼市", "住房", "房贷", "按揭", "土地",
        "限购", "限贷", "公积金", "保障房", "开发商", "商品房",
    ),
    "technology": (
        "科技", "互联网", "人工智能", "AI", "芯片", "半导体",
        "数字经济", "数据", "云计算", "区块链", "网络安全",
    ),
    "healthcare": (
        "医药", "医疗", "药品", "医院", "生物", "疫苗",
        "医疗器械", "临床", "仿制药", "集采", "带量采购",
    ),
    "energy": (
        "能源", "石油", "天然气", "煤炭", "电力", "新能源",
        "光伏", "风电", "碳排放", "碳中和", "储能",
    ),
    "consumer": (
        "消费", "零售", "电商", "食品", "饮料", "白酒",
        "家电", "汽车", "旅游", "餐饮", "日用品",
    ),
}

# All known sector names
ALL_SECTORS: frozenset[str] = frozenset(SECTOR_KEYWORDS.keys())


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SectorMatch:
    """Result of mapping a single sector.

    Attributes
    ----------
    sector:
        Sector name (e.g. "banking").
    matched_keywords:
        Keywords that matched in the document text.
    confidence:
        Mapping confidence in [0.0, 1.0].
    """

    sector: str = ""
    matched_keywords: tuple[str, ...] = ()
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "sector": self.sector,
            "matched_keywords": list(self.matched_keywords),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SectorMatch:
        return cls(
            sector=data.get("sector", ""),
            matched_keywords=tuple(data.get("matched_keywords", [])),
            confidence=float(data.get("confidence", 0.0)),
        )


# ---------------------------------------------------------------------------
# SectorMapper
# ---------------------------------------------------------------------------

class SectorMapper:
    """Map policy text to affected financial sectors via keyword matching.

    Usage::

        mapper = SectorMapper()
        matches = mapper.map_to_sectors("央行下调存款准备金率，利好银行板块")
        assert matches[0].sector == "banking"
    """

    def map_to_sectors(self, text: str) -> list[SectorMatch]:
        """Identify affected sectors from policy text.

        Parameters
        ----------
        text:
            Chinese regulatory document text.

        Returns
        -------
        List of SectorMatch, sorted by confidence descending.
        """
        if not text:
            return []

        matches: list[SectorMatch] = []
        for sector, keywords in SECTOR_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in text]
            if matched:
                # Confidence scales with number of keyword hits, capped at 1.0
                confidence = min(0.5 + len(matched) * 0.1, 1.0)
                matches.append(
                    SectorMatch(
                        sector=sector,
                        matched_keywords=tuple(matched),
                        confidence=round(confidence, 2),
                    )
                )

        # Sort by confidence descending, then by sector name
        matches.sort(key=lambda m: (-m.confidence, m.sector))
        return matches

    def map_to_sector_names(self, text: str) -> tuple[str, ...]:
        """Return only sector names (convenience method).

        Parameters
        ----------
        text:
            Chinese regulatory document text.

        Returns
        -------
        Tuple of sector name strings.
        """
        return tuple(m.sector for m in self.map_to_sectors(text))
