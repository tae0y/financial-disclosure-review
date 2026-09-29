"""Fixture loading, State building and the fake ask used in place of a real model call."""

import json
from pathlib import Path
from typing import Any

from financial_disclosure_review.core.state import State, empty_state
from financial_disclosure_review.core.text import visible_text
from financial_disclosure_review.domain.classification.schema import VerifyAnswer
from financial_disclosure_review.domain.classification.stages import FIELDS_AFTER_STAGE, STAGES

FIXTURE_DIR = Path(__file__).parent / "fixtures"
# Captured third-party pages are gitignored; a clone gets them from the submission zip.
CLASSIFY_MISSING = "tests/fixtures/classify/ is gitignored and missing locally"


def load_classify_fixtures() -> dict[str, dict]:
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted((FIXTURE_DIR / "classify").glob("*.json"))
    }


def page_of(fixture: dict) -> dict:
    return {key: fixture[key] for key in ("url", "product", "html")}


class FakeAsk:
    """Stands in for llm.client.ask and records the schema of every call it answered."""

    def __init__(self, answer):
        self.answer = answer
        self.calls: list[str] = []

    def __call__(self, model, schema, task, effort="low", **data):
        self.calls.append(schema.__name__)
        return self.answer(schema, data)


def make_fake_ask(
    fixture: dict, *, stage=None, verify="아니오", quote=None, reason="이유"
) -> FakeAsk:
    """fixture의 기대 답을 돌려주는 가짜 ask. 인자로 실패 상황을 흉내 낸다."""
    text = visible_text(fixture["html"])
    good = quote if quote is not None else text[: min(40, len(text))]
    fail = stage if stage is not None else fixture["expected"].get("stage")

    def answer(schema, data) -> dict:
        if schema is VerifyAnswer:
            return {"reason": "발췌 근거", "answer": verify}
        given = {
            "single_product_quote": good,
            "single_product_reason": reason,
            "single_product": True,
            "loan_product_quote": good,
            "loan_product_reason": reason,
            "loan_product": True,
            "evidence": good,
            "product_type_reason": reason,
            "product_type": fixture["expected"]["product_type"] if fail is None else None,
            "page_subject": "페이지 주제",
            "confidence": "high",
        }
        if fail:
            given[STAGES[fail - 1][0]] = False
            for key in FIELDS_AFTER_STAGE[fail]:
                given[key] = None
        return given

    return FakeAsk(answer)


def state_with(**keys: Any) -> State:
    """A full State with the given module keys filled in; the rest stay empty."""
    state = empty_state()
    state.update(keys)  # type: ignore[typeddict-item]
    return state


TITLE = "테스트 신용카드"
BENEFIT = "커피 전문점에서 10% 할인"
NOTICE = "※ 연체 시 신용평점이 하락할 수 있습니다."
FEE = "연회비는 연 1만원입니다."

RENDER_HTML = (
    '<section data-selector="article#product" data-state="0">'
    f"<h1>{TITLE}</h1><p>{BENEFIT}</p><p>{NOTICE}</p><p>{FEE}</p>"
    "</section>"
)


def style_row(
    path: str,
    text: str,
    *,
    px: float = 16.0,
    weight: int = 400,
    color: str = "rgb(17, 17, 17)",
    background: str = "rgb(255, 255, 255)",
    visible: bool = True,
    visual_risk: list[str] | None = None,
) -> dict:
    return {
        "tag": "p",
        "text": text,
        "font_size": f"{px}px",
        "font_weight": str(weight),
        "color": color,
        "visible": visible,
        "bounds": [0.0, 0.0, 600.0, 20.0],
        "path": path,
        "background": background,
        "background_source": "ancestor",
        "background_image": bool(visual_risk),
        "visual_risk": visual_risk or [],
    }


def render_snapshot(kind: str, note: str, rows: list[dict], number: int = 1) -> dict:
    return {
        "id": number,
        "phase": "render",
        "kind": kind,
        "note": note,
        "url": "https://example.test/product",
        "viewport": {"width": 1280, "height": 800},
        "document": {"width": 1280, "height": 2000},
        "html_path": "",
        "styles": rows,
        "images": [],
        "visual_samples": {},
    }


def make_render_page(notice_px: float = 16.0, *, html: str = RENDER_HTML, images: str = "") -> dict:
    """A product_page State value with one default and one expanded render snapshot."""
    default_rows = [
        style_row("html > h1:nth-of-type(1)", TITLE, px=24.0, weight=700),
        style_row("html > p:nth-of-type(1)", BENEFIT, px=18.0, weight=700),
        style_row("html > p:nth-of-type(2)", NOTICE, px=notice_px),
        style_row("html > p:nth-of-type(3)", FEE, px=notice_px, visible=False),
    ]
    expanded_rows = [
        {**row, "visible": True} if row["text"] == FEE else row for row in default_rows
    ]
    return {
        "url": "https://example.test/product",
        "product": {"product_name": TITLE, "summary": "", "evidence": []},
        "actions": [{"type": "reuse"}, {"type": "result"}],
        "snapshots": [
            render_snapshot("default", "arrived", default_rows, 1),
            render_snapshot("expanded", "expand button.tab-toggle", expanded_rows, 2),
        ],
        "html": html + images,
    }

    @property
    def texts(self) -> list[str]:
        return [text for batch in self.batches for text in batch]
