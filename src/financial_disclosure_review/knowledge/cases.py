"""Reading sanction/dispute cases out of the reference DB, the way `rubrics.py` reads items."""

import sqlite3
from contextlib import closing
from pathlib import Path

CASE_BUILD_STEP = "python -m financial_disclosure_review build-cases"
CASE_COLUMNS = (
    "case_id",
    "record_type",
    "institution",
    "firm",
    "official_date",
    "official_primary_url",
    "source_tier",
    "product_basis",
    "product_subtype",
    "legal_basis",
    "issue",
    "outcome",
    "mvp_signal",
    "page_only_detectability",
    "text",
    "text_sha256",
    "retrieved_at",
)


def _open(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"reference DB {path} does not exist. Run {CASE_BUILD_STEP}.")
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


def load_cases(
    db_path: str | Path, product_types: tuple[str, ...] = (), codes: tuple[str, ...] = ()
) -> list[dict]:
    """Cases in yaml order, filtered by `product_types`/`codes` (both empty means every case)."""
    with closing(_open(db_path)) as conn:
        try:
            rows = conn.execute(
                f"SELECT {', '.join(CASE_COLUMNS)} FROM cases ORDER BY position"
            ).fetchall()
            types = conn.execute(
                "SELECT case_id, product_type FROM case_product_types ORDER BY case_id, position"
            ).fetchall()
            checklist = conn.execute(
                "SELECT case_id, code FROM case_checklist ORDER BY case_id, position"
            ).fetchall()
        except sqlite3.OperationalError as error:
            raise RuntimeError(
                f"reference DB {db_path} has no case tables ({error}). Run {CASE_BUILD_STEP}."
            ) from error
    if not rows:
        raise RuntimeError(f"reference DB {db_path} has no cases. Run {CASE_BUILD_STEP}.")
    lists: dict[str, dict[str, list[str]]] = {
        row[0]: {"product_types": [], "related_checklist": []} for row in rows
    }
    for case_id, value in types:
        if case_id in lists:
            lists[case_id]["product_types"].append(value)
    for case_id, value in checklist:
        if case_id in lists:
            lists[case_id]["related_checklist"].append(value)
    cases = [{**dict(zip(CASE_COLUMNS, row)), **lists[row[0]]} for row in rows]
    return [
        case
        for case in cases
        if (not product_types or set(case["product_types"]) & set(product_types))
        and (not codes or set(case["related_checklist"]) & set(codes))
    ]


def case_summary(case: dict) -> str:
    """One line naming a case, for a reason string or a printed summary."""
    return (
        f"{case['case_id']} ({case['institution']} {case['official_date']},"
        f" {case['record_type']}): {case['issue']}"
    )
