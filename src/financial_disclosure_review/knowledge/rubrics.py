"""Reading rubric items out of the reference DB, and scoping them to a classification."""

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

RUBRIC_BUILD_STEP = "python -m financial_disclosure_review build-db"


def load_rubric(db_path: str | Path, rubric: str, groups: tuple[str, ...] = ()) -> list[dict]:
    """Items of one rubric in yaml order; `groups` keeps items whose group starts with a prefix."""
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"rubric DB {path} does not exist. Run {RUBRIC_BUILD_STEP}.")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        try:
            names = dict(conn.execute("SELECT name, screen_field FROM rubrics").fetchall())
            rows = conn.execute(
                "SELECT code, group_name, applies_condition, binding, criterion FROM rubric_items"
                " WHERE rubric = ? ORDER BY position",
                (rubric,),
            ).fetchall()
            applies_to = conn.execute(
                "SELECT code, product_type FROM rubric_applies_to ORDER BY code, position"
            ).fetchall()
            screens = conn.execute(
                "SELECT code, screen FROM rubric_screens ORDER BY code, position"
            ).fetchall()
            sources = conn.execute(
                "SELECT code, doc, loc, quote, snapshot, official_url FROM rubric_sources"
                " ORDER BY code, position"
            ).fetchall()
        except sqlite3.OperationalError as error:
            raise RuntimeError(
                f"rubric DB {path} has no rubric tables ({error}). Run {RUBRIC_BUILD_STEP}."
            ) from error
    if rubric not in names:
        raise RuntimeError(
            f"rubric DB {path} has no rubric {rubric!r} (it has {sorted(names)})."
            f" Run {RUBRIC_BUILD_STEP}."
        )
    if not rows:
        raise RuntimeError(
            f"rubric DB {path} has no items for rubric {rubric!r}. Run {RUBRIC_BUILD_STEP}."
        )
    screen_field = names[rubric]
    lists = {code: {"applies_to": [], "screens": [], "sources": []} for code, *_ in rows}
    for code, value in applies_to:
        if code in lists:
            lists[code]["applies_to"].append(value)
    for code, value in screens:
        if code in lists:
            lists[code]["screens"].append(value)
    for code, *values in sources:
        if code in lists:
            lists[code]["sources"].append(
                dict(zip(("doc", "loc", "quote", "snapshot", "official_url"), values))
            )
    return [
        {
            "code": code,
            "group": group,
            "applies_to": lists[code]["applies_to"],
            screen_field: lists[code]["screens"],
            "applies_condition": condition,
            "binding": binding,
            "criterion": criterion,
            "sources": lists[code]["sources"],
        }
        for code, group, condition, binding, criterion in rows
        if not groups or group.startswith(groups)
    ]


def item_scope(item: dict, classification: Mapping[str, Any]) -> str:
    """Empty when the item applies to the classified product type and page type; else why not."""
    product_type, page_type = classification.get("product_type"), classification.get("page_type")
    if product_type not in item["applies_to"]:
        return f"applies_to {item['applies_to']} does not include {product_type!r}"
    if page_type not in item["page_types"]:
        return f"page_types {item['page_types']} does not include {page_type!r}"
    return ""


def rubric_question(criterion: str) -> str:
    """The asking sentence of a criterion (`규칙 문장. 질문?`), without the trailing note after `?`.

    A criterion with no `?` is returned whole."""
    end = criterion.find("?")
    if end < 0:
        return criterion.strip()
    start = criterion.rfind(". ", 0, end)
    return criterion[start + 2 if start >= 0 else 0 : end + 1].strip()


# Short names for the source documents a rubric item cites, as a reviewer would say them.
DOC_NAMES = {
    "kfcpa": "금소법",
    "kfcpa_decree": "금소법 시행령",
    "fsc_rule": "금소 감독규정",
    "fsc_rule_app5": "금소 감독규정 별표5",
    "crefia_reg": "여신협회 광고규정",
    "crefia_guide": "여신협회 광고 세부지침",
    "fsc_ad_guideline": "금융광고규제 가이드라인",
    "fsc_explain": "설명의무 가이드라인",
    "fsc_online_explain": "온라인 설명의무 가이드라인",
    "fsc_ai_guideline": "금융분야 AI 가이드라인",
    "yeojeon": "여전법",
    "yeojeon_decree": "여전법 시행령",
    "yeojeon_rule": "여전업 감독규정",
    "ai_act": "AI 기본법",
    "ai_act_decree": "AI 기본법 시행령",
    "nikl_public_lang": "국립국어원 공공언어 바로 쓰기",
}


def rubric_basis(sources: list[tuple[str, str]]) -> str:
    """`(doc, loc)` pairs as one line: each document once, its first article, then a count."""
    by_doc: dict[str, list[str]] = {}
    for doc, loc in sources:
        by_doc.setdefault(doc, []).append(loc)
    return "; ".join(
        f"{DOC_NAMES.get(doc, doc)} {locs[0]}".strip()
        + (f" 외 {len(locs) - 1}" if len(locs) > 1 else "")
        for doc, locs in by_doc.items()
    )


def rubric_labels(db_path: str | Path) -> dict[str, dict[str, str]]:
    """Every rubric code with its `question` and legal `basis`; an absent DB gives an empty map."""
    path = Path(db_path).resolve()
    if not path.exists():
        return {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        rows = conn.execute("SELECT code, criterion FROM rubric_items").fetchall()
        sources = conn.execute(
            "SELECT code, doc, loc FROM rubric_sources ORDER BY code, position"
        ).fetchall()
    cited: dict[str, list[tuple[str, str]]] = {}
    for code, doc, loc in sources:
        cited.setdefault(code, []).append((doc or "", loc or ""))
    return {
        code: {
            "question": rubric_question(criterion or ""),
            "basis": rubric_basis(cited.get(code, [])),
        }
        for code, criterion in rows
    }


def rubric_bindings(db_path: str | Path) -> dict[str, str]:
    """Every rubric code with its binding level; an absent DB gives an empty map (stricter kept)."""
    path = Path(db_path).resolve()
    if not path.exists():
        return {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        return dict(conn.execute("SELECT code, binding FROM rubric_items").fetchall())
