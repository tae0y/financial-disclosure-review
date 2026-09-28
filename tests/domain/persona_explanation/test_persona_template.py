"""The reading-profile template: fixed rules from one dataset row, pinned by version."""

from pathlib import Path

import pytest
import yaml

from financial_disclosure_review.domain.persona_explanation.dataset import REVISION
from financial_disclosure_review.domain.persona_explanation.profiles import (
    resolve_dataset_profile,
)
from financial_disclosure_review.domain.persona_explanation.template import (
    TEMPLATE_FILE,
    TEMPLATE_VERSION,
    TemplateError,
    derive_profile,
    familiarity_of,
    load_template,
)
from tests.domain.persona_explanation.persona_dataset import make_rows, uuid_of

TEMPLATE = Path(__file__).resolve().parents[3] / "assets" / TEMPLATE_FILE
ROWS = {row["uuid"]: row for row in make_rows()}


def row(suffix: str) -> dict:
    return ROWS[uuid_of(suffix)]


def _write(tmp_path, raw: dict) -> Path:
    path = tmp_path / TEMPLATE_FILE
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def _raw() -> dict:
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def test_the_repository_template_is_pinned_and_ai_drafted():
    template = load_template(TEMPLATE)
    assert template.version == TEMPLATE_VERSION
    raw = _raw()
    assert raw["ai_drafted"] is True and raw["human_review"] is False


@pytest.mark.parametrize(
    ("suffix", "level"),
    [
        ("02", "높음"),  # 은행 사무원
        ("04", "높음"),  # 보험 설계사, 고등학교
        ("07", "높음"),  # 회계 사무원
        ("01", "낮음"),  # 74세, 초등학교
        ("06", "낮음"),  # 81세, 무학
        ("08", "낮음"),  # 중학교
        ("03", "보통"),
        ("05", "보통"),
        ("09", "보통"),
    ],
)
def test_familiarity_follows_occupation_then_education_and_age(suffix, level):
    assert familiarity_of(row(suffix), load_template(TEMPLATE)) == level


def test_an_old_reader_with_a_degree_is_still_low_familiarity():
    old = {**row("05"), "age": 72}
    assert familiarity_of(old, load_template(TEMPLATE)) == "낮음"


def test_derived_attributes_follow_familiarity_and_product_type():
    template = load_template(TEMPLATE)
    high = derive_profile(row("02"), "장기카드대출", template)
    low = derive_profile(row("01"), "장기카드대출", template)
    assert high["analogy_policy"] == "none" and low["analogy_policy"] == "benefit_only"
    assert high["likely_questions"] == _raw()["likely_questions"]["장기카드대출"]["높음"]
    assert low["reading_preference"] == _raw()["reading_preference"]["낮음"]
    assert 3 <= len(low["likely_questions"]) <= 5
    assert low["prohibited_assumptions"] == _raw()["prohibited_assumptions"]
    unknown = derive_profile(row("03"), None, template)
    assert unknown["likely_questions"] == _raw()["likely_questions"]["default"]["보통"]


def test_the_reader_sketch_uses_real_fields_and_the_persona_verbatim():
    reader = derive_profile(row("03"), "신용카드", load_template(TEMPLATE))["reader"]
    for value in ("23세", "여자", "2~3년제 전문대학", "간호사", "부산", "부모와 동거"):
        assert value in reader
    assert row("03")["persona"] in reader


def test_resolve_dataset_profile_has_the_legacy_shape_plus_reader():
    profile = resolve_dataset_profile(row("02"), "신용카드", TEMPLATE)
    assert set(profile) == {
        "id",
        "version",
        "source",
        "review_status",
        "status",
        "reason",
        "attributes",
    }
    assert profile["id"] == f"nemotron:{uuid_of('02')}"
    assert profile["version"] == f"t{TEMPLATE_VERSION}@{REVISION[:7]}"
    assert profile["status"] == "적용" and profile["review_status"] == "ai-drafted"
    for part in ("nvidia/Nemotron-Personas-Korea", REVISION[:7], uuid_of("02"), "CC-BY-4.0"):
        assert part in profile["source"]
    assert set(profile["attributes"]) == {
        "reading_preference",
        "financial_familiarity",
        "likely_questions",
        "prohibited_assumptions",
        "analogy_policy",
        "reader",
    }


def test_a_template_version_mismatch_makes_the_profile_invalid(tmp_path):
    raw = _raw()
    raw["version"] = TEMPLATE_VERSION + 1
    profile = resolve_dataset_profile(row("02"), "신용카드", _write(tmp_path, raw))
    assert profile["status"] == "무효" and "버전" in profile["reason"]
    assert profile["id"] == f"nemotron:{uuid_of('02')}"


def test_a_broken_template_or_row_makes_the_profile_invalid_without_raising(tmp_path):
    raw = _raw()
    del raw["likely_questions"]["default"]
    assert resolve_dataset_profile(row("02"), "신용카드", _write(tmp_path, raw))["status"] == "무효"
    missing = tmp_path / "nope.yaml"
    assert resolve_dataset_profile(row("02"), "신용카드", missing)["status"] == "무효"
    bad_row = {**row("02"), "uuid": "not-a-uuid"}
    assert resolve_dataset_profile(bad_row, "신용카드", TEMPLATE)["status"] == "무효"


def test_load_template_raises_template_error_for_a_bad_file(tmp_path):
    raw = _raw()
    raw["ai_drafted"] = False
    with pytest.raises(TemplateError):
        load_template(_write(tmp_path, raw))
