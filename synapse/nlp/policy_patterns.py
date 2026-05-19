"""Policy patterns -- Issuing body detection, effective date extraction,
and document type classification for Chinese regulatory documents.

Part of P4 Chinese Financial NLP Layer (F-040 Policy Document Understander).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Issuing body detection patterns
# ---------------------------------------------------------------------------

ISSUING_BODY_HEADERS: dict[str, str] = {
    "中国人民银行": "PBOC",
    "人民银行": "PBOC",
    "央行": "PBOC",
    "中国证券监督管理委员会": "CSRC",
    "中国证监会": "CSRC",
    "证监会": "CSRC",
    "国务院": "State_Council",
    "国务院办公厅": "State_Council",
}

# Longer patterns first to avoid partial matches
_ISSUING_BODY_SORTED: list[tuple[str, str]] = sorted(
    ISSUING_BODY_HEADERS.items(), key=lambda kv: len(kv[0]), reverse=True
)


# ---------------------------------------------------------------------------
# Effective date patterns
# ---------------------------------------------------------------------------

# Matches: 自2026年6月1日起施行, 自2026年6月1日起..., 自2026-06-01起施行
_DATE_CHINESE_RE = re.compile(
    r"自\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*起"
)

# Matches: 生效日期：2026年6月1日, 生效日期:2026-06-01
_DATE_LABEL_RE = re.compile(
    r"生效日期[：:]\s*(\d{4})\s*[年\-\.]\s*(\d{1,2})\s*[月\-\.]\s*(\d{1,2})\s*日?"
)

# Matches: 自公布之日起施行 (no specific date)
_DATE_PUBLISH_RE = re.compile(r"自公布之日起施行")

# Matches: 本办法自发布之日起施行
_DATE發布_RE = re.compile(r"自发布之日起施行")


# ---------------------------------------------------------------------------
# Document type classification patterns
# ---------------------------------------------------------------------------

DOCUMENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "monetary_policy": (
        "存款准备金", "利率", "公开市场操作", "逆回购", "MLF", "再贷款",
        "货币政策", "基准利率", "LPR", "SLF", "常备借贷便利",
        "中期借贷便利", "公开市场", "货币供应",
    ),
    "regulatory_rule": (
        "管理办法", "管理规定", "实施细则", "监管规则", "合规要求",
        "审批", "备案", "信息披露", "内控", "风险管理",
    ),
    "guidance": (
        "指导意见", "指导意见", "建议", "指引", "导向",
        "政策指引", "工作要求", "通知", "关于",
    ),
    "enforcement": (
        "处罚", "罚款", "责令改正", "行政处罚", "警告",
        "没收违法所得", "禁入", "监管措施", "通报批评",
    ),
}

# Order matters: more specific types checked first
_DOCUMENT_TYPE_ORDER: list[str] = [
    "monetary_policy",
    "enforcement",
    "regulatory_rule",
    "guidance",
]


# ---------------------------------------------------------------------------
# Key change extraction patterns
# ---------------------------------------------------------------------------

CHANGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:调整|下调|上调|修改|新增|取消|废止|暂停|恢复).{0,30}(?:政策|规则|利率|费率|比例|要求)"),
    re.compile(r"(?:自.{0,20}日起).{0,40}(?:施行|执行|适用)"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IssuingBodyMatch:
    """Result of issuing body detection.

    Attributes
    ----------
    body:
        Standardized body identifier (PBOC, CSRC, State_Council, or unknown).
    matched_keyword:
        The keyword that was matched in the document text.
    confidence:
        Detection confidence in [0.0, 1.0].
    """

    body: str = "unknown"
    matched_keyword: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "body": self.body,
            "matched_keyword": self.matched_keyword,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> IssuingBodyMatch:
        return cls(
            body=data.get("body", "unknown"),
            matched_keyword=data.get("matched_keyword", ""),
            confidence=float(data.get("confidence", 0.0)),
        )


def detect_issuing_body(text: str) -> IssuingBodyMatch:
    """Detect the issuing body from policy document text.

    Parameters
    ----------
    text:
        Raw text of a Chinese regulatory document.

    Returns
    -------
    IssuingBodyMatch with body identifier, matched keyword, and confidence.
    """
    for keyword, body in _ISSUING_BODY_SORTED:
        if keyword in text:
            # Longer matched keywords = higher confidence
            confidence = min(0.7 + len(keyword) * 0.03, 1.0)
            return IssuingBodyMatch(
                body=body, matched_keyword=keyword, confidence=confidence
            )
    return IssuingBodyMatch(body="unknown", matched_keyword="", confidence=0.0)


def extract_effective_date(text: str) -> str | None:
    """Extract the effective date from a policy document.

    Parameters
    ----------
    text:
        Raw text of a Chinese regulatory document.

    Returns
    -------
    ISO date string (YYYY-MM-DD) if found, else None.
    """
    # Try explicit date patterns first
    for pattern in (_DATE_CHINESE_RE, _DATE_LABEL_RE):
        match = pattern.search(text)
        if match:
            year, month, day = match.group(1), match.group(2), match.group(3)
            try:
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            except ValueError:
                continue

    # Check for relative date references
    if _DATE_PUBLISH_RE.search(text) or _DATE發布_RE.search(text):
        return "upon_publish"

    return None


def classify_document_type(text: str) -> str:
    """Classify the document type from policy text.

    Parameters
    ----------
    text:
        Raw text of a Chinese regulatory document.

    Returns
    -------
    Document type string: monetary_policy, regulatory_rule, guidance,
    or enforcement. Defaults to "guidance" if no strong match.
    """
    # Score each type by keyword hit count
    scores: dict[str, int] = {}
    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[doc_type] = count

    if not scores:
        return "guidance"

    # Return the type with most keyword hits, using type order as tiebreaker
    best_type = max(
        scores,
        key=lambda t: (scores[t], -_DOCUMENT_TYPE_ORDER.index(t) if t in _DOCUMENT_TYPE_ORDER else -99),
    )
    return best_type


def extract_key_changes(text: str) -> tuple[str, ...]:
    """Extract key regulatory changes from policy text.

    Parameters
    ----------
    text:
        Raw text of a Chinese regulatory document.

    Returns
    -------
    Tuple of extracted change descriptions.
    """
    changes: list[str] = []
    for pattern in CHANGE_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0).strip()
            if snippet and snippet not in changes:
                changes.append(snippet)
    return tuple(changes)
