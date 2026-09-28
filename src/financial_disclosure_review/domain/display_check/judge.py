"""Entry point of the display_check domain: label the blocks, then judge each rubric item."""

import json
import re
import time
from collections.abc import Mapping
from typing import Any

from ...core.context import Context
from ...core.display_codes import VIOLATION_KEYS
from ...knowledge.rubrics import item_scope, load_rubric
from ...llm.client import ask, ask_images
from .blocks import (
    BLOCK_COLUMNS,
    compact_block,
    display_blocks,
    page_images,
)
from .measures import (
    CONTRAST_MIN,
    CONTRAST_MIN_LARGE,
    LABEL_GROUPS,
    PX_TO_PT,
    display_measures,
    item_blocks,
)
from .prompts import LABEL_TASK, VERDICT_TASK, VISION_READABILITY_TASK
from .schema import DisplayLabels, DisplayVerdicts

# Label groups an item needs before code can measure it. No block in a group -> 판정 불가.
ITEM_NEEDS = {
    "E01": ("benefits", "penalties"),
    "E02": ("mandatory",),
    "E03": ("rates", "warnings"),
    "E04": ("warnings",),
    "E05": ("mandatory",),
    "E06": ("mandatory",),
}
# Items whose verdict follows from the measurements alone; the model never judges them.
CODE_DECIDED = tuple(VIOLATION_KEYS)


def code_verdict(code: str, m: Mapping[str, Any], flagged_images: list[str], legacy: bool) -> dict:
    """적합 only when every labelled block of the item was visible and measured with nothing
    left unresolved; a measured violation is 부적합 citing the violating blocks; anything the
    code could not measure makes a pass unproven, so 판정 불가."""
    violating = m[VIOLATION_KEYS[code]]
    if violating:
        what = "font size below the minimum" if code == "E02" else "contrast below the minimum"
        return {
            "verdict": "부적합",
            "block_ids": list(violating),
            "reason": f"measured {what}: {violating} ({VIOLATION_KEYS[code]})",
        }
    unknown = []
    if m["measured"] < m["blocks"]:
        unknown.append(f"{m['blocks'] - m['measured']} labelled block(s) never visible")
    if code == "E02" and m["size_unmeasured"]:
        unknown.append(f"size not drawn as text: {m['size_unmeasured']}")
    if code in ("E04", "E05"):
        if legacy:
            unknown.append("legacy snapshot without rendered-crop capture; rerun preprocess")
        if m["visual_unresolved"]:
            unknown.append(f"image-backed text without a readable crop: {m['visual_unresolved']}")
        if m["contrast_unmeasured"]:
            unknown.append(f"contrast unmeasured: {m['contrast_unmeasured']}")
    if flagged_images:
        unknown.append(f"disclosure text inside image(s) {flagged_images}")
    if unknown or not m["measured"]:
        return {
            "verdict": "판정 불가",
            "block_ids": [],
            "reason": "a pass would be unproven: " + "; ".join(unknown or ["nothing measured"]),
        }
    cited = m["min_pt_block"] if code == "E02" else m["min_contrast_block"]
    value = f"min {m['min_pt']}pt" if code == "E02" else f"min contrast {m['min_contrast']}"
    return {
        "verdict": "적합",
        "block_ids": [cited] if cited else [],
        "reason": f"all {m['measured']} labelled block(s) measured within the threshold ({value})",
    }


def call_model(
    ctx: Context,
    log: list[dict],
    step: str,
    schema,
    task: str,
    check,
    effort: str,
    salvage=None,
    ask_fn=None,
    **data,
) -> dict:
    """One model step: at most 2 logged attempts, then salvage(answer, problems) or raise."""
    problems: list[str] = []
    answer: dict = {}
    for attempt in (1, 2):
        if problems:
            data = {**data, "previous_problems": problems}
        if len(log) >= ctx.display_max_model_calls:
            raise RuntimeError(
                f"model call cap of {ctx.display_max_model_calls} reached before {step}"
            )
        entry = {"step": step, "attempt": attempt, "ok": False, "error": ""}
        log.append(entry)
        started = time.time()
        invalid = False
        try:
            answer = (ask_fn or ask)(ctx.model, schema, task, effort, **data)
            problems = check(answer)
            invalid = bool(problems)
            entry["ok"] = not problems
            entry["error"] = "; ".join(problems)[:300]
        except Exception as error:
            problems = [f"{type(error).__name__}: {error}"]
            entry["error"] = problems[0][:300]
        entry["seconds"] = round(time.time() - started, 1)
        head = f"    call {len(log)}/{ctx.display_max_model_calls} {step} attempt {attempt}"
        print(f"{head}: {'ok' if entry['ok'] else 'FAILED ' + entry['error']}")
        if entry["ok"]:
            return answer
    if salvage and invalid:
        return salvage(answer, problems)
    raise RuntimeError(f"{step} failed twice: {'; '.join(problems)[:400]}")


def judge_visual_readability(
    blocks: list[dict], labels: dict, ctx: Context, log: list[dict]
) -> dict:
    """One capped image call. Unknown or missing images stay unresolved, never an inferred pass."""
    relevant = set(labels["mandatory"]) | set(labels["warnings"])
    risky = [
        b for b in blocks if b["id"] in relevant and b["ever_visible"] and b.get("visual_risk")
    ]
    selected = [b for b in risky if b.get("visual_png")][: ctx.display_max_visual_crops]
    selected_ids = {b["id"] for b in selected}
    result = {
        "candidate_ids": [b["id"] for b in risky],
        "sampled_ids": [b["id"] for b in selected],
        "unresolved_ids": [b["id"] for b in risky if b["id"] not in selected_ids],
        "readable": {},
    }
    if not selected:
        return result
    if len(log) >= ctx.display_max_model_calls:
        result["unresolved_ids"] = result["candidate_ids"]
        result["error"] = "model call cap reached before vision"
        return result
    prompt = VISION_READABILITY_TASK + chr(10) + "ids=" + ", ".join(b["id"] for b in selected)
    entry = {
        "step": "vision_readability",
        "attempt": 1,
        "ok": False,
        "image_count": len(selected),
        "error": "",
    }
    log.append(entry)
    started = time.time()
    try:
        text, usage = ask_images(ctx.model, prompt, [b["visual_png"] for b in selected])
        answer = json.loads(text)
        if set(answer) != selected_ids or any(type(answer[i]) is not bool for i in selected_ids):
            raise ValueError("vision answer must map every sampled block id to a boolean")
        result["readable"] = answer
        entry["ok"] = True
        entry["usage"] = usage
    except Exception as error:
        result["unresolved_ids"] = result["candidate_ids"]
        result["error"] = f"{type(error).__name__}: {error}"[:300]
        entry["error"] = result["error"]
    entry["seconds"] = round(time.time() - started, 1)
    return result


def judge_display(
    page: Mapping[str, Any], classification: Mapping[str, Any], ctx: Context, ask_fn=None
) -> dict:
    """Display-method judgment of one page; returns the DisplayCheck fields items and judgments."""
    items = load_rubric(ctx.db_path, "card_guardrail_rubric")
    group = [i for i in items if i["group"].startswith("E.")]
    applied, skipped = [], []
    for item in group:
        why = item_scope(item, classification)
        (skipped if why else applied).append({"code": item["code"], "reason": why} if why else item)
    log: list[dict] = []
    judgments: dict[str, Any] = {"model_calls": log, "skipped": skipped}

    def unjudgeable(reason: str) -> dict:
        rows = [
            {
                "code": i["code"],
                "verdict": "판정 불가",
                "block_ids": [],
                "quotes": [],
                "measured": [],
                "reason": reason,
            }
            for i in applied
        ]
        return {"items": rows, "judgments": {**judgments, "status": "판정 불가", "reason": reason}}

    blocks, mapping = display_blocks(page)
    if not blocks:
        return unjudgeable("no snapshot text block could be mapped to the html; nothing measurable")
    images = page_images(page.get("html"))
    hidden_ids = [b["id"] for b in blocks if not b["default_visible"]]
    match = re.search(
        r"(\d+)\s*포인트", next((i["criterion"] for i in group if i["code"] == "E02"), "")
    )
    min_pt = float(match.group(1)) if match else None
    assumptions = {
        "font_size": (
            f"E02 says {min_pt:g}pt on A4. A web page has no paper size, so the node uses"
            f" computed CSS px x {PX_TO_PT} >= {min_pt:g}pt at the captured viewport."
        ),
        "contrast": (
            f"No threshold in the rubric. The node uses the WCAG 2.1 SC 1.4.3 AA ratio:"
            f" {CONTRAST_MIN}:1 for normal text, {CONTRAST_MIN_LARGE}:1 for large text"
            " (>= 24px, or >= 18.66px and weight >= 700). Text and background colors come from"
            " the snapshot (blended background when captured); Image-backed blocks are checked"
            " from saved rendered crops; an uncertain crop cannot prove a pass or failure."
        ),
        "hidden": (
            "Hidden by default = not visible in the default snapshot of the final render;"
            " revealed = visible in a later snapshot of that visit."
        ),
        "line_break": (
            "A block is 'alone on its line' when its text is a whole line of the html split"
            " at block elements and <br>."
        ),
        "vision": (
            "For image-backed text in E04/E05, a saved rendered crop overrides the flat-color"
            " DOM contrast proxy. Missing or failed crops cannot establish a pass."
        ),
    }
    judgments.update({"assumptions": assumptions, "mapping": mapping, "images": len(images)})

    mandatory_items = [
        {"code": i["code"], "criterion": i["criterion"]}
        for i in items
        if i["group"][0] in "ABC" and not item_scope(i, classification)
    ]
    by_id = {b["id"]: b for b in blocks}
    known = set(by_id) | {i["id"] for i in images}

    def check_labels(answer: dict) -> list[str]:
        problems = [
            f"{g}: unknown id {i}" for g in LABEL_GROUPS for i in answer[g] if i not in known
        ]
        return problems + [
            f"image_disclosure: unknown id {f['id']}"
            for f in answer["image_disclosure"]
            if f["id"] not in known
        ]

    labels = call_model(
        ctx,
        log,
        "label_blocks",
        DisplayLabels,
        LABEL_TASK,
        check_labels,
        "medium",
        ask_fn=ask_fn,
        columns=BLOCK_COLUMNS,
        blocks=[compact_block(b) for b in blocks],
        mandatory_items=mandatory_items,
        images=images,
    )
    # An image counts as disclosure text only if its alt names a disclosure topic from the
    # mandatory items.
    vocabulary = " ".join(i["criterion"] for i in mandatory_items)
    alt_of = {i["id"]: i["alt"] for i in images}
    flags = [f for f in labels["image_disclosure"] if f["id"] in alt_of]
    kept = [
        f
        for f in flags
        if len(f["alt_phrase"]) >= 3
        and f["alt_phrase"] in alt_of[f["id"]]
        and f["alt_phrase"] in vocabulary
    ]
    labels["dropped_image_flags"] = [f for f in flags if f not in kept]
    labels["image_disclosure"] = [f["id"] for f in kept]
    judgments["labels"] = labels
    vision = judge_visual_readability(blocks, labels, ctx, log)
    legacy_visual_capture = any(
        s.get("phase") == "render" and "visual_samples" not in s for s in page["snapshots"]
    )
    vision["legacy_capture"] = legacy_visual_capture
    judgments["vision"] = vision
    for block in blocks:
        if block["id"] in vision["readable"]:
            block["vision_readable"] = vision["readable"][block["id"]]
    # Keep image bytes in product_page only; do not duplicate them in the evidence table.
    judgments["blocks"] = [{k: v for k, v in b.items() if k != "visual_png"} for b in blocks]
    measures = display_measures(
        blocks, labels, min_pt, hidden_ids, mapping, page.get("actions") or []
    )
    judgments["measures"] = measures

    flagged_images = labels["image_disclosure"]
    ready, by_code, decided = [], {}, {}
    for item in applied:
        code = item["code"]
        missing = [g for g in ITEM_NEEDS.get(code, ()) if not labels[g]]
        if missing:
            by_code[code] = (
                f"the model found no block in {', '.join(missing)},"
                " so there is nothing to measure for this item"
            )
        elif code in CODE_DECIDED:
            decided[code] = code_verdict(
                code, measures[code], flagged_images, legacy_visual_capture
            )
        else:
            ready.append(item)
    judgments["code_decided"] = sorted(decided)

    verdicts = {}
    if ready:
        evidence = {
            i["code"]: {
                "criterion": i["criterion"],
                "measures": (
                    {k: v for k, v in measures[i["code"]].items() if k != "dom_below_contrast_min"}
                    if i["code"] in ("E04", "E05")
                    else measures.get(i["code"])
                ),
                "blocks": [
                    compact_block(b) for b in item_blocks(i["code"], blocks, labels, hidden_ids)
                ],
            }
            for i in ready
        }
        wanted = {i["code"] for i in ready}

        def check_verdicts(answer: dict) -> list[str]:
            problems, seen = [], [v["code"] for v in answer["items"]]
            if sorted(seen) != sorted(wanted):
                problems.append(f"codes {sorted(seen)} do not match {sorted(wanted)}")
            for v in answer["items"]:
                if not v["reason"].strip():
                    problems.append(f"{v['code']}: empty reason")
                if v["verdict"] != "판정 불가" and not v["block_ids"]:
                    problems.append(f"{v['code']}: verdict without block ids")
                problems += [
                    f"{v['code']}: unknown id {i}" for i in v["block_ids"] if i not in known
                ]
                if v["code"] == "E07" and v["verdict"] == "부적합":
                    if not any(by_id[i]["revealed_by"] for i in v["block_ids"] if i in by_id):
                        problems.append(
                            "E07 부적합 must cite a block revealed by a user action (D flag);"
                            " H blocks alone prove nothing"
                        )
                key = VIOLATION_KEYS.get(v["code"])
                if key:
                    violating = measures[v["code"]][key]
                    if v["verdict"] == "적합" and violating:
                        problems.append(
                            f"{v['code']} 적합 contradicts measured violations {violating}"
                        )
                    if v["verdict"] == "부적합" and not set(violating) & set(v["block_ids"]):
                        problems.append(
                            f"{v['code']} 부적합 must cite a block that violates the"
                            f" threshold ({key}={violating})"
                        )
            return problems

        def salvage_verdicts(answer: dict, problems: list[str]) -> dict:
            """Downgrade only the items whose verdict failed validation; structural ones raise."""
            bad = {p.split(":")[0].split(" ")[0] for p in problems}
            if not bad <= wanted:
                raise RuntimeError(f"judge_items failed twice: {'; '.join(problems)[:400]}")
            note = "; ".join(problems)[:200]
            return {
                "items": [
                    {
                        **v,
                        "verdict": "판정 불가",
                        "reason": f"model verdict failed validation twice ({note}); it is not used",
                    }
                    if v["code"] in bad
                    else v
                    for v in answer["items"]
                ]
            }

        answer = call_model(
            ctx,
            log,
            "judge_items",
            DisplayVerdicts,
            VERDICT_TASK,
            check_verdicts,
            "medium",
            salvage_verdicts,
            ask_fn=ask_fn,
            columns=BLOCK_COLUMNS,
            assumptions=assumptions,
            items=evidence,
        )
        verdicts = {v["code"]: v for v in answer["items"]}

    rows = []
    for item in applied:
        code = item["code"]
        v = (
            decided.get(code)
            or verdicts.get(code)
            or {
                "verdict": "판정 불가",
                "block_ids": [],
                "reason": by_code.get(code, "not judged"),
            }
        )
        verdict, reason = v["verdict"], v["reason"]
        if code in ("E04", "E05") and legacy_visual_capture:
            verdict = "판정 불가"
            reason = (
                "legacy snapshot has no image-overlap or rendered-crop capture; rerun preprocess"
            )
        if verdict == "적합" and code in ("E04", "E05") and measures[code]["visual_unresolved"]:
            verdict = "판정 불가"
            reason = (
                f"rendered image evidence is missing for"
                f" {measures[code]['visual_unresolved']}; a pass would be unproven."
                f" Model reason: {reason}"
            )
        if verdict == "적합" and code == "E02" and measures[code]["size_unmeasured"]:
            verdict = "판정 불가"
            reason = (
                f"text of {measures[code]['size_unmeasured']} is not drawn as text (font-size"
                " below 1px, usually a picture of the words), so its size cannot be measured"
                f" and a pass would be unproven. Model reason: {reason}"
            )
        if verdict == "적합" and flagged_images and code != "E07":
            verdict = "판정 불가"
            reason = (
                f"text inside image(s) {flagged_images} cannot be measured, so a pass would be"
                f" unproven. Model reason: {reason}"
            )
        cited = [by_id[i] for i in v["block_ids"] if i in by_id]
        rows.append(
            {
                "code": code,
                "verdict": verdict,
                "block_ids": [b["id"] for b in cited],
                "quotes": [b["text"] for b in cited],
                "measured": [
                    {
                        k: b[k]
                        for k in (
                            "id",
                            "px",
                            "pt",
                            "weight",
                            "color",
                            "background",
                            "contrast",
                            "bounds",
                            "default_visible",
                            "revealed_by",
                        )
                    }
                    for b in cited
                ],
                "reason": reason,
            }
        )
    judgments["status"] = "완료"
    judgments["limits"] = {
        "images": (
            f"{len(images)} images in the selected html,"
            f" {sum(not i['alt'] for i in images)} without alt text; text inside images is not"
            f" measurable. Flagged by the model: {flagged_images or 'none'}"
        ),
        "backgrounds": (
            "CSS background images and overlapping img bounds flag risky blocks; captured crops"
            " are checked by vision for E04/E05. Pseudo-elements and image-only text remain"
            " unmeasured."
        ),
    }
    return {"items": rows, "judgments": judgments}
