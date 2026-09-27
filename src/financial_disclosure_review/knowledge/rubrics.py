"""Reading rubric items out of the reference DB, and scoping them to a classification."""

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

RUBRIC_BUILD_STEP = "python -m financial_disclosure_review build-db"


def load_rubric(db_path: str | Path, rubric: str, groups: tuple[str, ...] = ()) -> list[dict]:
    """Items of one rubric (its yaml file stem) in yaml order, shaped as that yaml gave them.
    groups keeps only items whose group starts with one of these prefixes, e.g. ("E.",)."""
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
