"""resolve_profile: only allowlisted, version-pinned, valid profiles are 적용; it never raises."""

import pytest
import yaml

from financial_disclosure_review.domain.persona_explanation.profiles import (
    PROFILE_ALLOWLIST,
    resolve_profile,
)
from tests.domain.persona_explanation.persona_fixtures import (
    FIRSTCARD,
    LOANFAMILIAR,
    LOWFIN,
    PROFILES,
)


def _raw() -> dict:
    return yaml.safe_load(PROFILES.read_text(encoding="utf-8"))


def _write(tmp_path, raw) -> str:
    path = tmp_path / "persona_profiles.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return str(path)


def test_the_repository_file_holds_exactly_the_allowlisted_profiles():
    raw = _raw()
    assert {p["id"]: p["version"] for p in raw["profiles"]} == PROFILE_ALLOWLIST
    assert raw["default"] in PROFILE_ALLOWLIST
    for profile_id in PROFILE_ALLOWLIST:
        assert resolve_profile(profile_id, PROFILES)["status"] == "적용"


def test_every_profile_names_its_source_row_and_stays_ai_drafted():
    for p in _raw()["profiles"]:
        assert p["source"]["dataset"] == "nvidia/Nemotron-Personas-Korea"
        assert p["source"]["license"] == "CC-BY-4.0"
        assert len(p["source"]["uuid"]) == 32
        assert p["review_status"] == "ai-drafted"
        assert 3 <= len(p["likely_questions"]) <= 5
        # The persona prose itself is never copied into the repository.
        assert "persona" not in p


def test_an_empty_id_picks_the_default_and_exposes_only_derived_attributes():
    profile = resolve_profile("", PROFILES)
    assert profile["id"] == LOWFIN
    assert profile["status"] == "적용"
    assert profile["source"].startswith("nvidia/Nemotron-Personas-Korea uuid=")
    assert set(profile["attributes"]) == {
        "reading_preference",
        "financial_familiarity",
        "likely_questions",
        "prohibited_assumptions",
        "analogy_policy",
    }


def test_the_analogy_policies_differ_by_reader():
    policies = {
        pid: resolve_profile(pid, PROFILES)["attributes"]["analogy_policy"]
        for pid in (LOWFIN, FIRSTCARD, LOANFAMILIAR)
    }
    assert policies == {LOWFIN: "benefit_only", FIRSTCARD: "benefit_only", LOANFAMILIAR: "none"}


def test_an_id_outside_the_allowlist_is_invalid():
    profile = resolve_profile("someone-else", PROFILES)
    assert profile["status"] == "무효"
    assert "허용목록" in profile["reason"]
    assert profile["attributes"] == {}


def test_a_version_mismatch_is_invalid(tmp_path):
    raw = _raw()
    for p in raw["profiles"]:
        p["version"] = 2
    profile = resolve_profile(LOWFIN, _write(tmp_path, raw))
    assert profile["status"] == "무효"
    assert "버전" in profile["reason"]


@pytest.mark.parametrize(
    "breakage",
    [
        lambda p: p.pop("analogy_policy"),
        lambda p: p.update(analogy_policy="always"),
        lambda p: p.update(likely_questions=["하나"]),
        lambda p: p["source"].update(uuid="not-a-uuid"),
        lambda p: p.update(extra_field="x"),
    ],
)
def test_a_schema_error_is_invalid(tmp_path, breakage):
    raw = _raw()
    breakage(next(p for p in raw["profiles"] if p["id"] == LOWFIN))
    profile = resolve_profile(LOWFIN, _write(tmp_path, raw))
    assert profile["status"] == "무효"
    assert "스키마" in profile["reason"]


def test_a_missing_or_broken_file_is_invalid_not_an_exception(tmp_path):
    assert resolve_profile(LOWFIN, tmp_path / "missing.yaml")["status"] == "무효"
    broken = tmp_path / "broken.yaml"
    broken.write_text("profiles: [unclosed", encoding="utf-8")
    assert resolve_profile(LOWFIN, broken)["status"] == "무효"
    no_list = tmp_path / "no_list.yaml"
    no_list.write_text("default: x\n", encoding="utf-8")
    assert resolve_profile(None, no_list)["status"] == "무효"


def test_a_duplicated_id_is_invalid(tmp_path):
    raw = _raw()
    raw["profiles"].append(dict(raw["profiles"][0]))
    assert resolve_profile(raw["profiles"][0]["id"], _write(tmp_path, raw))["status"] == "무효"
