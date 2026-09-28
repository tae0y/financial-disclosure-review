"""judge_display end to end with the model faked and the fixture rubric DB."""

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.display_check import judge
from financial_disclosure_review.domain.display_check.blocks import display_blocks
from financial_disclosure_review.domain.display_check.schema import DisplayLabels, DisplayVerdicts
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import BENEFIT, FEE, FIXTURE_DIR, NOTICE, FakeAsk, make_render_page

REVOLVING = {"product_type": "리볼빙", "page_type": "업무광고"}


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    return str(path)


@pytest.fixture
def ctx(db_path) -> Context:
    return Context(model="fake", db_path=db_path)


def ids_of(page: dict) -> dict[str, str]:
    blocks, _ = display_blocks(page)
    return {block["text"]: block["id"] for block in blocks}


def fake_model(labels: dict, verdicts: list[dict]) -> FakeAsk:
    """Answers the two structured calls judge_display makes, and records what it was asked."""

    def answer(schema, data) -> dict:
        if schema is DisplayLabels:
            return labels
        if schema is DisplayVerdicts:
            return {"items": verdicts}
        raise AssertionError(f"unexpected schema {schema}")

    return FakeAsk(answer)


def labels_for(by_text: dict, *, mandatory=True) -> dict:
    return {
        "mandatory": [by_text[NOTICE]] if mandatory else [],
        "warnings": [by_text[NOTICE]],
        "rates": [],
        "benefits": [by_text[BENEFIT]],
        "penalties": [by_text[FEE]],
        "image_disclosure": [],
        "note": "",
    }


def test_only_the_items_that_apply_to_the_classification_are_judged(monkeypatch, ctx):
    page = make_render_page()
    by_text = ids_of(page)
    ask = fake_model(
        labels_for(by_text),
        [{"code": "E02", "verdict": "적합", "block_ids": [by_text[NOTICE]], "reason": "12pt"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    result = judge.judge_display(page, REVOLVING, ctx)

    assert [row["code"] for row in result["items"]] == ["E02"]
    assert result["items"][0]["verdict"] == "적합"
    assert result["judgments"]["status"] == "완료"
    assert [entry["code"] for entry in result["judgments"]["skipped"]] == ["E04"]
    assert ask.calls == ["DisplayLabels", "DisplayVerdicts"]


def test_the_measured_evidence_is_carried_into_the_row(monkeypatch, ctx):
    page = make_render_page()
    by_text = ids_of(page)
    ask = fake_model(
        labels_for(by_text),
        [{"code": "E02", "verdict": "적합", "block_ids": [by_text[NOTICE]], "reason": "12pt"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    row = judge.judge_display(page, REVOLVING, ctx)["items"][0]
    assert row["quotes"] == [NOTICE]
    assert row["measured"][0]["pt"] == 12.0
    assert row["measured"][0]["default_visible"] is True


def test_a_verdict_that_contradicts_the_measurement_is_downgraded(monkeypatch, ctx):
    page = make_render_page(notice_px=10.0)
    by_text = ids_of(page)
    ask = fake_model(
        labels_for(by_text),
        [
            {
                "code": "E02",
                "verdict": "적합",
                "block_ids": [by_text[NOTICE]],
                "reason": "괜찮습니다",
            }
        ],
    )
    monkeypatch.setattr(judge, "ask", ask)
    row = judge.judge_display(page, REVOLVING, ctx)["items"][0]
    assert row["verdict"] == "판정 불가"
    assert "failed validation twice" in row["reason"]
    assert ask.calls == ["DisplayLabels", "DisplayVerdicts", "DisplayVerdicts"]


def test_a_failure_citing_the_offending_block_is_kept(monkeypatch, ctx):
    page = make_render_page(notice_px=10.0)
    by_text = ids_of(page)
    ask = fake_model(
        labels_for(by_text),
        [{"code": "E02", "verdict": "부적합", "block_ids": [by_text[NOTICE]], "reason": "7.5pt"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    row = judge.judge_display(page, REVOLVING, ctx)["items"][0]
    assert row["verdict"] == "부적합"
    assert row["reason"] == "7.5pt"


def test_an_item_with_no_labeled_block_is_never_sent_to_the_model(monkeypatch, ctx):
    page = make_render_page()
    by_text = ids_of(page)
    ask = fake_model(labels_for(by_text, mandatory=False), [])
    monkeypatch.setattr(judge, "ask", ask)
    result = judge.judge_display(page, REVOLVING, ctx)
    row = result["items"][0]
    assert row["verdict"] == "판정 불가"
    assert "nothing to measure" in row["reason"]
    assert ask.calls == ["DisplayLabels"]


def test_a_page_with_nothing_measurable_is_unjudgeable(monkeypatch, ctx):
    page = make_render_page()
    page["snapshots"] = []
    monkeypatch.setattr(judge, "ask", fake_model({}, []))
    result = judge.judge_display(page, REVOLVING, ctx)
    assert result["items"][0]["verdict"] == "판정 불가"
    assert result["judgments"]["status"] == "판정 불가"
    assert "nothing measurable" in result["judgments"]["reason"]


def test_disclosure_text_inside_an_image_blocks_a_pass(monkeypatch, ctx):
    page = make_render_page(images='<img alt="상품설명서 확인 안내">')
    by_text = ids_of(page)
    labels = {
        **labels_for(by_text),
        "image_disclosure": [{"id": "img1", "alt_phrase": "상품설명서"}],
    }
    ask = fake_model(
        labels,
        [{"code": "E02", "verdict": "적합", "block_ids": [by_text[NOTICE]], "reason": "12pt"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    result = judge.judge_display(page, REVOLVING, ctx)
    row = result["items"][0]
    assert row["verdict"] == "판정 불가"
    assert "cannot be measured" in row["reason"]
    assert result["judgments"]["labels"]["image_disclosure"] == ["img1"]


def test_an_image_flag_whose_alt_says_nothing_about_disclosures_is_dropped(monkeypatch, ctx):
    page = make_render_page(images='<img alt="OO카드 앞면">')
    by_text = ids_of(page)
    labels = {
        **labels_for(by_text),
        "image_disclosure": [{"id": "img1", "alt_phrase": "카드 앞면"}],
    }
    ask = fake_model(
        labels,
        [{"code": "E02", "verdict": "적합", "block_ids": [by_text[NOTICE]], "reason": "12pt"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    result = judge.judge_display(page, REVOLVING, ctx)
    assert result["judgments"]["labels"]["image_disclosure"] == []
    assert result["judgments"]["labels"]["dropped_image_flags"][0]["id"] == "img1"
    assert result["items"][0]["verdict"] == "적합"


def test_the_assumptions_state_the_thresholds_the_code_applied(monkeypatch, ctx):
    page = make_render_page()
    by_text = ids_of(page)
    ask = fake_model(
        labels_for(by_text),
        [{"code": "E02", "verdict": "적합", "block_ids": [by_text[NOTICE]], "reason": "12pt"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    assumptions = judge.judge_display(page, REVOLVING, ctx)["judgments"]["assumptions"]
    assert "9pt" in assumptions["font_size"]
    assert "4.5:1" in assumptions["contrast"]
    assert set(assumptions) == {"font_size", "contrast", "hidden", "line_break", "vision"}


def test_the_model_call_cap_is_enforced(monkeypatch, db_path):
    page = make_render_page()
    by_text = ids_of(page)
    ask = fake_model(labels_for(by_text), [])
    monkeypatch.setattr(judge, "ask", ask)
    with pytest.raises(RuntimeError, match="model call cap"):
        judge.judge_display(
            page, REVOLVING, Context(model="fake", db_path=db_path, display_max_model_calls=0)
        )


@pytest.mark.parametrize("verdict", ["적합", "부적합"])
def test_undrawn_text_can_neither_pass_nor_fail_the_size_rule(monkeypatch, ctx, verdict):
    page = make_render_page(notice_px=0.0)
    by_text = ids_of(page)
    ask = fake_model(
        labels_for(by_text),
        [{"code": "E02", "verdict": verdict, "block_ids": [by_text[NOTICE]], "reason": "모델"}],
    )
    monkeypatch.setattr(judge, "ask", ask)
    row = judge.judge_display(page, REVOLVING, ctx)["items"][0]
    assert row["code"] == "E02"
    assert row["verdict"] == "판정 불가", row
