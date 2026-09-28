"""Building the sanction/dispute case tables, and their vectors, from the case corpus yaml.

The counterpart of `build.py` for cases. Same shape as the rubric build — the yaml is checked
against the tables first, then every case table is dropped and rebuilt in one transaction, so a
failed build leaves the previous DB untouched.

It is kept apart from `build.py` on purpose: `build-db` stays free and offline, while this step
calls a paid embedding model, so it is its own command (`build-cases`).
"""

import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import yaml

from .db import connect

CASE_CORPUS_FILE = "case_corpus.yaml"
# Every field the yaml must carry, and the type it must have. Nothing is coerced.
CASE_FIELDS: dict[str, type | tuple[type, ...]] = {
    "case_id": str,
    "record_type": str,
    "institution": str,
    "firm": str,
    "official_date": str,
    "official_primary_url": str,
    "source_tier": int,
    "product_types": list,
    "product_basis": str,
    "product_subtype": str,
    "legal_basis": str,
    "issue": str,
    "outcome": str,
    "mvp_signal": str,
    "page_only_detectability": str,
    "related_checklist": list,
    "text": str,
    "text_sha256": str,
    "retrieved_at": str,
}
LIST_FIELDS = ("product_types", "related_checklist")
# Columns of `cases`, in table order. The two list fields live in their own tables.
CASE_COLUMNS = tuple(f for f in CASE_FIELDS if f not in LIST_FIELDS)
RECORD_TYPES = ("위반사례", "지적사례", "민원사례")
PRODUCT_BASES = ("직접", "유추")
DETECTABILITY = ("full", "partial", "review_required", "out_of_scope")


def case_schema(dimensions: int) -> list[str]:
    """DDL for the case tables. `dimensions` must match the embedding model's output width."""
    return [
        "DROP TABLE IF EXISTS case_vectors",
        "DROP TABLE IF EXISTS case_checklist",
        "DROP TABLE IF EXISTS case_product_types",
        "DROP TABLE IF EXISTS cases",
        """CREATE TABLE cases (
            case_id TEXT PRIMARY KEY,
            position INTEGER NOT NULL UNIQUE,   -- order in the yaml
            record_type TEXT NOT NULL,          -- 위반사례 | 지적사례 | 민원사례
            institution TEXT NOT NULL,
            firm TEXT NOT NULL,
            official_date TEXT NOT NULL,
            official_primary_url TEXT NOT NULL,
            source_tier INTEGER NOT NULL,
            product_basis TEXT NOT NULL,        -- 직접 | 유추
            product_subtype TEXT NOT NULL,
            legal_basis TEXT NOT NULL,
            issue TEXT NOT NULL,
            outcome TEXT NOT NULL,
            mvp_signal TEXT NOT NULL,
            page_only_detectability TEXT NOT NULL,
            text TEXT NOT NULL,                 -- the quoted source wording, and what is embedded
            text_sha256 TEXT NOT NULL,          -- SHA-256 of text.strip(), for reproducibility
            retrieved_at TEXT NOT NULL
        )""",
        """CREATE TABLE case_product_types (
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            position INTEGER NOT NULL,
            product_type TEXT NOT NULL,
            PRIMARY KEY (case_id, position)
        )""",
        """CREATE TABLE case_checklist (
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            position INTEGER NOT NULL,
            code TEXT NOT NULL,                 -- a rubric item code (A01, 표시04, 쉬운말12 …)
            PRIMARY KEY (case_id, position)
        )""",
        "CREATE INDEX case_product_types_type ON case_product_types (product_type)",
        "CREATE INDEX case_checklist_code ON case_checklist (code)",
        # One row per case. Product-type filtering is a subquery on case_product_types, which
        # sqlite-vec 0.1.9 accepts as a KNN prefilter (`AND case_id IN (SELECT …)`).
        f"""CREATE VIRTUAL TABLE case_vectors USING vec0(
            case_id TEXT PRIMARY KEY,
            embedding float[{dimensions}] distance_metric=cosine
        )""",
    ]


def case_schema_problems(items: list[dict]) -> list[str]:
    """Every way the yaml differs from the case tables. Nothing is coerced."""
    problems = []
    for n, item in enumerate(items):
        where = f"case {n} ({item.get('case_id')})"
        if not isinstance(item, dict):
            problems.append(f"{where}: not a mapping")
            continue
        if set(item) != set(CASE_FIELDS):
            problems.append(
                f"{where}: missing {sorted(set(CASE_FIELDS) - set(item))},"
                f" extra {sorted(set(item) - set(CASE_FIELDS))}"
            )
        for key, kind in CASE_FIELDS.items():
            if key in item and not isinstance(item[key], kind):
                problems.append(f"{where}: {key} is {type(item[key]).__name__}")
        for key in LIST_FIELDS:
            value = item.get(key)
            if isinstance(value, list) and (
                not value or not all(isinstance(v, str) and v for v in value)
            ):
                problems.append(f"{where}: {key} is empty or has a non-string value")
        for key, allowed in (
            ("record_type", RECORD_TYPES),
            ("product_basis", PRODUCT_BASES),
            ("page_only_detectability", DETECTABILITY),
        ):
            if item.get(key) not in allowed:
                problems.append(f"{where}: {key} is {item.get(key)!r}, not one of {allowed}")
        # The rubric's sources[].official_url principle: a case with no official source is out.
        url = item.get("official_primary_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            problems.append(f"{where}: official_primary_url is {url!r}, not an https URL")
        if not isinstance(item.get("text"), str) or not (item.get("text") or "").strip():
            problems.append(f"{where}: text is empty, so there is nothing to embed")
        elif item.get("text_sha256") != sha256(item["text"].strip().encode("utf-8")).hexdigest():
            problems.append(f"{where}: text_sha256 does not match text.strip()")
    codes = [item.get("case_id") for item in items]
    problems += [
        f"case_id {code} appears {codes.count(code)} times"
        for code in sorted({c for c in codes if codes.count(c) > 1}, key=str)
    ]
    return problems


def embed_text_of(item: dict) -> str:
    """What gets embedded: the fields a query would be about, not the bookkeeping ones.

    The product type and the checklist codes are included so a query naming a product type or a
    judgment item lands near the cases that carry it, on top of the metadata prefilter.
    """
    return "\n".join(
        [
            f"상품유형: {', '.join(item['product_types'])}",
            f"상품: {item['product_subtype']}",
            f"문제: {item['issue']}",
            f"조치: {item['outcome']}",
            f"페이지 신호: {item['mvp_signal']}",
            f"관련 점검항목: {', '.join(item['related_checklist'])}",
            item["text"].strip(),
        ]
    )


def build_case_db(
    corpus_path: str | Path, db_path: str | Path, embed=None, dimensions: int | None = None
) -> dict[str, int]:
    """Load the case corpus into db_path and embed each case. Safe to re-run.

    `embed` takes a list of texts and returns a list of vectors, so a caller can hand in a
    stand-in and build the DB without paying (the same arrangement as `call_ask`'s `ask_fn`).
    Returns the counts a caller can assert on.
    """
    path = Path(corpus_path)
    if path.is_dir():
        path = path / CASE_CORPUS_FILE
    if not path.exists():
        raise FileNotFoundError(f"case corpus {path} does not exist")
    loaded = yaml.safe_load(path.read_text())
    items = (loaded or {}).get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"case corpus {path} has no items list")
    problems = case_schema_problems(items)
    if problems:
        raise ValueError(
            f"the case corpus {path.name} does not fit the case tables:\n" + "\n".join(problems)
        )

    if embed is None:  # imported here so an offline build never needs the API client
        from ..llm.client import EMBED_DIMENSIONS, embed_texts

        embed, dimensions = embed_texts, dimensions or EMBED_DIMENSIONS
    vectors = embed([embed_text_of(item) for item in items])
    if len(vectors) != len(items):
        raise RuntimeError(f"embedding returned {len(vectors)} vectors for {len(items)} cases")
    width = dimensions or len(vectors[0])
    wrong = [n for n, vector in enumerate(vectors) if len(vector) != width]
    if wrong:
        raise RuntimeError(f"cases {wrong} got a vector that is not {width} numbers wide")

    import sqlite_vec  # a local import keeps `knowledge.cases` importable without the extension

    with closing(connect(db_path)) as conn:
        conn.execute("BEGIN")
        try:
            for statement in case_schema(width):
                conn.execute(statement)
            for position, (item, vector) in enumerate(zip(items, vectors)):
                case_id = item["case_id"]
                conn.execute(
                    f"INSERT INTO cases VALUES ({','.join('?' * (len(CASE_COLUMNS) + 1))})",
                    (case_id, position, *(item[f] for f in CASE_COLUMNS if f != "case_id")),
                )
                conn.executemany(
                    "INSERT INTO case_product_types VALUES (?, ?, ?)",
                    [(case_id, k, v) for k, v in enumerate(item["product_types"])],
                )
                conn.executemany(
                    "INSERT INTO case_checklist VALUES (?, ?, ?)",
                    [(case_id, k, v) for k, v in enumerate(item["related_checklist"])],
                )
                conn.execute(
                    "INSERT INTO case_vectors(case_id, embedding) VALUES (?, ?)",
                    (case_id, sqlite_vec.serialize_float32(vector)),
                )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return {
        "cases": len(items),
        "product_types": sum(len(i["product_types"]) for i in items),
        "checklist_codes": sum(len(i["related_checklist"]) for i in items),
        "dimensions": width,
    }


def case_db_counts(db_path: str | Path) -> dict[str, int]:
    """Row counts of the case tables, or an empty dict when the DB has none yet."""
    try:
        with closing(connect(db_path, read_only=True)) as conn:
            return {
                name: conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                for name in ("cases", "case_product_types", "case_checklist", "case_vectors")
            }
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return {}
