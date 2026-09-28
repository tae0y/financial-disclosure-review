"""Smoke test against the real local persona dataset (about 2GB); skipped when it is absent.

Marked use_network so the default run never reads it; run with `-m use_network`.
"""

from pathlib import Path

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.persona_explanation.dataset import (
    Filters,
    PersonaStore,
    dataset_dir,
    missing_shards,
)
from financial_disclosure_review.domain.persona_explanation.selection import choose_profile

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"

pytestmark = [
    pytest.mark.use_network,
    pytest.mark.skipif(bool(missing_shards(DATA_DIR)), reason="persona dataset not downloaded"),
]


def test_the_real_dataset_answers_queries_and_every_filter_field_exists():
    store = PersonaStore(dataset_dir(DATA_DIR))
    assert store.count(Filters()) == 1_000_000
    assert set(Filters.model_fields) - {"age_min", "age_max", "occupation_contains"} <= set(
        store.fields()
    )
    assert store.values("province", limit=1)[0]["value"] == "경기"


def test_choose_profile_on_the_real_dataset_is_deterministic():
    ctx = Context(
        model="fake",
        rubric_dir=str(ROOT / "assets"),
        persona_attributes={"age_min": 70, "education_level": ["초등학교"]},
    )

    def choose() -> dict:
        return choose_profile(
            ctx,
            product_type="장기카드대출",
            cards=[],
            data_dir=DATA_DIR,
            rubric_dir=ROOT / "assets",
        )

    first = choose()
    assert first["selection"]["decided_by"] == "attributes"
    assert first["profile"]["status"] == "적용"
    assert first["profile"]["attributes"]["financial_familiarity"] == "낮음"
    assert choose()["profile"]["id"] == first["profile"]["id"]
