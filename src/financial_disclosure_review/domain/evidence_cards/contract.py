"""Mechanical (code, never the model) validation of one candidate card against its source."""

from ...core.text import locate_quote
from .schema import EVIDENCE_KINDS


def validate_candidate(item: dict, sources_by_id: dict[str, dict]) -> list[str]:
    """candidate가 원문에서 확인되면 빈 목록, 아니면 이유 목록을 돌려준다."""
    problems: list[str] = []
    if item.get("kind") not in EVIDENCE_KINDS:
        problems.append(f"알 수 없는 kind: {item.get('kind')}")

    source_id = item.get("source_id")
    source = sources_by_id.get(source_id) if isinstance(source_id, str) else None
    if source is None:
        problems.append(f"source_id를 찾을 수 없음: {source_id}")
        return problems  # quote/qualifiers/numbers는 출처가 있어야 대조할 수 있음

    quote = item.get("quote") or ""
    if locate_quote(source["text"], quote) is None:
        problems.append("quote를 해당 source에서 확인할 수 없음")
        return problems  # quote 자체가 근거 없으면 그 안의 세부 항목도 대조할 수 없음

    for number in item.get("numbers") or []:
        if locate_quote(quote, number) is None:
            problems.append(f"quote에 없는 수치: {number}")
    for qualifier in item.get("qualifiers") or []:
        if locate_quote(quote, qualifier) is None:
            problems.append(f"quote에 없는 qualifier: {qualifier}")
    for exception in item.get("exceptions") or []:
        if locate_quote(quote, exception) is None:
            problems.append(f"quote에 없는 exception: {exception}")
    return problems
