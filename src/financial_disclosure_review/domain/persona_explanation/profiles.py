"""Loading the reviewed reader profiles; anything unexpected yields an invalid one, never raises."""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ...core.context import default_rubric_dir
from . import dataset
from .template import TEMPLATE_VERSION, TemplateError, derive_profile, load_template

PROFILES_FILE = "persona_profiles.yaml"
# Version pin of every profile the node may use. A profile whose id is missing here, or whose
# yaml version differs, is 무효: editing a profile's content requires bumping both places.
PROFILE_ALLOWLIST: dict[str, int] = {
    "nemotron-ko-70s-lowfin": 1,
    "nemotron-ko-20s-firstcard": 1,
    "nemotron-ko-40s-loanfamiliar": 1,
}
DATASET = dataset.DATASET
UUID_RE = re.compile(r"^[0-9a-f]{32}$")


class ProfileSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: Literal["nvidia/Nemotron-Personas-Korea"]
    license: Literal["CC-BY-4.0"]
    uuid: str = Field(pattern=r"^[0-9a-f]{32}$")


class PersonaProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    version: int
    source: ProfileSource
    review_status: Literal["ai-drafted", "human-reviewed"]
    basis: str = ""
    reading_preference: str = Field(min_length=1)
    financial_familiarity: Literal["낮음", "보통", "높음"]
    likely_questions: list[str] = Field(min_length=3, max_length=5)
    prohibited_assumptions: list[str] = Field(min_length=1)
    analogy_policy: Literal["none", "benefit_only"]


def default_profiles_path() -> Path:
    return Path(default_rubric_dir()) / PROFILES_FILE


def _invalid(profile_id: str, reason: str) -> dict:
    return {
        "id": profile_id,
        "version": None,
        "source": "",
        "review_status": "",
        "status": "무효",
        "reason": reason,
        "attributes": {},
    }


def resolve_profile(profile_id: str | None = None, path: str | Path | None = None) -> dict:
    """The profile to explain for, as {id, version, source, review_status, status, reason,
    attributes}. status is 적용 or 무효; an empty/None id picks the file's `default`."""
    file = Path(path) if path else default_profiles_path()
    try:
        raw = yaml.safe_load(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return _invalid(profile_id or "", f"프로필 파일을 읽을 수 없음: {type(error).__name__}")
    if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), list):
        return _invalid(profile_id or "", "프로필 파일 형식 오류: profiles 목록 없음")

    wanted = profile_id or raw.get("default") or ""
    if not isinstance(wanted, str) or not wanted:
        return _invalid("", "프로필 id가 없고 파일의 default도 없음")
    if wanted not in PROFILE_ALLOWLIST:
        return _invalid(wanted, "허용목록에 없는 프로필 id")

    entries = [p for p in raw["profiles"] if isinstance(p, dict) and p.get("id") == wanted]
    if len(entries) != 1:
        return _invalid(
            wanted, f"프로필 파일에서 id가 {len(entries)}번 발견됨(정확히 1번이어야 함)"
        )
    try:
        profile = PersonaProfile.model_validate(entries[0])
    except ValidationError as error:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in error.errors()})
        return _invalid(wanted, f"프로필 스키마 오류: {', '.join(fields)}")
    if profile.version != PROFILE_ALLOWLIST[wanted]:
        return _invalid(
            wanted,
            f"프로필 버전 불일치: 파일 {profile.version}, 허용목록 {PROFILE_ALLOWLIST[wanted]}",
        )

    attributes = profile.model_dump(
        include={
            "reading_preference",
            "financial_familiarity",
            "likely_questions",
            "prohibited_assumptions",
            "analogy_policy",
        }
    )
    return {
        "id": profile.id,
        "version": profile.version,
        "source": f"{DATASET} uuid={profile.source.uuid} ({profile.source.license})",
        "review_status": profile.review_status,
        "status": "적용",
        "reason": "",
        "attributes": attributes,
    }


def dataset_profile_version() -> str:
    """Template version and dataset revision together: either change makes a new profile."""
    return f"t{TEMPLATE_VERSION}@{dataset.REVISION[:7]}"


def resolve_dataset_profile(
    row: Mapping[str, Any],
    product_type: str | None,
    template_path: str | Path,
    familiarity: Literal["낮음", "보통", "높음"] | None = None,
) -> dict:
    """The profile of one dataset row, in the shape of resolve_profile plus attributes.reader.

    Derived by the template's fixed rules; an unreadable or other-version template, or a row
    without a proper uuid, gives a 무효 profile instead of raising.
    """
    uuid = str(row.get("uuid") or "")
    profile_id = f"nemotron:{uuid}"
    if not UUID_RE.match(uuid):
        return _invalid(profile_id, "데이터셋 행의 uuid 형식 오류")
    try:
        template = load_template(template_path)
    except TemplateError as error:
        return _invalid(profile_id, str(error))
    return {
        "id": profile_id,
        "version": dataset_profile_version(),
        "source": (f"{DATASET} rev={dataset.REVISION[:7]} uuid={uuid} ({dataset.LICENSE})"),
        "review_status": "ai-drafted",
        "status": "적용",
        "reason": "",
        "attributes": derive_profile(row, product_type, template, familiarity),
    }
