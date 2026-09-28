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
from .display_flip import run_display_flip
from .metrics import metrics_for
from .report import render
from .suites import (
    load_cases,
    run_classification,
    run_duty_flip,
    run_plain_contract,
    run_stability,
)

SUITES = ("classification", "duty-flip", "display-flip", "plain-contract", "stability")

LIMITS = [
    "표본이 작습니다. 분류 6건, 결함 주입 3건과 대조군 1건, 표시방법 2개 페이지에 주입 4건과 대조군"
    " 2건, 쉬운말 계약 케이스는 파일에 적힌 건수만큼입니다. 여기의 비율은 경향이지 신뢰구간이 붙은"
    " 성능치가 아닙니다.",
    "결함 주입의 정답은 '삭제했으므로 없다'는 사실에서 옵니다. 반대 방향(원래 없던 설명을 넣으면"
    " 적합으로 바뀌는지)은 측정하지 않았습니다.",
    "표시방법(display-flip)은 실제 검토의 렌더링 측정값을 바꾼 것이지 화면을 다시 그린 것이"
    " 아닙니다. 캡처 이미지는 내보내지 않아 이미지 위 글자는 판정 불가로 남습니다.",
    "분류 라벨은 페이지에 적힌 상품 구분을 영태가 옮겨 적은 것이고 프롬프트도 영태가 썼습니다."
    " 키워드 기준선도 6건을 모두 맞혀, 이 평가셋은 두 방식의 차이를 드러내기에 쉽습니다.",
    "쉬운말 계약 케이스는 손으로 만든 문장쌍입니다. 실제 모델이 만들어 내는 오류 분포와 같지"
    " 않을 수 있습니다.",
    "같은 입력을 세 번 판정하면 설명의무 항목의 약 28%가 다른 답을 냅니다(stability 스위트)."
    " 한 번의 실행 결과를 확정 판정으로 읽으면 안 됩니다.",
]


def _fixtures() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "classify"


def default_eval_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "eval"


def run_evaluation(
    ctx: Context,
    suites: tuple[str, ...] = SUITES,
    mode: str = "replay",
    eval_dir: str | Path | None = None,
    max_flips: int = 3,
    arms: tuple[str, ...] = ("pipeline", "ablation"),
    repeats: int = 3,
) -> dict[str, Any]:
    """Run the named suites and return the whole run as data. Caller writes it out."""
    root = Path(eval_dir) if eval_dir else default_eval_dir()
    meter = start_run(max_calls=80, max_usd=1.0)
    cassette = Cassette(root / "cassettes" / f"{ctx.model}.json", mode=mode)
    results = []
    try:
        _run_suites(ctx, suites, root, cassette, results, max_flips, arms, repeats)
    finally:
        # Paid answers are kept even when a suite stops halfway, so the rerun replays them.
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


def _run_suites(
    ctx: Context,
    suites: tuple[str, ...],
    root: Path,
    cassette: Cassette,
    results: list[dict],
    max_flips: int,
    arms: tuple[str, ...],
    repeats: int,
) -> None:
    if "classification" in suites:
        results.append(run_classification(ctx, cassette, _fixtures()))
        if "ablation" in arms:
            results.append(run_classification(ctx, cassette, _fixtures(), arm="keyword"))
    if "duty-flip" in suites:
        config = load_cases(root / "cases" / "duty_flip.json")
        config["base_html"] = str(
            (Path(__file__).resolve().parents[3] / config["base_html"]).resolve()
        )
        for arm in arms:
            results.append(run_duty_flip(ctx, cassette, config, arm=arm, max_flips=max_flips))
    if "display-flip" in suites:
        config = load_cases(root / "cases" / "display_flip.json")
        repo = Path(__file__).resolve().parents[3]
        results.append(run_display_flip(ctx, cassette, config, repo))
        if "ablation" in arms:
            results.append(run_display_flip(ctx, cassette, config, repo, arm="rules"))
    if "plain-contract" in suites:
        cases = load_cases(root / "cases" / "plain_contract.json")
        results.append(run_plain_contract(ctx, cassette, cases["cases"]))
    if "stability" in suites:
        config = load_cases(root / "cases" / "duty_flip.json")
        config["base_html"] = str(
            (Path(__file__).resolve().parents[3] / config["base_html"]).resolve()
        )
        results.append(run_stability(ctx, cassette, _fixtures(), config, repeats, arms))


__all__ = ["LIMITS", "SUITES", "default_eval_dir", "render", "run_evaluation"]
