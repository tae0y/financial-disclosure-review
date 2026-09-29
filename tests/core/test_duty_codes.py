import yaml

from financial_disclosure_review.core.duty_codes import DUTY_TWINS, duty_topic
from tests.helpers import FIXTURE_DIR

ROOT = FIXTURE_DIR.parents[1]


def _criteria(name: str, prefix: str) -> dict[str, str]:
    data = yaml.safe_load((ROOT / "assets" / name).read_text(encoding="utf-8"))
    items = data.get("items", data) if isinstance(data, dict) else data
    return {
        i["code"]: " ".join(i["criterion"].split()) for i in items if i["code"].startswith(prefix)
    }


def test_every_word_for_word_twin_is_in_the_table():
    f_items = _criteria("card_guardrail_rubric.yaml", "F")
    duty_items = _criteria("plain_service_rubric.yaml", "설명")
    same = {f: d for f, c in f_items.items() for d, e in duty_items.items() if c == e}
    assert same and all(DUTY_TWINS[f] == d for f, d in same.items())


def test_codes_without_a_twin_are_their_own_topic():
    assert duty_topic("F20") == "F20"
    assert duty_topic("설명07") == "설명07"
    assert duty_topic("F21") == "설명27"
