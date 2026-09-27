"""Running the evaluation suites and writing the result.

Not a graph domain: nothing here is part of a review. It is the measurement harness, so it may
read the domains but no domain may read it.

Two modes matter. `--live --record` pays for the model once and writes every answer to a
cassette; the default `replay` re-derives the same table from that cassette for free. A reader
who wants to check a number runs the free path.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.context import Context
from ..core.usage import current, start_run
from .cassette import Cassette
from .metrics import metrics_for
from .report import render
from .suites import load_cases, run_classification, run_duty_flip, run_plain_contract

SUITES = ("classification", "duty-flip", "plain-contract")

LIMITS = [
    "표본이 작습니다. 분류 6건, 결함 주입 3건과 대조군 1건, 쉬운말 계약 케이스는 파일에 적힌"
    " 건수만큼입니다. 여기의 비율은 경향이지 신뢰구간이 붙은 성능치가 아닙니다.",
    "결함 주입의 정답은 '삭제했으므로 없다'는 사실에서 옵니다. 반대 방향(원래 없던 설명을 넣으면"
    " 적합으로 바뀌는지)은 측정하지 않았습니다.",
    "표시방법(display_check)은 이 평가에 포함되지 않습니다. 렌더링된 화면 측정이 필요해"
    " 결함 주입으로 정답을 만들 수 없었습니다.",
    "분류 라벨은 영태가 직접 붙였습니다. 라벨을 만든 사람과 프롬프트를 쓴 사람이 같으므로"
    " 완전히 독립된 평가셋은 아닙니다.",
    "쉬운말 계약 케이스는 손으로 만든 문장쌍입니다. 실제 모델이 만들어 내는 오류 분포와 같지"
    " 않을 수 있습니다.",
]


def default_eval_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "eval"


def run_evaluation(
    ctx: Context,
    suites: tuple[str, ...] = SUITES,
    mode: str = "replay",
    eval_dir: str | Path | None = None,
    max_flips: int = 3,
    arms: tuple[str, ...] = ("pipeline", "ablation"),
) -> dict[str, Any]:
    """Run the named suites and return the whole run as data. Caller writes it out."""
    root = Path(eval_dir) if eval_dir else default_eval_dir()
    meter = start_run(max_calls=80, max_usd=1.0)
    cassette = Cassette(root / "cassettes" / f"{ctx.model}.json", mode=mode)
    results = []

    if "classification" in suites:
        fixtures = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "classify"
        results.append(run_classification(ctx, cassette, fixtures))
    if "duty-flip" in suites:
        config = load_cases(root / "cases" / "duty_flip.json")
        config["base_html"] = str(
            (Path(__file__).resolve().parents[3] / config["base_html"]).resolve()
        )
        for arm in arms:
            results.append(run_duty_flip(ctx, cassette, config, arm=arm, max_flips=max_flips))
    if "plain-contract" in suites:
        cases = load_cases(root / "cases" / "plain_contract.json")
        results.append(run_plain_contract(cases["cases"]))

    saved = cassette.save()
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": ctx.model,
        "mode": mode,
        "cassette": {**cassette.stats(), "saved": saved},
        "suites": [{"result": result, "metrics": metrics_for(result)} for result in results],
        "cost": (meter if meter is current() else current()).summary(),
        "limits": LIMITS,
    }


__all__ = ["LIMITS", "SUITES", "default_eval_dir", "render", "run_evaluation"]
