"""Mechanical checks of one generated block against its source quote.

Every check here is decidable from the two strings, so a block that fails one is replaced by its
original quote rather than sent back to the model a third time.
"""

import re

from ...core.text import locate_quote

FORBIDDEN_ABSOLUTE_PHRASES = [
    "누구나", "무조건", "조건 없이", "조건없이", "묻지도 따지지도", "묻지도따지지도",
    "역대급", "최강", "끝판왕", "종결자", "꿀혜택", "꿀 혜택",
    "최고", "최저", "최상", "최초", "최대", "1위", "제일", "유일",
]  # fmt: skip
HEDGE_MARKERS = [
    "수 있습니다", "수있습니다", "수 있어요", "수 있음", "따라 다름", "따라 달라집니다",
    "따라 다를 수", "경우에 따라", "심사 결과", "가능성이 있습니다", "할 수도 있습니다",
]  # fmt: skip
CONDITION_KEYWORDS = [
    "제외", "이상", "이하", "미만", "초과", "한도", "조건", "예외", "위약금", "수수료",
    "연체", "불이익", "책임", "제휴사", "제휴회사", "협력사", "약관", "설명서", "권유",
    "신용점수", "하락", "해지", "변동",
]  # fmt: skip
NUMBER_RE = re.compile(r"\d[\d,.]*")


def strip_ws(s: str) -> str:
    return "".join(s.split())


def number_set(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in NUMBER_RE.findall(text)}


def verify_source_quote(text: str, quote: str) -> str:
    """quote가 실제 입력 텍스트(text)에서 확인되면 빈 문자열, 아니면 이유를 돌려준다."""
    return "" if locate_quote(text, quote) else "source_quote를 원문에서 확인할 수 없음"


def verify_block(quote: str, text: str) -> list[str]:
    """원문 quote 대비 생성한 text의 수치·단정 표현·가능성 표현·조건 키워드를 기계적으로 대조한다.
    문제가 없으면 빈 리스트를 돌려준다."""
    problems: list[str] = []
    q_nums, t_nums = number_set(quote), number_set(text)
    extra_nums = sorted(t_nums - q_nums)
    missing_nums = sorted(q_nums - t_nums)
    if extra_nums:
        problems.append(f"원문에 없는 수치 포함: {', '.join(extra_nums)}")
    if missing_nums:
        problems.append(f"원문 수치 누락: {', '.join(missing_nums)}")

    q_compact, t_compact = strip_ws(quote), strip_ws(text)
    added_phrases = [
        p
        for p in FORBIDDEN_ABSOLUTE_PHRASES
        if strip_ws(p) in t_compact and strip_ws(p) not in q_compact
    ]
    if added_phrases:
        problems.append(f"원문에 없는 단정·최상급 표현 포함: {', '.join(added_phrases)}")

    had_hedge = any(strip_ws(m) in q_compact for m in HEDGE_MARKERS)
    kept_hedge = any(strip_ws(m) in t_compact for m in HEDGE_MARKERS)
    if had_hedge and not kept_hedge:
        problems.append("원문의 가능성·조건 표현이 쉬운말에서 확정 표현으로 바뀜")

    dropped_keywords = [k for k in CONDITION_KEYWORDS if k in quote and k not in text]
    if dropped_keywords:
        problems.append(f"조건·불이익 관련 문구 누락 가능: {', '.join(dropped_keywords)}")
    return problems


def verify_terms(quote: str, terms: list[str]) -> list[str]:
    """quote 안에서 실제로 확인되는 용어만 남긴다(근거 없는 용어 풀이 방지)."""
    q_compact = strip_ws(quote)
    return [t for t in terms if strip_ws(t) and strip_ws(t) in q_compact]
