"""Turning suite rows into the few numbers the evaluation reports.

Counts come first and rates second, always with their denominator, because a rate over four cases
and a rate over four hundred read the same otherwise.
"""

from typing import Any


def rate(hit: int, total: int) -> float | None:
    return round(hit / total, 3) if total else None


def classification_metrics(result: dict) -> dict:
    rows = result["rows"]
    correct = [row for row in rows if row["correct"]]
    return {
        "cases": len(rows),
        "correct": len(correct),
        "accuracy": rate(len(correct), len(rows)),
        "reason_given": sum(1 for row in rows if row["reason_given"]),
        "wrong": [row["case"] for row in rows if not row["correct"]],
    }


def duty_flip_metrics(result: dict) -> dict:
    rows = result["rows"]
    injected = [row for row in rows if row["kind"] == "결함 주입" and row["landed"]]
    detected = [row for row in injected if row.get("detected")]
    softened = [row for row in injected if row.get("softened")]
    skipped = [row for row in rows if not row["landed"]]
    neutral = next((row for row in rows if row["case"] == "neutral-delete"), None)
    grounded = [row.get("groundedness") or {} for row in rows if row.get("groundedness")]
    quoted = sum(g.get("quoted", 0) for g in grounded)
    found = sum(g.get("found", 0) for g in grounded)
    return {
        "injected": len(injected),
        "detected": len(detected),
        "detection_rate": rate(len(detected), len(injected)),
        "softened_to_unjudged": len(softened),
        "missed": [row["code"] for row in injected if not row.get("detected")],
        # A variant the arm could not judge at all counts as missed above and is named here too.
        "failed": [row["case"] for row in rows if row.get("failed")],
        "skipped_variants": [row["case"] for row in skipped],
        "false_flips": (neutral or {}).get("false_flips") or [],
        "quote_groundedness": {"quoted": quoted, "found": found, "rate": rate(found, quoted)},
        "base_verdicts": result["base"]["verdicts"],
        "base_groundedness": result["base"]["groundedness"],
    }


def plain_contract_metrics(result: dict) -> dict:
    rows = result["rows"]
    defective = [row for row in rows if row["gold_defective"]]
    clean = [row for row in rows if not row["gold_defective"]]
    caught = [row for row in defective if row["flagged"]]
    false_alarms = [row for row in clean if row["flagged"]]
    by_defect: dict[str, dict] = {}
    for row in defective:
        entry = by_defect.setdefault(row["defect"], {"cases": 0, "caught": 0, "marker_hit": 0})
        entry["cases"] += 1
        entry["caught"] += int(row["flagged"])
        entry["marker_hit"] += int(bool(row["marker_hit"]))
    return {
        "cases": len(rows),
        "defective": len(defective),
        "caught": len(caught),
        "recall": rate(len(caught), len(defective)),
        "clean": len(clean),
        "false_alarms": len(false_alarms),
        "false_alarm_rate": rate(len(false_alarms), len(clean)),
        "missed": [row["case"] for row in defective if not row["flagged"]],
        "by_defect": by_defect,
    }


def _duty_agreement(duty: list[dict]) -> dict:
    stable = [row for row in duty if row["stable"]]
    return {
        "duty_items": len(duty),
        "duty_stable": len(stable),
        "duty_stability": rate(len(stable), len(duty)),
        # An item that is 적합 in one round and not in another is the costly kind of instability:
        # the reviewer's to-do list would differ from run to run.
        "duty_pass_flips": [
            row["code"]
            for row in duty
            if "적합" in row["verdicts"] and len(set(row["verdicts"])) > 1
        ],
        "duty_unstable": [
            {"code": row["code"], "verdicts": row["verdicts"]} for row in duty if not row["stable"]
        ],
    }


def stability_metrics(result: dict) -> dict:
    classification = result["classification"]
    return {
        "repeats": result["repeats"],
        "classification_cases": len(classification),
        "classification_stable": sum(1 for row in classification if row["stable"]),
        "classification_unstable": [row["case"] for row in classification if not row["stable"]],
        **_duty_agreement(result["duty"]),
        "baseline": {
            arm: _duty_agreement(rows) for arm, rows in (result.get("baseline") or {}).items()
        },
    }


def display_flip_metrics(result: dict) -> dict:
    rows = result["rows"]
    injected = [row for row in rows if row["kind"] == "결함 주입" and row["landed"]]
    controls = [row for row in rows if row["kind"] == "대조군" and row["landed"]]
    detected = [row for row in injected if row.get("detected")]
    blamed = [row for row in controls if row.get("blamed_control")]
    return {
        "injected": len(injected),
        "detected": len(detected),
        "detection_rate": rate(len(detected), len(injected)),
        "missed": [row["case"] for row in injected if not row.get("detected")],
        "controls": len(controls),
        "blamed_controls": len(blamed),
        "blamed": [row["case"] for row in blamed],
        "skipped": [row["case"] for row in rows if not row["landed"]],
        "base_verdicts": {
            base["page"]: f"{base['watch']} {base['verdict']}" for base in result["bases"]
        },
    }


METRICS = {
    "classification": classification_metrics,
    "duty-flip": duty_flip_metrics,
    "plain-contract": plain_contract_metrics,
    "stability": stability_metrics,
    "display-flip": display_flip_metrics,
}


def metrics_for(result: dict) -> dict[str, Any]:
    name = result["suite"].split("/")[0]
    return METRICS[name](result)
