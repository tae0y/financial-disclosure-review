"""Verify every quote in card_guardrail_rubric.yaml against the source snapshots, then render
the reference sheet `01 사람 대조표.md`.

A quote passes when it appears in `원문 스냅샷/<doc>.txt` after removing whitespace and
unifying middle-dot and quotation-mark variants. When `loc` names an article (제N조...) or
an appendix (별표N), the nearest article/appendix heading above the matched text must agree.

This is a pure render: the schema is flat lookup data (no decisions, no draft/adopt workflow),
so there is nothing for a human to check off and nothing to preserve across re-renders.

    uv run --no-project --with pyyaml python tools/verify_and_render.py
"""

from __future__ import annotations

import re
import sys
from bisect import bisect_right
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "원문 스냅샷"
RUBRIC = ROOT / "card_guardrail_rubric.yaml"
SHEET = ROOT / "01 사람 대조표.md"

DOCS = {
    "kfcpa": ("금소법", "법률"),
    "kfcpa_decree": ("금소법 시행령", "대통령령"),
    "fsc_rule": ("금소법 감독규정", "금융위 고시"),
    "fsc_rule_app5": ("감독규정 별표 5", "금융위 고시"),
    "yeojeon": ("여전법", "법률"),
    "yeojeon_decree": ("여전법 시행령", "대통령령"),
    "crefia_reg": ("협회 광고규정", "협회 자율규제"),
    "crefia_guide": ("협회 광고규정 세부지침", "협회 자율규제"),
    "fsc_ad_guideline": ("금융광고규제 가이드라인", "금융위·금감원 가이드라인"),
    "fsc_online_explain": ("온라인 설명의무 가이드라인", "금융위 가이드라인"),
    "fsc_explain": ("설명의무 가이드라인", "금융위 가이드라인"),
    # Used by plain_service_rubric.yaml (render_plain_service.py).
    "ai_act": ("인공지능기본법", "법률"),
    "ai_act_decree": ("인공지능기본법 시행령", "대통령령"),
    "fsc_ai_guideline": ("금융분야 AI 가이드라인", "금융위 가이드라인"),
    "nikl_public_lang": ("국립국어원 공공언어 바로 쓰기", "참고(공공기관 기준)"),
    "yeojeon_rule": ("여신전문금융업감독규정", "금융위 고시"),
    "yeojeon_decree_app13": ("여전법 시행령 별표 1의3", "대통령령"),
}
ARTICLE_DOCS = {"kfcpa", "kfcpa_decree", "fsc_rule", "yeojeon", "yeojeon_decree", "yeojeon_rule", "crefia_reg", "crefia_guide", "ai_act", "ai_act_decree"}
ART_HEAD = re.compile(r"^\s*(제\d+조(?:의\d+)?)\(")
APP_HEAD = re.compile(r"\[세부지침 (별표\d+)\]")
_TRANS = str.maketrans({c: "·" for c in "ㆍ·‧∙・․"} | {c: '"' for c in "“”″"} | {c: "'" for c in "‘’"})


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s.translate(_TRANS))


class Snapshot:
    def __init__(self, sid: str):
        raw = (SNAP / f"{sid}.txt").read_text(encoding="utf-8").splitlines()
        self.lines = raw
        self.text, self.starts, self.heads = "", [], []  # heads: (norm_pos, label)
        buf = []
        pos = 0
        for i, ln in enumerate(raw, start=1):
            if ln.startswith("#"):
                continue
            n = norm(ln)
            self.starts.append((pos, i))
            m = ART_HEAD.match(ln)
            if m:
                self.heads.append((pos, m.group(1)))
            for a in APP_HEAD.findall(ln):
                self.heads.append((pos, a))
            buf.append(n)
            pos += len(n)
        self.text = "".join(buf)
        self._keys = [p for p, _ in self.starts]

    def line_of(self, npos: int) -> int:
        return self.starts[bisect_right(self._keys, npos) - 1][1]

    def head_before(self, npos: int, want_app: bool) -> str | None:
        label = None
        for p, lab in self.heads:
            if p > npos:
                break
            if lab.startswith("별표") == want_app:
                label = lab
        return label


SNAPS: dict[str, Snapshot] = {}


def snap(sid: str) -> Snapshot:
    if sid not in SNAPS:
        SNAPS[sid] = Snapshot(sid)
    return SNAPS[sid]


def check_quote(doc: str, loc: str | None, quote: str) -> dict:
    s = snap(doc)
    q = norm(quote)
    hits = [m.start() for m in re.finditer(re.escape(q), s.text)] if q else []
    if not hits:
        return {"ok": False, "why": "스냅샷에 문구 없음", "line": None, "hits": 0}
    want = None
    if doc in ARTICLE_DOCS and loc:
        m = re.match(r"(제\d+조(?:의\d+)?)", loc)
        a = re.match(r"(별표\d+)", loc)
        want = (m.group(1), False) if m else ((a.group(1), True) if a else None)
    if want is None:
        return {"ok": True, "why": "문구 일치(위치 확인 대상 아님)", "line": s.line_of(hits[0]), "hits": len(hits)}
    for h in hits:
        if s.head_before(h, want[1]) == want[0]:
            return {"ok": True, "why": f"문구 일치 · {want[0]} 안에 있음", "line": s.line_of(h), "hits": len(hits)}
    found = s.head_before(hits[0], want[1])
    return {"ok": False, "why": f"문구는 있으나 {found or '알 수 없는 위치'}에 있음(기대: {want[0]})", "line": s.line_of(hits[0]), "hits": len(hits)}


def quote_block(src: dict, res: dict) -> list[str]:
    name, tier = DOCS[src["doc"]]
    mark = "✅" if res["ok"] else "❌"
    where = f"[{Path(src['snapshot']).name}](<{src['snapshot']}>) {res['line']}행" if res["line"] else Path(src["snapshot"]).name
    head = f"> [!quote] {name} {src.get('loc', '')} · {tier}"
    return [head, f"> {src['quote']}", "> ", f"> {mark} {res['why']} · {where} · [공식 출처]({src['official_url']})", ""]


def verify_items(items: list[dict]) -> tuple[dict[str, list[dict]], list[str], int]:
    failures: list[str] = []
    n_quotes = 0
    item_res: dict[str, list[dict]] = {}
    for it in items:
        results = [check_quote(s["doc"], s.get("loc"), s["quote"]) for s in it["sources"]]
        item_res[it["code"]] = results
        n_quotes += len(results)
        for s, r in zip(it["sources"], results):
            if not r["ok"]:
                failures.append(f"{it['code']} {s['doc']} {s.get('loc')}: {r['why']} :: {s['quote'][:40]}")
    return item_res, failures, n_quotes


def scope_line(it: dict) -> str:
    where = it.get("page_types") or it.get("targets") or []
    line = f"[{it['binding']}] {' · '.join(it['applies_to'])} / {' · '.join(where)}"
    if it.get("applies_condition"):
        line += f" (조건: {it['applies_condition']})"
    return line


def render(rubric_path: Path, sheet_path: Path, h1: str, script_name: str) -> int:
    data = yaml.safe_load(rubric_path.read_text(encoding="utf-8"))
    items = data["items"]
    item_res, failures, n_quotes = verify_items(items)

    used_docs = []
    for it in items:
        for s in it["sources"]:
            if s["doc"] not in used_docs:
                used_docs.append(s["doc"])

    out: list[str] = [
        "---",
        "ai-generated: true",
        "human-review: false",
        "created: 2026-09-26",
        "---",
        "",
        f"# {h1}",
        "",
        f"> [!info] 이 파일은 `{rubric_path.name}`에서 생성합니다. YAML을 고친 뒤 `uv run --no-project --with pyyaml python tools/{script_name}`를 다시 실행해 주세요.",
        "",
        "## 자동 확인 결과",
        "",
        f"- 인용 문구 {n_quotes}개 중 {n_quotes - len(failures)}개가 원문 스냅샷과 일치합니다(공백·가운뎃점·따옴표 모양만 통일해 비교).",
        "- 자동 확인은 **문구가 스냅샷에 있고, 적어 둔 조(또는 별표) 안에 있는지**까지만 봅니다. 항·호·목 번호나 적용 범위 해석은 사람이 판단해야 합니다.",
    ]
    if failures:
        out += ["", "> [!warning] 확인 실패", *[f"> - {f}" for f in failures]]

    out += ["", "## 항목 목록", ""]
    group = None
    for it in items:
        if it["group"] != group:
            group = it["group"]
            out += [f"## {group}", ""]
        ok = all(r["ok"] for r in item_res[it["code"]])
        out += [f"### {it['code']}", "", f"{'✅' if ok else '❌'} {scope_line(it)}", "", f"**판단기준:** {it['criterion']}", ""]
        for s, r in zip(it["sources"], item_res[it["code"]]):
            out += quote_block(s, r)

    out += ["## 원문 목록", "", "인용에 쓰인 문서만 처음 등장한 순서로 나열합니다.", "", "| 원문 | 효력 | 스냅샷 | 공식 출처 |", "| --- | --- | --- | --- |"]
    doc_meta: dict[str, tuple[str, str]] = {}
    for it in items:
        for s in it["sources"]:
            doc_meta.setdefault(s["doc"], (s["snapshot"], s["official_url"]))
    for doc in used_docs:
        name, tier = DOCS[doc]
        snap_path, url = doc_meta[doc]
        out.append(f"| {name} | {tier} | [{Path(snap_path).name}](<{snap_path}>) | [링크]({url}) |")
    out.append("")

    sheet_path.write_text("\n".join(out), encoding="utf-8")
    print(f"{sheet_path.name}: items={len(items)} quotes={n_quotes} failures={len(failures)}")
    for f in failures:
        print("  FAIL", f)
    return 1 if failures else 0


def main() -> int:
    return render(RUBRIC, SHEET, "카드사 광고 가드레일 루브릭", "verify_and_render.py")


if __name__ == "__main__":
    sys.exit(main())
