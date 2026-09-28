"""Mechanical string checks of a block against its source quote (semantics judged in judge.py)."""

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
NUMBER_RE = re.compile(r"\d[\d,.]*")
# "1년에", "1개월"처럼 원문의 '연회비'·'무이자 할부'를 자연스럽게 풀어 쓸 때 생기는 1 + 단위는
# 지어낸 수치로 보지 않는다. 원문에 있던 수치를 바꾸거나 빼면 '수치 누락' 쪽에서 잡히므로,
# 이 예외가 만드는 구멍은 '원문에 수치가 전혀 없던 기간을 1로 지어내는 경우'로 좁다.
COUNTER_UNITS = ["년", "해", "달", "개월", "회", "번", "명", "곳", "가지", "종류"]
# 짧고 다른 낱말 안에 자주 들어가는 표현("결제일에"의 '제일')은 부분문자열만으로 판단하지 않는다.
AMBIGUOUS_SHORT = {"최고", "최저", "최상", "최초", "최대", "최강", "제일", "유일", "1위"}


def strip_ws(s: str) -> str:
    return "".join(s.split())


def number_set(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in NUMBER_RE.findall(text)}


def counter_ones(text: str) -> set[str]:
    """'1' + 기간·횟수 단위로만 쓰인 1을 모은다. 다른 수치는 건드리지 않는다."""
    if not any(f"1{unit}" in text for unit in COUNTER_UNITS):
        return set()
    return {"1"} if re.search(r"(?<!\d)1(" + "|".join(COUNTER_UNITS) + ")", text) else set()


def has_phrase(text: str, phrase: str) -> bool:
    """단정·최상급 표현이 다른 낱말의 일부가 아니라 실제로 그 표현으로 쓰였는지 본다."""
    if phrase not in AMBIGUOUS_SHORT:
        return strip_ws(phrase) in strip_ws(text)
    spaced = " ".join(text.split())
    for match in re.finditer(re.escape(phrase), spaced):
        before = spaced[match.start() - 1] if match.start() else ""
        if not ("가" <= before <= "힣"):
            return True
    return False


def verify_source_quote(text: str, quote: str) -> str:
    """quote가 실제 입력 텍스트(text)에서 확인되면 빈 문자열, 아니면 이유를 돌려준다."""
    return "" if locate_quote(text, quote) else "source_quote를 원문에서 확인할 수 없음"


def verify_block(quote: str, text: str) -> list[str]:
    """원문 quote 대비 text의 수치·단정·가능성 표현을 기계적으로 대조해 문제 목록을 돌려준다."""
    problems: list[str] = []
    q_nums, t_nums = number_set(quote), number_set(text)
    extra_nums = sorted(t_nums - q_nums - counter_ones(text))
    missing_nums = sorted(q_nums - t_nums)
    if extra_nums:
        problems.append(f"원문에 없는 수치 포함: {', '.join(extra_nums)}")
    if missing_nums:
        problems.append(f"원문 수치 누락: {', '.join(missing_nums)}")

    added_phrases = [
        p for p in FORBIDDEN_ABSOLUTE_PHRASES if has_phrase(text, p) and not has_phrase(quote, p)
    ]
    if added_phrases:
        problems.append(f"원문에 없는 단정·최상급 표현 포함: {', '.join(added_phrases)}")

    q_compact, t_compact = strip_ws(quote), strip_ws(text)
    had_hedge = any(strip_ws(m) in q_compact for m in HEDGE_MARKERS)
    kept_hedge = any(strip_ws(m) in t_compact for m in HEDGE_MARKERS)
    if had_hedge and not kept_hedge:
        problems.append("원문의 가능성·조건 표현이 쉬운말에서 확정 표현으로 바뀜")
    return problems


def verify_terms(quote: str, terms: list[str]) -> list[str]:
    """quote 안에서 실제로 확인되는 용어만 남긴다(근거 없는 용어 풀이 방지)."""
    q_compact = strip_ws(quote)
    return [t for t in terms if strip_ws(t) and strip_ws(t) in q_compact]
