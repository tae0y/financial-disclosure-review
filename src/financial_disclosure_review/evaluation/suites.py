"""The three evaluation suites, each answering one question with counted cases.

| Suite | Question | Gold label comes from |
|---|---|---|
| `classification` | is a real page put in the right product type? | 영태's labels on six pages |
| `duty-flip` | is a disclosure that left the page noticed? | the deletion (true by construction) |
| `plain-contract` | is a rewrite that drifts caught? | the defect written into each pair |
| `stability` | does the same input get the same answer? | the first answer (agreement, no label) |

`duty-flip` also runs an ablation arm — the same rubric items, one call, no quote validation, no
condition step, no retry — so the measured difference is this project's engineering rather than
the model's general ability. `classification` has a keyword-frequency arm for the same reason:
what the three-step judgment adds over counting product words on the page.
"""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from ..core.context import Context
from ..core.text import locate_quote, visible_text
from ..domain.classification import classify_page
from ..domain.classification.schema import PAGE_TYPE_BY_PRODUCT
from ..domain.explanation_duty_check.check import (
    explanation_scope,
    judge_original_side,
    load_explanation_items,
)
from ..domain.plain_language.contract import verify_block, verify_source_quote
from ..domain.plain_language.judge import judge_condition_preservation
from .cassette import Cassette
from .defects import longest_unused_sentence, remove_quote

ABLATION_TASK = """당신은 카드회사 상품광고 페이지 원문(text)이 설명의무 기준(items)을 지켰는지
판단합니다. items의 각 항목마다 verdict(적합/부적합/판정 불가), quote(근거 문장),
reason(짧은 근거)을 답합니다."""


class AblationJudgment(BaseModel):
    code: str
    verdict: Literal["적합", "부적합", "판정 불가"]
    quote: str
    reason: str


class AblationJudgments(BaseModel):
    items: list[AblationJudgment]


# ---------------------------------------------------------------- classification

# The comparison arm: the product words a reader would scan for, counted on the visible text.
# Written from the product definitions (여전법·광고규정 terms), not tuned on the fixtures.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "리볼빙": ("리볼빙", "일부결제금액이월", "결제비율"),
    "장기카드대출": ("카드론", "장기카드대출"),
    "단기카드대출": ("현금서비스", "단기카드대출"),
    "할부금융·리스": ("할부금융", "오토할부", "자동차 할부", "리스"),
    "신용카드": ("신용카드", "연회비", "카드 발급", "카드발급"),
}
OUT_OF_SCOPE_WORDS = ("보험료", "보험금", "특약", "예금", "적금", "만기", "보장")


def keyword_classify(page: dict) -> dict:
    """Most-mentioned product type wins; more out-of-scope words than that means 범위 밖."""
    text = " ".join(
        [(page.get("product") or {}).get("product_name", ""), visible_text(page["html"])]
    )
    counts = {kind: sum(text.count(word) for word in words) for kind, words in KEYWORDS.items()}
    outside = sum(text.count(word) for word in OUT_OF_SCOPE_WORDS)
    best = max(counts, key=lambda kind: counts[kind])
    reason = f"keyword counts {counts}, out-of-scope words {outside}"
    if not counts[best] or outside > counts[best]:
        return {"product_type": "범위 밖", "page_type": None, "reason": reason}
    return {"product_type": best, "page_type": PAGE_TYPE_BY_PRODUCT[best], "reason": reason}


def run_classification(
    ctx: Context, cassette: Cassette, fixtures_dir: str | Path, arm: str = "pipeline"
) -> dict:
    """Six captured pages against 영태's labels. One to three calls per page on the pipeline arm,
    none on the keyword arm."""
    rows = []
    for path in sorted(Path(fixtures_dir).glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        page = {key: fixture[key] for key in ("url", "product", "html")}
        if arm == "keyword":
            result = keyword_classify(page)
        else:
            result = classify_page(page, ctx.model, ask=cassette.ask)
        expected = fixture["expected"]
        rows.append(
            {
                "case": path.stem,
                "expected_product_type": expected["product_type"],
                "actual_product_type": result.get("product_type"),
                "expected_page_type": expected["page_type"],
                "actual_page_type": result.get("page_type"),
                "correct": (
                    result.get("product_type") == expected["product_type"]
                    and result.get("page_type") == expected["page_type"]
                ),
                "reason_given": bool((result.get("reason") or "").strip()),
            }
        )
    name = "classification" if arm == "pipeline" else f"classification/{arm}"
    return {"suite": name, "arm": arm, "rows": rows}


# ---------------------------------------------------------------- duty flip


def _in_scope_items(db_path: str, product_type: str) -> list[dict]:
    return [
        item
        for item in load_explanation_items(db_path)
        if not explanation_scope(item, product_type)
    ]


def _pipeline_verdicts(items: list[dict], text: str, ctx: Context, cassette: Cassette) -> dict:
    return judge_original_side(items, text, ctx.model, cassette.ask)


def _ablation_verdicts(items: list[dict], text: str, ctx: Context, cassette: Cassette) -> dict:
    """One call, answer taken as given: no quote check, no condition step, no retry."""
    evidence = [{"code": i["code"], "criterion": i["criterion"]} for i in items]
    answer = cassette.ask(
        ctx.model, AblationJudgments, ABLATION_TASK, "medium", text=text, items=evidence
    )
    return {row["code"]: {**row, "condition_status": "해당없음"} for row in answer["items"]}


ARMS = {"pipeline": _pipeline_verdicts, "ablation": _ablation_verdicts}


def run_duty_flip(
    ctx: Context, cassette: Cassette, config: dict, arm: str = "pipeline", max_flips: int = 3
) -> dict:
    """Delete one quoted disclosure at a time from a real page and see whether the item flips.

    `rows` holds one row per variant. A variant whose deletion did not really land is marked
    `landed: False` and left out of the rate, rather than counted as a pass or a failure.
    """
    judge = ARMS[arm]
    base_html = Path(config["base_html"]).read_text(encoding="utf-8")
    base_text = visible_text(base_html)
    product_type = config["classification"]["product_type"]
    items = _in_scope_items(ctx.db_path, product_type)
    prefer = tuple(config.get("prefer_codes") or ())

    base = judge(items, base_text, ctx, cassette)
    base_rows = [
        {
            "code": code,
            "verdict": row["verdict"],
            "quote": row["quote"],
            "quote_found": bool(row["quote"]) and locate_quote(base_text, row["quote"]) is not None,
        }
        for code, row in sorted(base.items())
    ]
    passed = [row for row in base_rows if row["verdict"] == "적합" and row["quote_found"]]
    ranked = sorted(passed, key=lambda row: (row["code"] not in prefer, row["code"]))
    targets = ranked[:max_flips]

    rows = []
    for target in targets:
        variant_html, landed = remove_quote(base_html, target["quote"])
        variant_text = visible_text(variant_html)
        row = {
            "case": f"drop-{target['code']}",
            "kind": "결함 주입",
            "code": target["code"],
            "removed_quote": target["quote"][:120],
            "landed": landed,
            "base_verdict": target["verdict"],
        }
        if not landed:
            row.update(after_verdict=None, detected=None, note="삭제가 적용되지 않아 제외")
            rows.append(row)
            continue
        after = judge(items, variant_text, ctx, cassette)
        verdict = (after.get(target["code"]) or {}).get("verdict")
        row.update(
            after_verdict=verdict,
            detected=verdict == "부적합",
            softened=verdict == "판정 불가",
            groundedness=_groundedness(after, variant_text),
            note="",
        )
        rows.append(row)

    neutral_quote = longest_unused_sentence(base_html, [row["quote"] for row in base_rows])
    if neutral_quote:
        variant_html, landed = remove_quote(base_html, neutral_quote)
        row = {
            "case": "neutral-delete",
            "kind": "무관 문장 삭제(대조군)",
            "code": "",
            "removed_quote": neutral_quote[:120],
            "landed": landed,
            "base_verdict": "-",
        }
        if landed:
            variant_text = visible_text(variant_html)
            after = judge(items, variant_text, ctx, cassette)
            flipped = sorted(
                row_["code"]
                for row_ in passed
                if (after.get(row_["code"]) or {}).get("verdict") == "부적합"
            )
            row.update(
                after_verdict=f"{len(flipped)} flipped",
                false_flips=flipped,
                detected=None,
                groundedness=_groundedness(after, variant_text),
                note="적합→부적합으로 바뀐 항목이 없어야 정상",
            )
        else:
            row.update(after_verdict=None, detected=None, note="삭제가 적용되지 않아 제외")
        rows.append(row)

    return {
        "suite": f"duty-flip/{arm}",
        "arm": arm,
        "base": {
            "html": config["base_html"],
            "visible_chars": len(base_text),
            "items_in_scope": len(items),
            "verdicts": _counts(base_rows),
            "passed_with_quote": len(passed),
            "groundedness": _groundedness(base, base_text),
            "rows": [{**row, "quote": row["quote"][:140]} for row in base_rows],
        },
        "rows": rows,
    }


def _counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return counts


def _groundedness(verdicts: dict, text: str) -> dict:
    """Share of quoted judgments whose quote is really in the text it was judged against."""
    quoted = [row for row in verdicts.values() if (row.get("quote") or "").strip()]
    found = [row for row in quoted if locate_quote(text, row["quote"]) is not None]
    return {
        "quoted": len(quoted),
        "found": len(found),
        "rate": round(len(found) / len(quoted), 3) if quoted else None,
    }


# ---------------------------------------------------------------- plain contract


def run_plain_contract(ctx: Context, cassette: Cassette, cases: list[dict]) -> dict:
    """The rewrite contract against pairs whose defect is known.

    Numbers/absolute-phrase/hedge are decidable from the two strings, so those run for free.
    Whether a condition/exception/limit/penalty survived in meaning is not, so a pair that clears
    the mechanical checks goes through `judge_condition_preservation` on `cassette.ask` — one
    model call per case (paid on `--live --record`, free on replay).
    """
    rows = []
    to_judge: list[dict] = []
    for case in cases:
        quote, rewrite = case["source_quote"], case["rewrite"]
        problems = verify_block(quote, rewrite)
        quote_problem = verify_source_quote(case.get("page_text") or quote, quote)
        if quote_problem:
            problems = [quote_problem, *problems]
        row = {
            "case": case["id"],
            "defect": case["defect"],
            "gold_defective": bool(case["defect"]),
            "problems": problems,
            "expect_marker": case.get("expect_marker", ""),
        }
        rows.append(row)
        if not problems:
            to_judge.append({"id": case["id"], "quote": quote, "text": rewrite})

    judgments = judge_condition_preservation(to_judge, ctx.model, cassette.ask) if to_judge else {}
    for row in rows:
        judgment = judgments.get(row["case"])
        if judgment and judgment["verdict"] == "누락 가능":
            row["problems"] = [f"조건·불이익 관련 뜻 누락 가능: {judgment['reason']}"]
        row["flagged"] = bool(row["problems"])
        row["correct"] = row["flagged"] == row["gold_defective"]
        row["marker_hit"] = (
            any(row["expect_marker"] in p for p in row["problems"])
            if row["expect_marker"]
            else None
        )
    return {"suite": "plain-contract", "rows": rows}


# ---------------------------------------------------------------- stability


def run_stability(
    ctx: Context, cassette: Cassette, fixtures_dir: str | Path, config: dict, repeats: int = 3
) -> dict:
    """Ask the same questions `repeats` times and count how often the answer stays the same.

    The first round is the recording the other suites already use (unsalted); rounds 2.. are
    kept apart by a salt. No label is involved: the measure is agreement with itself.
    """
    salts = ["", *[f"repeat-{n}" for n in range(2, repeats + 1)]]
    classification = []
    for path in sorted(Path(fixtures_dir).glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        page = {key: fixture[key] for key in ("url", "product", "html")}
        answers = [
            classify_page(page, ctx.model, ask=cassette.salted(salt)).get("product_type")
            for salt in salts
        ]
        classification.append(
            {"case": path.stem, "answers": answers, "stable": len(set(answers)) == 1}
        )

    base_html = Path(config["base_html"]).read_text(encoding="utf-8")
    base_text = visible_text(base_html)
    items = _in_scope_items(ctx.db_path, config["classification"]["product_type"])
    runs = [
        judge_original_side(items, base_text, ctx.model, cassette.salted(salt)) for salt in salts
    ]
    duty = []
    for item in items:
        verdicts = [(run.get(item["code"]) or {}).get("verdict") for run in runs]
        duty.append({"code": item["code"], "verdicts": verdicts, "stable": len(set(verdicts)) == 1})
    return {
        "suite": "stability",
        "repeats": repeats,
        "base_html": config["base_html"],
        "classification": classification,
        "duty": duty,
    }


def load_cases(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
