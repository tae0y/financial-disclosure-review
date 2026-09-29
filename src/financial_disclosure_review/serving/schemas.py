"""Request/response bodies shared by gateway and worker — a narrowed view of State, not raw HTML."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class Detail(str, Enum):
    """How much of a finished run to return."""

    summary = "summary"
    full = "full"


class PersonaRequest(BaseModel):
    """Who the reader-tailored explanation is written for. Every field is nullable; null, an
    empty string and an `attributes` object whose values are all null mean "not given". The
    first one given wins: `uuid`, then `attributes`, then free-text `request`. Nothing given:
    the product type's default reader. An invalid value never fails the run; the report says
    what was used instead."""

    request: str | None = Field(
        default=None,
        max_length=300,
        description="Free text, e.g. '70대 은퇴자, 카드론을 처음 알아보는 사람'",
    )
    uuid: str | None = Field(
        default=None, pattern=r"^([0-9a-f]{32})?$", description="One exact dataset row"
    )
    attributes: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Dataset filters: age_min, age_max, sex, education_level, occupation_contains,"
            " province, family_type, housing_type, marital_status. Null values are ignored"
        ),
    )


class ReviewRequest(BaseModel):
    """One product page to review. Everything but `url` falls back to the process defaults."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"url": "https://www.example-card.co.kr/product/credit/apply"},
                {
                    "url": "https://www.example-card.co.kr/product/credit/apply",
                    "model": "gpt-5",
                    "detail": "full",
                    "max_usd": 2.0,
                    "persona": {"request": "70대 은퇴자, 카드론을 처음 알아보는 사람"},
                },
            ]
        }
    }

    url: HttpUrl
    model: str | None = Field(default=None, description="Overrides FDR_MODEL, e.g. gpt-5-mini")
    thread_id: str | None = Field(
        default=None,
        max_length=120,
        description="Checkpoint thread to write; a timestamped one when omitted",
    )
    detail: Detail = Detail.summary
    max_calls: int | None = Field(default=None, ge=1, le=500)
    max_usd: float | None = Field(default=None, gt=0, le=50)
    persona: PersonaRequest | None = None


class RerunRequest(BaseModel):
    """Re-run an existing checkpoint thread from one node onward."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "thread_id": "review-260927-101500-a1b2c3",
                    "from_node": "judge_display_method",
                }
            ]
        }
    }

    thread_id: str = Field(max_length=120)
    from_node: str = Field(
        max_length=80,
        description=(
            "A graph node name: preprocess_product_page, classify_type, extract_evidence_cards, "
            "retrieve_reference_cases, judge_display_method, generate_persona_explanation, "
            "judge_explanation_duty, verify_answer, end_report."
        ),
    )
    model: str | None = None
    detail: Detail = Detail.summary
    max_calls: int | None = Field(default=None, ge=1, le=500)
    max_usd: float | None = Field(default=None, gt=0, le=50)


class RunResult(BaseModel):
    """What the worker hands back for a finished run."""

    thread_id: str
    url: str | None = None
    status: str | None = Field(default=None, description="report.status, e.g. 검토 완료")
    decision: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    report: dict[str, Any] = Field(default_factory=dict)
    cost: dict[str, Any] = Field(default_factory=dict)
    elapsed_seconds: float = 0.0


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    interrupted = "interrupted"


TERMINAL = frozenset({JobStatus.succeeded, JobStatus.failed, JobStatus.interrupted})


class Job(BaseModel):
    """A queued or finished review, as the gateway records it."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "82653a02438f4ce4b8bbc5524ea9d711",
                    "status": "failed",
                    "kind": "review",
                    "url": "https://www.example-card.co.kr/product/credit/apply",
                    "thread_id": None,
                    "model": None,
                    "created_at": "2026-09-27T08:44:35.297258Z",
                    "started_at": "2026-09-27T08:44:35.302597Z",
                    "finished_at": "2026-09-27T08:44:36.678295Z",
                    "error": "worker returned 500: PageBlocked: navigation failed",
                    "result": None,
                }
            ]
        }
    }

    job_id: str
    status: JobStatus
    kind: Literal["review", "rerun"] = "review"
    url: str | None = None
    thread_id: str | None = None
    model: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: RunResult | None = None


class JobAccepted(BaseModel):
    """The 202 body: enough to poll with, nothing more."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "82653a02438f4ce4b8bbc5524ea9d711",
                    "status": "queued",
                    "poll": "/v1/reviews/82653a02438f4ce4b8bbc5524ea9d711",
                }
            ]
        }
    }

    job_id: str
    status: JobStatus
    poll: str


class JobList(BaseModel):
    jobs: list[Job]
    count: int


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    detail: dict[str, Any] = Field(default_factory=dict)
