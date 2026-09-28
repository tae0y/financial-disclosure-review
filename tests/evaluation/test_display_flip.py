"""display-flip with the model faked: the mutation lands, the rules arm blames anything under the
threshold, and the pipeline arm blames only the text it labelled as a mandatory disclosure."""

import json

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.display_codes import VIOLATION_KEYS
from financial_disclosure_review.domain.display_check.blocks import display_blocks
from financial_disclosure_review.domain.display_check.schema import DisplayLabels, DisplayVerdicts
from financial_disclosure_review.evaluation.cassette import Cassette
from financial_disclosure_review.evaluation.display_flip import (
    mutate,
    rules_verdicts,
    run_display_flip,
)
from financial_disclosure_review.evaluation.metrics import metrics_for
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import BENEFIT, FIXTURE_DIR, NOTICE, FakeAsk, make_render_page

SHRINK = {"font_size": "9px"}
REVOLVING = {"product_type": "리볼빙", "page_type": "업무광고"}


@pytest.fixture(scope="module")
def ctx(tmp_path_factory) -> Context:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    return Context(model="fake", db_path=str(path))


def compliant_model() -> FakeAsk:
    """Labels the notice as the mandatory text, and judges each item exactly as the measures say:
    a model that makes no mistake, so what is tested is the harness around it."""

    def answer(schema, data) -> dict:
        if schema is DisplayLabels:
            notice = next(line.split("|")[0] for line in data["blocks"] if NOTICE[:10] in line)
            return {
                "mandatory": [notice],
                "warnings": [notice],
                "rates": [],
                "benefits": [],
                "penalties": [],
                "image_disclosure": [],
                "note": "",
            }
        assert schema is DisplayVerdicts
        verdicts = []
        for code, item in data["items"].items():
            ids = [line.split("|")[0] for line in item["blocks"]]
            key = VIOLATION_KEYS.get(code)
            failing = (item["measures"] or {}).get(key) or [] if key else []
            verdicts.append(
                {
                    "code": code,
                    "verdict": "부적합" if failing else "적합",
                    "block_ids": failing or ids[:1],
                    "reason": "측정값대로",
                }
            )
        return {"items": verdicts}

    return FakeAsk(answer)


def test_a_mutation_changes_every_capture_of_that_text_and_nothing_else():
    page = make_render_page()
    variant, changed = mutate(page, NOTICE, SHRINK)
    assert changed == 2, "both the default and the expanded capture hold the notice"
    blocks = {b["text"]: b for b in display_blocks(variant)[0]}
    assert blocks[NOTICE]["pt"] == 6.75
    assert blocks[BENEFIT]["pt"] == 13.5, "the other blocks keep their measurements"
    assert {b["text"]: b for b in display_blocks(page)[0]}[NOTICE]["pt"] == 12.0, "a copy"


def test_text_that_is_not_on_the_page_does_not_land():
    _, changed = mutate(make_render_page(), "이 문장은 페이지에 없습니다", SHRINK)
    assert changed == 0


def test_the_rules_arm_fails_the_item_for_any_small_text(ctx):
    base = rules_verdicts(make_render_page(), ctx)
    assert base["E02"]["verdict"] == "적합"
    shrunk, _ = mutate(make_render_page(), BENEFIT, SHRINK)
    after = rules_verdicts(shrunk, ctx)
    assert after["E02"]["verdict"] == "부적합", "no notion of which text is mandatory"


def run(tmp_path, ctx, arm: str) -> dict:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps({"page": make_render_page(), "classification": REVOLVING}, ensure_ascii=False),
        encoding="utf-8",
    )
    config = {
        "mutations": {"shrink": SHRINK},
        "pages": [
            {
                "id": "p",
                "fixture": "fixture.json",
                "watch": "E02",
                "cases": [
                    {"id": "shrink-notice", "kind": "shrink", "rubric": "A11", "text": NOTICE},
                    {"id": "shrink-control", "kind": "shrink", "rubric": None, "text": BENEFIT},
                ],
            }
        ],
    }
    cassette = Cassette(tmp_path / "c.json", mode="live", ask=compliant_model())
    return metrics_for(run_display_flip(ctx, cassette, config, tmp_path, arm=arm))


def test_the_pipeline_catches_the_shrunk_disclosure_and_leaves_the_control_alone(tmp_path, ctx):
    metrics = run(tmp_path, ctx, "pipeline")
    assert metrics["detected"] == 1 and metrics["injected"] == 1
    assert metrics["blamed_controls"] == 0 and metrics["controls"] == 1
    assert metrics["base_verdicts"] == {"p": "E02 적합"}


def test_the_rules_arm_catches_it_too_but_blames_the_control(tmp_path, ctx):
    metrics = run(tmp_path, ctx, "rules")
    assert metrics["detected"] == 1
    assert metrics["blamed_controls"] == 1
