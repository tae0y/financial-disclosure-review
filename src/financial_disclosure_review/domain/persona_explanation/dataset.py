"""The pinned nvidia/Nemotron-Personas-Korea dataset on local disk: download, verify, query.

The full dataset is fetched once (container first boot, or `fetch-personas`) and read from disk
with DuckDB; nothing is downloaded while a review runs. Every query is parameterized, and filter
values must come from the dataset's own vocabulary.
"""

import hashlib
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import get_origin

import duckdb
import httpx
from pydantic import BaseModel, ConfigDict, Field

DATASET = "nvidia/Nemotron-Personas-Korea"
LICENSE = "CC-BY-4.0"
REVISION = "ada0f5b53a38bb5a30cce09358adde883c1ab63a"
# sha256 of every shard, in shard order (train-0000N-of-00009.parquet).
SHARDS: dict[str, str] = {
    f"train-{n:05d}-of-00009.parquet": sha
    for n, sha in enumerate(
        (
            "5f447553b9e30ac98631af17f2274780586fbd5e2705125b8f3a49fe2af037b2",
            "332ade7365bd842838de6295e15f4457d0050b4792b33a8330b3b8a39a6dfc3b",
            "65d4860663fab1ff4166f5db4eb96fc39e84ccc952391ab36437d0373bc6d5f1",
            "d94a0f221edd1e70e28d7e19acf9b9f4cfa315b630f51607b28b06498a28591b",
            "c31efb3b3f0ef6405956683a9a6fb99276dea2c16b22efe883555a31ff05b3ed",
            "e95979de298ffecac1db437401baf19e3bdae16355fcd5a54320c63290c3e07f",
            "5b0fc5fd097bd9c82be9f6c9ff57eddee314226eabe820f83e2426bed34e40ff",
            "73a4178828b9d08cd44b141c3c0da2d69521a8fa9cd22194868d07c36f0a6680",
            "e32faf2717f7b9634ff38d62b175f9d9817b1eee797c043032b3dc2d8d055fe6",
        )
    )
}
# Fields whose distinct values may be listed and used as filter values. occupation has ~2,000
# values, so it is listed by frequency and filtered by substring instead of by exact value.
CATEGORICAL_FIELDS = (
    "sex",
    "education_level",
    "occupation",
    "province",
    "family_type",
    "housing_type",
    "marital_status",
)
SOURCE = "read_parquet(?)"  # the shard glob is always the first query parameter
LIST_FILTERS = ("education_level", "province", "family_type", "housing_type", "marital_status")


def dataset_dir(data_dir: str | Path) -> Path:
    return Path(data_dir) / "personas" / REVISION


def shard_url(shard: str) -> str:
    return f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{shard}"


def missing_shards(data_dir: str | Path) -> list[str]:
    """Pinned shard names absent from disk. Existence only: hashing 2GB is left to fetch."""
    folder = dataset_dir(data_dir)
    return [shard for shard in sorted(SHARDS) if not (folder / shard).is_file()]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def http_fetch(url: str, dest: Path) -> None:
    """Stream one file to dest; Hugging Face answers resolve URLs with a redirect."""
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        with dest.open("wb") as file:
            for chunk in response.iter_bytes(1 << 20):
                file.write(chunk)


def ensure_dataset(
    data_dir: str | Path,
    fetch: Callable[[str, Path], None] = http_fetch,
    shards: Mapping[str, str] = SHARDS,
    log: Callable[[str], None] = print,
) -> dict:
    """Download every missing or hash-mismatched shard, verified before it takes its name.

    Returns {dir, ok, shards: [{shard, status: present | downloaded | failed, bytes, reason}]};
    a failed shard is reported, never raised, and leaves no file behind.
    """
    folder = dataset_dir(data_dir)
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for shard, expected in sorted(shards.items()):
        path = folder / shard
        if path.is_file() and sha256_of(path) == expected:
            log(f"  {shard}: present, sha256 verified ({path.stat().st_size:,} bytes)")
            rows.append({"shard": shard, "status": "present", "bytes": path.stat().st_size})
            continue
        part = path.with_name(path.name + ".part")
        url = shard_url(shard)
        log(f"  {shard}: downloading {url}")
        try:
            fetch(url, part)
            actual = sha256_of(part)
            if actual != expected:
                raise ValueError(f"sha256 mismatch: expected {expected[:12]}, got {actual[:12]}")
            os.replace(part, path)
        except (OSError, ValueError, httpx.HTTPError) as error:
            part.unlink(missing_ok=True)
            reason = f"{type(error).__name__}: {error}"
            log(f"  {shard}: FAILED {reason}")
            rows.append({"shard": shard, "status": "failed", "bytes": 0, "reason": reason})
            continue
        size = path.stat().st_size
        log(f"  {shard}: downloaded {size:,} bytes, sha256 verified")
        rows.append({"shard": shard, "status": "downloaded", "bytes": size})
    return {
        "dir": str(folder),
        "ok": all(r["status"] != "failed" for r in rows),
        "shards": rows,
    }


class Filters(BaseModel):
    """Row filters over the persona dataset. Every list value must be a real dataset value."""

    model_config = ConfigDict(extra="forbid")
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = None
    education_level: list[str] = []
    occupation_contains: list[str] = Field(
        default=[], max_length=2, description="substrings of occupation; a row matches any one"
    )
    province: list[str] = []
    family_type: list[str] = []
    housing_type: list[str] = []
    marital_status: list[str] = []


def filters_from_pairs(pairs: list[str]) -> dict:
    """CLI `key=value` pairs to a Filters dict: list fields split on commas, ages as ints."""
    result: dict = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not value:
            raise ValueError(f"expected key=value, got {pair!r}")
        field = Filters.model_fields.get(key)
        if field is None:
            raise ValueError(
                f"unknown persona attribute {key!r}; one of {list(Filters.model_fields)}"
            )
        if get_origin(field.annotation) is list:
            result[key] = [v.strip() for v in value.split(",") if v.strip()]
        elif key in ("age_min", "age_max"):
            try:
                result[key] = int(value)
            except ValueError:
                raise ValueError(f"{key} must be a whole number, got {value!r}") from None
        else:
            result[key] = value
    return result


def _where(filters: Filters) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if filters.age_min is not None:
        clauses.append("age >= ?")
        params.append(filters.age_min)
    if filters.age_max is not None:
        clauses.append("age <= ?")
        params.append(filters.age_max)
    if filters.sex:
        clauses.append("sex = ?")
        params.append(filters.sex)
    for name in LIST_FILTERS:
        values = getattr(filters, name)
        if values:
            clauses.append(f"list_contains(?, {name})")
            params.append(list(values))
    if filters.occupation_contains:
        clauses.append(
            "(" + " OR ".join("contains(occupation, ?)" for _ in filters.occupation_contains) + ")"
        )
        params.extend(filters.occupation_contains)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


class PersonaStore:
    """Read-only queries over the parquet shards in one folder."""

    def __init__(self, path: str | Path) -> None:
        self.glob = str(Path(path) / "*.parquet")
        self.con = duckdb.connect()
        self._vocab: dict[str, set[str]] = {}

    def _query(self, sql: str, params: list) -> list[tuple]:
        """sql reads the shards through its first placeholder, `SOURCE`."""
        return self.con.execute(sql, [self.glob, *params]).fetchall()

    def fields(self) -> list[str]:
        return [row[0] for row in self._query(f"DESCRIBE SELECT * FROM {SOURCE}", [])]

    def values(self, field: str, limit: int = 30) -> list[dict]:
        """Distinct values of a categorical field with their row counts, most frequent first."""
        if field not in CATEGORICAL_FIELDS:
            raise ValueError(f"not a categorical field: {field}")
        rows = self._query(
            f"SELECT {field}, count(*) AS n FROM {SOURCE} GROUP BY 1 ORDER BY n DESC, 1 LIMIT ?",
            [limit],
        )
        return [{"value": value, "count": n} for value, n in rows]

    def vocabulary(self, field: str) -> set[str]:
        if field not in self._vocab:
            if field not in CATEGORICAL_FIELDS:
                raise ValueError(f"not a categorical field: {field}")
            rows = self._query(f"SELECT DISTINCT {field} FROM {SOURCE}", [])
            self._vocab[field] = {value for (value,) in rows if value is not None}
        return self._vocab[field]

    def count(self, filters: Filters) -> int:
        where, params = _where(filters)
        return self._query(f"SELECT count(*) FROM {SOURCE}{where}", params)[0][0]

    def _rows(self, sql: str, params: list) -> list[dict]:
        cursor = self.con.execute(sql, [self.glob, *params])
        names = [d[0] for d in cursor.description or []]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]

    def pick(self, filters: Filters, seed: str) -> dict | None:
        """One matching row, the same for the same filters and seed."""
        where, params = _where(filters)
        rows = self._rows(
            f"SELECT * FROM {SOURCE}{where} ORDER BY md5(uuid || ?), uuid LIMIT 1", [*params, seed]
        )
        return rows[0] if rows else None

    def row(self, uuid: str) -> dict | None:
        rows = self._rows(f"SELECT * FROM {SOURCE} WHERE uuid = ? LIMIT 1", [uuid])
        return rows[0] if rows else None


def validate_filters(store: PersonaStore, filters: Filters) -> list[str]:
    """Why the filters are not usable as given; empty when every value exists in the dataset."""
    problems = []
    if filters.age_min is not None and filters.age_max is not None:
        if filters.age_min > filters.age_max:
            problems.append(f"age_min {filters.age_min}이 age_max {filters.age_max}보다 큼")
    if filters.sex and filters.sex not in store.vocabulary("sex"):
        problems.append(f"sex: 데이터셋에 없는 값 {filters.sex!r}")
    for name in LIST_FILTERS:
        unknown = [v for v in getattr(filters, name) if v not in store.vocabulary(name)]
        if unknown:
            problems.append(f"{name}: 데이터셋에 없는 값 {', '.join(unknown)}")
    occupations = store.vocabulary("occupation")
    for term in filters.occupation_contains:
        if not term.strip() or not any(term in o for o in occupations):
            problems.append(f"occupation_contains: 어떤 직업에도 포함되지 않는 문자열 {term!r}")
    return problems
