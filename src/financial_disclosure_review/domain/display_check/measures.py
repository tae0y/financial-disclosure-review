"""Numbers over the measured blocks. The model never computes these."""

from collections import Counter, defaultdict

PX_TO_PT = 0.75
CONTRAST_MIN = 4.5
CONTRAST_MIN_LARGE = 3.0
LABEL_GROUPS = ("mandatory", "warnings", "rates", "benefits", "penalties")
# Label groups whose blocks are shown to the model for an item; an unlisted item gets
# every labeled block.
ITEM_BLOCKS = {
    "E01": ("benefits", "penalties"),
    "E02": ("mandatory", "warnings"),
    "E03": ("rates", "warnings"),
    "E04": ("warnings",),
    "E05": ("mandatory", "warnings"),
    "E06": ("mandatory", "warnings"),
    "E08": ("rates", "benefits", "penalties"),
}
MAX_EVIDENCE_BLOCKS = 60


def baseline_style(blocks: list[dict]) -> dict:
    """Most common weight, text color and background by characters of visible text."""
    weight, color, background = defaultdict(int), defaultdict(int), defaultdict(int)
    for block in blocks:
        if block["ever_visible"]:
            size = len(block["text"])
            weight[block["weight"]] += size
            color[block["color"]] += size
            background[block["background"]] += size

    def top(counts: dict):
        return max(counts, key=lambda key: counts[key]) if counts else None

    return {"weight": top(weight), "color": top(color), "background": top(background)}


def group_measures(blocks: list[dict], ids: list[str], min_pt: float | None) -> dict:
    """Numbers over the visible blocks of one label group; the model never computes these."""
    rows = [b for b in blocks if b["id"] in ids and b["ever_visible"]]
    contrasts = [b for b in rows if b["contrast"] is not None and not b.get("visual_risk")]
    weak = [
        b["id"]
        for b in rows
        if not b.get("visual_risk")
        and b["contrast"] is not None
        and b["contrast"] < (CONTRAST_MIN_LARGE if b["large_text"] else CONTRAST_MIN)
    ]
    visual_unresolved = [
        b["id"] for b in rows if b.get("visual_risk") and b.get("vision_readable") is not True
    ]
    return {
        "blocks": len(ids),
        "measured": len(rows),
        "min_pt": min((b["pt"] for b in rows if b["pt"] is not None), default=None),
        "max_pt": max((b["pt"] for b in rows if b["pt"] is not None), default=None),
        "min_pt_block": min(
            (b for b in rows if b["pt"] is not None), key=lambda b: b["pt"], default={}
        ).get("id"),
        "min_contrast_block": min(contrasts, key=lambda b: b["contrast"], default={}).get("id"),
        "below_min_pt": [
            b["id"] for b in rows if min_pt and b["pt"] is not None and b["pt"] < min_pt
        ],
        "min_contrast": min((b["contrast"] for b in contrasts), default=None),
        "below_contrast_min": weak,
        "contrast_unmeasured": [
            b["id"] for b in rows if b["contrast"] is None or b["id"] in visual_unresolved
        ],
        "visual_unresolved": visual_unresolved,
        "size_unmeasured": [b["id"] for b in rows if b.get("size_unmeasured")],
        "vision_readable": [b["id"] for b in rows if b.get("vision_readable") is True],
        "dom_below_contrast_min": [
            b["id"]
            for b in rows
            if b["contrast"] is not None
            and b["contrast"] < (CONTRAST_MIN_LARGE if b["large_text"] else CONTRAST_MIN)
        ],
        "weights": sorted({b["weight"] for b in rows if b["weight"] is not None}),
        "colors": sorted({b["color"] for b in rows if b["color"]}),
    }


def display_measures(
    blocks: list[dict],
    labels: dict,
    min_pt: float | None,
    hidden_ids: list[str],
    mapping: dict,
    actions: list[dict],
) -> dict:
    base = baseline_style(blocks)
    by_id = {b["id"]: b for b in blocks}

    def stats(*groups: str) -> dict:
        return group_measures(blocks, sorted({i for g in groups for i in labels[g]}), min_pt)

    set_off = [
        {
            "id": i,
            "bolder": (by_id[i]["weight"] or 400) > (base["weight"] or 400),
            "other_background": by_id[i]["background"] != base["background"],
            "other_color": by_id[i]["color"] != base["color"],
        }
        for i in sorted(set(labels["rates"]) | set(labels["warnings"]))
        if i in by_id and by_id[i]["ever_visible"]
    ]
    mandatory = [by_id[i] for i in labels["mandatory"] if i in by_id and by_id[i]["ever_visible"]]
    return {
        "baseline": base,
        "E01": {"benefits": stats("benefits"), "penalties": stats("penalties")},
        "E02": stats("mandatory", "warnings"),
        "E03": {"baseline": base, "set_off": set_off},
        "E04": stats("warnings"),
        "E05": stats("mandatory", "warnings"),
        "E06": {
            "mandatory_blocks": len(mandatory),
            "with_marker": sum(b["marker"] for b in mandatory),
            "alone_on_line": sum(b["own_line"] for b in mandatory),
            "in_multi_sentence_line": [
                b["id"] for b in mandatory if b["line_sentences"] >= 3 and not b["marker"]
            ],
            "unseparated": [b["id"] for b in mandatory if not b["marker"] and not b["own_line"]],
        },
        "E08": {
            "rate_blocks": len(labels["rates"]),
            "benefit_blocks": len(labels["benefits"]),
            "penalty_blocks": len(labels["penalties"]),
        },
        "E07": {
            "hidden_labeled": [i for i in hidden_ids if any(i in labels[g] for g in LABEL_GROUPS)],
            "hidden_total": len(hidden_ids),
            "states_captured": mapping["states"],
            "action_log": dict(Counter(a["type"] for a in actions)),
            "revealed_by_action": [
                {"id": b["id"], "action": b["revealed_by"]} for b in blocks if b["revealed_by"]
            ][:10],
        },
    }


def item_blocks(code: str, blocks: list[dict], labels: dict, hidden_ids: list[str]) -> list[dict]:
    by_id = {b["id"]: b for b in blocks}
    if code == "E07":
        ids = [i for i in hidden_ids if any(i in labels[g] for g in LABEL_GROUPS)]
        ids += [i for i in hidden_ids if i not in ids and len(by_id[i]["text"]) >= 30]
    else:
        groups = ITEM_BLOCKS.get(code, LABEL_GROUPS)
        ids = [b["id"] for b in blocks if any(b["id"] in labels[g] for g in groups)]
    return [by_id[i] for i in ids[:MAX_EVIDENCE_BLOCKS]]
