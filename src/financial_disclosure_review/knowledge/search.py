"""Vector search over the reference DB: the nearest sanction/dispute cases to a query."""

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

from .cases import CASE_BUILD_STEP
from .db import connect

# Cosine distance in sqlite-vec: 0 is identical, 1 is unrelated. Similarity is reported as
# 1 - distance so a caller can read it the usual way round.
HIT_FIELDS = (
    "case_id",
    "issue",
    "outcome",
    "official_primary_url",
    "official_date",
    "institution",
    "firm",
    "record_type",
    "product_basis",
    "product_subtype",
    "mvp_signal",
    "page_only_detectability",
    "source_tier",
)


def search(db_path: str | Path, query: str, kind: str = "", k: int = 5, embed=None) -> list[dict]:
    """The k cases nearest to `query`, nearest first.

    `kind` is a product type (신용카드, 단기카드대출, 장기카드대출, 리볼빙, 할부금융·리스); when
    given, only cases that apply to it are considered. `embed` takes a list of texts and returns a
    list of vectors, so a caller can hand in a stand-in and search without paying.
    Each hit carries `distance`, `similarity`, `related_checklist` and the fields in HIT_FIELDS.
    """
    if not query.strip() or k <= 0:
        return []
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"reference DB {path} does not exist. Run {CASE_BUILD_STEP}.")
    if embed is None:
        from ..llm.client import embed_texts

        embed = embed_texts
    vector = embed([query])[0]

    import sqlite_vec

    columns = ", ".join(f"c.{name}" for name in HIT_FIELDS)
    sql = (
        f"SELECT {columns}, v.distance FROM case_vectors v JOIN cases c ON c.case_id = v.case_id"
        " WHERE v.embedding MATCH ? AND k = ?"
    )
    args: list = [sqlite_vec.serialize_float32(vector), k]
    if kind:
        sql += " AND v.case_id IN (SELECT case_id FROM case_product_types WHERE product_type = ?)"
        args.append(kind)
    with closing(connect(path, read_only=True)) as conn:
        try:
            rows = conn.execute(sql + " ORDER BY v.distance", args).fetchall()
            checklist = conn.execute(
                "SELECT case_id, code FROM case_checklist ORDER BY case_id, position"
            ).fetchall()
            types = conn.execute(
                "SELECT case_id, product_type FROM case_product_types ORDER BY case_id, position"
            ).fetchall()
        except sqlite3.OperationalError as error:
            raise RuntimeError(
                f"reference DB {path} has no case vectors ({error}). Run {CASE_BUILD_STEP}."
            ) from error
    codes: dict[str, list[str]] = {}
    for case_id, code in checklist:
        codes.setdefault(case_id, []).append(code)
    product_types: dict[str, list[str]] = {}
    for case_id, product_type in types:
        product_types.setdefault(case_id, []).append(product_type)
    hits: list[dict[str, Any]] = []
    for row in rows:
        hit: dict[str, Any] = dict(zip(HIT_FIELDS, row))
        distance = float(row[-1])
        hit["distance"] = round(distance, 6)
        hit["similarity"] = round(1.0 - distance, 6)
        hit["related_checklist"] = codes.get(hit["case_id"], [])
        hit["product_types"] = product_types.get(hit["case_id"], [])
        hits.append(hit)
    return hits


# What a query can be about at this point in the graph: the page has been preprocessed and the
# product type is known, but no judgment has run yet, so a query names the product and one area
# of the rubric rather than a found violation. One query per area keeps the areas from crowding
# each other out of the top k.
QUERY_AREAS = {
    "의무표시": "광고 의무표시, 이자율 범위와 산출기준, 수수료, 연회비, 경고문구",
    "표시방법": "표시방법, 글자 크기와 색상, 강조와 음영, 숨겨진 정보, 최저금리만 표기",
    "금지행위": "오인 표현, 단정적 표현, 최상급 표현, 혜택만 강조하고 조건 누락, 기간 한정 조건",
    "설명의무": "설명의무, 상환방법과 총부담액, 부가서비스 조건과 이행책임, 개인신용평점 영향",
}


def case_queries(classification: Mapping[str, Any], product: Mapping[str, Any]) -> list[dict]:
    """One query per rubric area, each naming the classified product. Order is QUERY_AREAS."""
    product_type = classification.get("product_type") or ""
    name = (product.get("product_name") or "").strip()
    head = f"{product_type} {name}".strip()
    return [{"area": area, "text": f"{head} {terms}"} for area, terms in QUERY_AREAS.items()]


def search_cases_for(
    product: Mapping[str, Any],
    classification: Mapping[str, Any],
    db_path: str | Path,
    k: int = 3,
    embed=None,
) -> dict:
    """The `case_search` value for one page: the queries run and the hits they found.

    Hits are merged across queries and kept unique by `case_id`, nearest first, with `areas`
    recording which queries found each case. A missing or unbuilt case DB is a normal result
    (`status` 판정 불가) rather than an exception: the review can go on without cases.
    """
    queries = case_queries(classification, product)
    product_type = classification.get("product_type") or ""
    found: dict[str, dict[str, Any]] = {}
    try:
        if embed is None:
            from ..llm.client import embed_texts

            embed = embed_texts
        # All the queries are embedded in one call, then handed to `search` one at a time, so a
        # page costs one embedding request rather than one per area.
        vectors = dict(zip((q["text"] for q in queries), embed([q["text"] for q in queries])))
        for query in queries:
            hits = search(
                db_path, query["text"], product_type, k, lambda texts: [vectors[texts[0]]]
            )
            for hit in hits:
                kept = found.setdefault(hit["case_id"], {**hit, "areas": []})
                kept["areas"].append(query["area"])
                if hit["distance"] < kept["distance"]:
                    kept.update(distance=hit["distance"], similarity=hit["similarity"])
    except (FileNotFoundError, RuntimeError) as error:
        return {"queries": queries, "hits": [], "status": "판정 불가", "reason": str(error)}
    hits = sorted(found.values(), key=lambda h: h["distance"])
    return {
        "queries": queries,
        "hits": hits,
        "status": "완료" if hits else "해당 사례 없음",
        "reason": "" if hits else f"{classification.get('product_type')!r}에 해당하는 사례가 없음",
    }
