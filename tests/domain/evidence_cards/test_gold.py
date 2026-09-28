"""Free (offline) check that every gold quote actually resolves in its fixture's page text.

eval/fixtures/ is gitignored in the public repo, so both the real lottecard pages and this gold
set (eval/fixtures/gold/evidence_cards.json) exist only on a working machine. When either is
missing, this test skips instead of failing, so a fresh clone stays green.
"""

import json
from pathlib import Path

import pytest

from financial_disclosure_review.core.text import locate_quote, visible_text

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_PATH = REPO_ROOT / "eval" / "fixtures" / "gold" / "evidence_cards.json"
FIXTURE_DIR = REPO_ROOT / "eval" / "fixtures"


def _load_gold() -> dict:
    if not GOLD_PATH.exists():
        pytest.skip(f"local-only gold set missing: {GOLD_PATH}")
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def _fixture_texts(entries: list[dict]) -> dict[str, str]:
    fixtures = sorted({e["fixture"] for e in entries})
    missing = [f for f in fixtures if not (FIXTURE_DIR / f"{f}.json").exists()]
    if missing:
        pytest.skip(f"eval/fixtures/ is gitignored and missing locally: {missing}")
    texts = {}
    for name in fixtures:
        data = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
        texts[name] = visible_text(data["page"]["html"])
    return texts


def test_gold_file_flags_are_ai_drafted():
    gold = _load_gold()
    assert gold["ai_drafted"] is True
    assert gold["human_review"] is False


def test_gold_quotes_resolve_in_their_fixture_page_text():
    gold = _load_gold()
    entries = gold["entries"]
    assert 8 <= sum(1 for e in entries if e["fixture"] == "display_lottecard_card_loan") <= 15
    assert 8 <= sum(1 for e in entries if e["fixture"] == "display_lottecard_loca_classic") <= 15

    texts = _fixture_texts(entries)
    for entry in entries:
        text = texts[entry["fixture"]]
        assert locate_quote(text, entry["quote"]) is not None, (
            f"gold quote not found in {entry['fixture']}: {entry['quote']!r}"
        )
