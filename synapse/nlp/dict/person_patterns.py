"""Person Patterns -- Person name detection for Chinese financial text.

Uses role-based suffix matching (analyst, executive, regulator names)
combined with Chinese name length heuristics.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Person name suffixes (role-based)
# ---------------------------------------------------------------------------

# Common professional role suffixes in financial context
PERSON_SUFFIXES: list[str] = [
    "分析师", "研究员", "高级分析师", "首席分析师", "首席研究员",
    "董事长", "副董事长", "总经理", "副总经理", "总裁", "副总裁",
    "CEO", "CFO", "CTO", "COO",
    "董事", "监事", "独立董事", "执行董事",
    "总经理", "副总经理", "总会计师", "总工程师", "总法律顾问",
    "部门经理", "部门总监", "部门主管",
    "首席经济学家", "经济学家", "策略分析师",
    "基金经理", "投资经理", "基金经理助理",
    "行长", "副行长", "行长助理",
    "主任", "副主任", "院长", "副院长",
    "主席", "副主席",
    "秘书长", "副秘书长",
    "部长", "副部长", "司长", "副司长", "局长", "副局长",
    "处长", "副处长",
    "发言人", "新闻发言人",
]

# Person role patterns (regex): name + role suffix
# Chinese name: 2-4 characters, followed by a role suffix
PERSON_ROLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"([\u4e00-\u9fff]{2,4})" + suffix)
    for suffix in PERSON_SUFFIXES
]

# Reverse patterns: role prefix + name (e.g. "分析师张三")
# Chinese name: 2-4 characters, preceded by a role suffix
PERSON_PREFIX_PATTERNS: list[re.Pattern] = [
    re.compile(suffix + r"([\u4e00-\u9fff]{2,4})")
    for suffix in PERSON_SUFFIXES
]

# Generic Chinese name pattern (2-4 hanzi characters) with context markers
# This is a heuristic and may produce false positives
GENERIC_PERSON_PATTERN = re.compile(
    r"(?:由|让|是|与|和|跟|对|向|给|请|让|被|将|已|曾)([\u4e00-\u9fff]{2,4})(?:表示|认为|指出|称|说|提到|强调|建议|认为|透露)"
)


def has_person_suffix(text: str) -> list[tuple[str, int, int]]:
    """Find person names with role suffixes (name + suffix or suffix + name).

    Parameters
    ----------
    text:
        Chinese text to search.

    Returns
    -------
    List of (name, start, end) tuples where start/end are character offsets.
    """
    results: list[tuple[str, int, int]] = []
    # Forward patterns: name + suffix (e.g. "张三分析师")
    for pattern in PERSON_ROLE_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            results.append((name, match.start(1), match.end(1)))
    # Reverse patterns: suffix + name (e.g. "分析师张三")
    for pattern in PERSON_PREFIX_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            results.append((name, match.start(1), match.end(1)))
    # Deduplicate by (name, start) while keeping the longest match
    seen: set[tuple[str, int]] = set()
    deduped: list[tuple[str, int, int]] = []
    for name, start, end in sorted(results, key=lambda x: -(x[2] - x[1])):
        key = (name, start)
        if key not in seen:
            seen.add(key)
            deduped.append((name, start, end))
    return deduped


def find_generic_persons(text: str) -> list[tuple[str, int, int]]:
    """Find person names using context-based heuristics.

    Looks for patterns like "由张三表示" or "李四认为".

    Parameters
    ----------
    text:
        Chinese text to search.

    Returns
    -------
    List of (name, start, end) tuples.
    """
    results: list[tuple[str, int, int]] = []
    for match in GENERIC_PERSON_PATTERN.finditer(text):
        name = match.group(1)
        results.append((name, match.start(1), match.end(1)))
    return results


# Institution patterns (regex)
INSTITUTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"中国证券监督管理委员会"),
    re.compile(r"证监会"),
    re.compile(r"中国人民银行"),
    re.compile(r"央行"),
    re.compile(r"中国银保监会"),
    re.compile(r"银保监会"),
    re.compile(r"国家金融监督管理总局"),
    re.compile(r"金融监管总局"),
    re.compile(r"财政部"),
    re.compile(r"国家发展和改革委员会"),
    re.compile(r"发改委"),
    re.compile(r"国务院"),
    re.compile(r"中国共产党中央委员会"),
    re.compile(r"中共中央"),
    re.compile(r"全国人大常委会"),
    re.compile(r"全国人大"),
    re.compile(r"上海证券交易所"),
    re.compile(r"上交所"),
    re.compile(r"深圳证券交易所"),
    re.compile(r"深交所"),
    re.compile(r"北京证券交易所"),
    re.compile(r"北交所"),
    re.compile(r"中国银行间市场交易商协会"),
    re.compile(r"中央国债登记结算有限责任公司"),
    re.compile(r"中国证券登记结算有限责任公司"),
    re.compile(r"中国期货业协会"),
    re.compile(r"中国证券业协会"),
    re.compile(r"中国基金业协会"),
    re.compile(r"国家统计局"),
    re.compile(r"海关总署"),
    re.compile(r"商务部"),
    re.compile(r"工业和信息化部"),
    re.compile(r"工信部"),
    re.compile(r"科技部"),
    re.compile(r"生态环境部"),
    re.compile(r"住房和城乡建设部"),
    re.compile(r"交通运输部"),
    re.compile(r"农业农村部"),
    re.compile(r"中国人民保险集团"),
    re.compile(r"中国出口信用保险公司"),
]

# Product patterns (brands/products common in financial text)
PRODUCT_PATTERNS: list[re.Pattern] = [
    re.compile(r"茅台酒"),
    re.compile(r"飞天茅台"),
    re.compile(r"五粮液酒"),
    re.compile(r"国窖1573"),
    re.compile(r"华为Mate"),
    re.compile(r"iPhone"),
    re.compile(r"iPad"),
    re.compile(r"Model [3YX]"),
    re.compile(r"比亚迪汉"),
    re.compile(r"比亚迪唐"),
    re.compile(r"比亚迪宋"),
    re.compile(r"理想L[0-9]+"),
    re.compile(r"蔚来[ES][0-9]+"),
    re.compile(r"小鹏[PG][0-9]+"),
]
