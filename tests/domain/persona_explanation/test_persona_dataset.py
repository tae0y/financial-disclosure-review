"""The pinned persona dataset: verified download, and parameterized queries over the shards."""

import hashlib
from collections.abc import Set as AbstractSet
from pathlib import Path

import pytest
from pydantic import ValidationError

from financial_disclosure_review.domain.persona_explanation.dataset import (
    REVISION,
    SHARDS,
    Filters,
    PersonaStore,
    dataset_dir,
    ensure_dataset,
    filters_from_pairs,
    shard_url,
    validate_filters,
)
from tests.domain.persona_explanation.persona_dataset import uuid_of, write_store


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


BODIES = {"a.parquet": b"alpha", "b.parquet": b"bravo"}
PINNED = {name: _sha(body) for name, body in BODIES.items()}


class FakeFetch:
    """Writes the pinned body (or a wrong one) to the destination and records each URL."""

    def __init__(
        self, wrong: AbstractSet[str] = frozenset(), broken: AbstractSet[str] = frozenset()
    ):
        self.urls: list[str] = []
        self.wrong, self.broken = wrong, broken

    def __call__(self, url: str, dest: Path) -> None:
        self.urls.append(url)
        name = url.rsplit("/", 1)[-1]
        if name in self.broken:
            raise OSError("connection reset")
        dest.write_bytes(b"tampered" if name in self.wrong else BODIES[name])


@pytest.fixture
def store(tmp_path) -> PersonaStore:
    return PersonaStore(write_store(tmp_path / "set"))


def test_the_dataset_is_pinned_to_one_revision_and_nine_hashed_shards(tmp_path):
    assert len(REVISION) == 40
    assert sorted(SHARDS) == [f"train-0000{n}-of-00009.parquet" for n in range(9)]
    assert all(len(sha) == 64 for sha in SHARDS.values())
    assert dataset_dir(tmp_path) == tmp_path / "personas" / REVISION
    assert shard_url("train-00000-of-00009.parquet") == (
        "https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea/resolve/"
        f"{REVISION}/data/train-00000-of-00009.parquet"
    )


def test_ensure_dataset_downloads_missing_shards_and_verifies_them(tmp_path):
    fetch = FakeFetch()
    report = ensure_dataset(tmp_path, fetch=fetch, shards=PINNED, log=lambda _: None)
    folder = dataset_dir(tmp_path)
    assert {r["shard"]: r["status"] for r in report["shards"]} == {
        "a.parquet": "downloaded",
        "b.parquet": "downloaded",
    }
    assert report["ok"] is True
    assert (folder / "a.parquet").read_bytes() == b"alpha"
    assert not list(folder.glob("*.part"))

    again = FakeFetch()
    report = ensure_dataset(tmp_path, fetch=again, shards=PINNED, log=lambda _: None)
    assert again.urls == []
    assert {r["status"] for r in report["shards"]} == {"present"}


def test_ensure_dataset_replaces_a_shard_whose_hash_does_not_match(tmp_path):
    folder = dataset_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / "a.parquet").write_bytes(b"alpha")
    (folder / "b.parquet").write_bytes(b"corrupted")
    fetch = FakeFetch()
    report = ensure_dataset(tmp_path, fetch=fetch, shards=PINNED, log=lambda _: None)
    assert [u.rsplit("/", 1)[-1] for u in fetch.urls] == ["b.parquet"]
    assert (folder / "b.parquet").read_bytes() == b"bravo"
    assert report["ok"] is True


def test_a_download_with_the_wrong_hash_or_an_error_is_failed_and_leaves_no_file(tmp_path):
    fetch = FakeFetch(wrong={"a.parquet"}, broken={"b.parquet"})
    report = ensure_dataset(tmp_path, fetch=fetch, shards=PINNED, log=lambda _: None)
    rows = {r["shard"]: r for r in report["shards"]}
    assert rows["a.parquet"]["status"] == "failed" and "sha256" in rows["a.parquet"]["reason"]
    assert rows["b.parquet"]["status"] == "failed" and "OSError" in rows["b.parquet"]["reason"]
    assert report["ok"] is False
    assert list(dataset_dir(tmp_path).iterdir()) == []


def test_the_store_lists_fields_and_categorical_values_with_counts(store):
    assert {"uuid", "age", "occupation", "persona"} <= set(store.fields())
    assert store.values("sex") == [{"value": "여자", "count": 5}, {"value": "남자", "count": 4}]
    assert len(store.values("occupation", limit=2)) == 2
    with pytest.raises(ValueError):
        store.values("persona")


def test_count_and_pick_apply_every_filter(store):
    assert store.count(Filters()) == 9
    assert store.count(Filters(age_min=70)) == 2
    assert store.count(Filters(age_min=30, age_max=59, sex="남자")) == 3
    assert store.count(Filters(education_level=["대학원", "무학"])) == 2
    assert store.count(Filters(occupation_contains=["보험", "은행"])) == 2
    assert store.count(Filters(province=["서울"], housing_type=["아파트"])) == 2
    row = store.pick(Filters(occupation_contains=["회계"]), seed="s")
    assert row is not None and row["uuid"] == uuid_of("07") and row["age"] == 31
    assert store.pick(Filters(age_min=90), seed="s") is None


def test_pick_is_deterministic_for_a_seed(store):
    first = store.pick(Filters(), seed="fixed")
    assert first is not None
    assert all(store.pick(Filters(), seed="fixed")["uuid"] == first["uuid"] for _ in range(3))
    picked = {store.pick(Filters(), seed=f"seed-{n}")["uuid"] for n in range(12)}
    assert len(picked) > 1


def test_row_returns_one_row_by_uuid_or_none(store):
    assert store.row(uuid_of("03"))["occupation"] == "간호사"
    assert store.row("f" * 32) is None
    assert store.row("'; DROP TABLE x; --") is None


def test_filters_only_take_real_fields():
    with pytest.raises(ValidationError):
        Filters.model_validate({"income": "high"})
    with pytest.raises(ValidationError):
        Filters(occupation_contains=["a", "b", "c"])


def test_validate_filters_rejects_values_outside_the_dataset_vocabulary(store):
    assert validate_filters(store, Filters(sex="여자", province=["서울"])) == []
    problems = validate_filters(
        store,
        Filters(
            sex="기타",
            province=["서울", "화성"],
            education_level=["박사"],
            occupation_contains=["우주비행"],
            age_min=60,
            age_max=40,
        ),
    )
    joined = " ".join(problems)
    for needle in ("sex", "화성", "박사", "우주비행", "age_min"):
        assert needle in joined


def test_filters_from_pairs_parses_cli_attributes():
    assert filters_from_pairs(["age_min=30", "province=서울,경기", "sex=여자"]) == {
        "age_min": 30,
        "province": ["서울", "경기"],
        "sex": "여자",
    }
    with pytest.raises(ValueError):
        filters_from_pairs(["income=high"])
    with pytest.raises(ValueError):
        filters_from_pairs(["age_min"])
    with pytest.raises(ValueError):
        filters_from_pairs(["age_min=old"])
