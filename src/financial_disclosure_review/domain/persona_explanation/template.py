"""Reading attributes derived from one dataset row by the fixed rules of persona_template.yaml."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .dataset import Filters

TEMPLATE_FILE = "persona_template.yaml"
# Version pin of the template, like profiles.PROFILE_ALLOWLIST: a file with another version is
# refused, so editing the derivation rules requires bumping both places.
TEMPLATE_VERSION = 1
LEVELS = ("낮음", "보통", "높음")
Level = Literal["낮음", "보통", "높음"]


class TemplateError(ValueError):
    """The template file is unreadable, malformed or of another version."""


class FamiliarityRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    high_occupation_terms: list[str] = Field(min_length=1)
    low_education: list[str]
    low_age_min: int


class PersonaTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    ai_drafted: Literal[True]
    human_review: bool
    familiarity: FamiliarityRule
    reading_preference: dict[Level, str]
    analogy_policy: dict[Level, Literal["none", "benefit_only"]]
    prohibited_assumptions: list[str] = Field(min_length=1)
    likely_questions: dict[str, dict[Level, list[str]]]
    default_filters: dict[str, Filters]

    @model_validator(mode="after")
    def _complete(self) -> "PersonaTemplate":
        for name, table in (
            ("reading_preference", self.reading_preference),
            ("analogy_policy", self.analogy_policy),
            *((f"likely_questions.{k}", v) for k, v in self.likely_questions.items()),
        ):
            if set(table) != set(LEVELS):
                raise ValueError(f"{name} needs exactly the levels {LEVELS}")
        for product, table in self.likely_questions.items():
            for level, questions in table.items():
                if not 3 <= len(questions) <= 5:
                    raise ValueError(f"likely_questions.{product}.{level} needs 3-5 questions")
        for name, table in (
            ("likely_questions", self.likely_questions),
            ("default_filters", self.default_filters),
        ):
            if "default" not in table:
                raise ValueError(f"{name} needs a default entry")
        return self


def default_template_path(rubric_dir: str | Path) -> Path:
    return Path(rubric_dir) / TEMPLATE_FILE


def load_template(path: str | Path) -> PersonaTemplate:
    """The validated template; TemplateError (Korean reason) for anything else."""
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise TemplateError(f"템플릿 파일을 읽을 수 없음: {type(error).__name__}") from error
    try:
        template = PersonaTemplate.model_validate(raw)
    except ValidationError as error:
        fields = sorted({".".join(str(p) for p in e["loc"]) or "root" for e in error.errors()})
        raise TemplateError(f"템플릿 스키마 오류: {', '.join(fields)}") from error
    if template.version != TEMPLATE_VERSION:
        raise TemplateError(f"템플릿 버전 불일치: 파일 {template.version}, 코드 {TEMPLATE_VERSION}")
    return template


def familiarity_of(row: Mapping[str, Any], template: PersonaTemplate) -> Level:
    """높음 for a finance occupation; else 낮음 for little schooling or old age; else 보통."""
    rule = template.familiarity
    occupation = row.get("occupation") or ""
    if any(term in occupation for term in rule.high_occupation_terms):
        return "높음"
    age = row.get("age")
    if row.get("education_level") in rule.low_education or (
        isinstance(age, int) and age >= rule.low_age_min
    ):
        return "낮음"
    return "보통"


def reader_sketch(row: Mapping[str, Any]) -> str:
    """Who the reader is, from the row's real fields, then the row's persona sentence verbatim."""
    parts = [
        f"{row.get('age')}세 {row.get('sex')}",
        f"학력 {row.get('education_level')}",
        f"직업 {row.get('occupation')}",
        f"{row.get('province')} 거주",
        f"가구 {row.get('family_type')}",
    ]
    return " · ".join(parts) + "\n" + (row.get("persona") or "")


def derive_profile(
    row: Mapping[str, Any],
    product_type: str | None,
    template: PersonaTemplate,
    familiarity: Level | None = None,
) -> dict:
    """The reading attributes of one row, the same shape as a legacy profile plus `reader`.

    `familiarity` is what the reviewer's own words said about the reader (the selection
    agent's hint); it wins over the row-based estimate, which only guesses from schooling, age
    and occupation. `familiarity_source` records which one was used."""
    level = familiarity or familiarity_of(row, template)
    questions = (
        template.likely_questions.get(product_type or "") or template.likely_questions["default"]
    )
    return {
        "reading_preference": template.reading_preference[level],
        "financial_familiarity": level,
        "likely_questions": list(questions[level]),
        "prohibited_assumptions": list(template.prohibited_assumptions),
        "analogy_policy": template.analogy_policy[level],
        "familiarity_source": "request" if familiarity else "row",
        "reader": reader_sketch(row),
    }


def default_filters(product_type: str | None, template: PersonaTemplate) -> Filters:
    return template.default_filters.get(product_type or "") or template.default_filters["default"]
