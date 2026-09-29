"""Which dataset row the explanation is written for, and the profile derived from it.

Precedence: an exact uuid, then attributes (filters), then free text turned into filters by a
small bounded tool loop, then the product type's default filters. The model only proposes
filters; code validates every value against the dataset and picks the row deterministically.
Provisional design: see docs/agent-node-specs/persona_explanation.md.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

import duckdb
from pydantic import BaseModel, Field, ValidationError

from ...core.context import Context
from ...core.text import short
from ...core.usage import BudgetError
from ...llm.client import ToolChat, tool_spec
from .dataset import (
    CATEGORICAL_FIELDS,
    Filters,
    PersonaStore,
    dataset_dir,
    missing_shards,
    validate_filters,
)
from .profiles import PROFILES_FILE, resolve_dataset_profile, resolve_profile
from .prompts import SELECT_TASK
from .template import TemplateError, default_filters, default_template_path, load_template

# A fixed seed: the same filters pick the same row on every rerun.
DEFAULT_SEED = "fdr-persona-v1"
MAX_TURNS = 6
# A second `choose` that matches nothing ends the loop; relaxation takes over.
MAX_EMPTY_CHOICES = 2
VALUES_LIMIT = 30
CARD_SUMMARY_LIMIT = 15
# Filters dropped one at a time, in this order, until at least one row matches. The age range
# goes last: it is what the product type's defaults are made of.
RELAX_ORDER = (
    "occupation_contains",
    "housing_type",
    "family_type",
    "marital_status",
    "province",
    "education_level",
    "sex",
    "age",
)


class ListValues(BaseModel):
    """The real values of one dataset field with their row counts, most frequent first."""

    field: Literal[
        "sex",
        "education_level",
        "occupation",
        "province",
        "family_type",
        "housing_type",
        "marital_status",
    ]


class CountMatches(BaseModel):
    """How many dataset rows match the filters."""

    filters: Filters


class Choose(BaseModel):
    """The final filters for the reader. Refused when a value is not in the dataset or no row
    matches; code then picks one matching row deterministically. familiarity_hint: only when the
    description itself says how familiar the reader is with finance (e.g. '처음 알아보는' ->
    낮음, '금융권 종사자' -> 높음); empty otherwise."""

    filters: Filters
    rationale: str = Field(min_length=1)
    familiarity_hint: Literal["", "낮음", "보통", "높음"] = ""


TOOLS = [
    tool_spec("list_values", ListValues),
    tool_spec("count_matches", CountMatches),
    tool_spec("choose", Choose),
]


def summarize_cards(cards: Sequence[Mapping[str, Any]]) -> list[str]:
    """`kind: subject` of the page's cards, first occurrence only, at most CARD_SUMMARY_LIMIT."""
    lines = [f"{c.get('kind', '')}: {c.get('subject') or c.get('claim') or ''}" for c in cards]
    return list(dict.fromkeys(lines))[:CARD_SUMMARY_LIMIT]


def _dump(filters: Filters) -> dict:
    return filters.model_dump(exclude_defaults=True)


def _drop(filters: Filters, name: str) -> Filters:
    if name == "age":
        return filters.model_copy(update={"age_min": None, "age_max": None})
    return filters.model_copy(update={name: Filters.model_fields[name].get_default()})


def _is_set(filters: Filters, name: str) -> bool:
    if name == "age":
        return filters.age_min is not None or filters.age_max is not None
    return bool(getattr(filters, name))


def relax(store: PersonaStore, filters: Filters, trace: list[dict]) -> tuple[Filters, int]:
    """Drop filters in RELAX_ORDER until a row matches; each drop is traced."""
    count = store.count(filters)
    for name in RELAX_ORDER:
        if count > 0:
            break
        if not _is_set(filters, name):
            continue
        filters = _drop(filters, name)
        count = store.count(filters)
        trace.append({"step": "relax", "dropped": name, "filters": _dump(filters), "count": count})
    return filters, count


def _refusal(reason: str) -> dict:
    return {"refused": True, "reason": reason}


def call_tool(store: PersonaStore, name: str, args: Mapping[str, Any]) -> dict:
    """Run one tool call; anything invalid comes back refused with the reason."""
    schemas: dict[str, type[BaseModel]] = {
        "list_values": ListValues,
        "count_matches": CountMatches,
        "choose": Choose,
    }
    if name not in schemas:
        return _refusal(f"unknown tool {name!r}")
    try:
        parsed = schemas[name].model_validate(args)
    except ValidationError as error:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in error.errors()})
        return _refusal(f"invalid arguments: {', '.join(fields)}")
    if isinstance(parsed, ListValues):
        return {"field": parsed.field, "values": store.values(parsed.field, VALUES_LIMIT)}
    assert isinstance(parsed, CountMatches | Choose)
    problems = validate_filters(store, parsed.filters)
    if problems:
        return _refusal("; ".join(problems))
    count = store.count(parsed.filters)
    if isinstance(parsed, CountMatches):
        return {"count": count}
    if count == 0:
        return {**_refusal("no row matches these filters; loosen one and choose again"), "count": 0}
    return {"accepted": True, "count": count}


def _agent_filters(
    request: str,
    product_type: str | None,
    cards_summary: Sequence[str],
    store: PersonaStore,
    chat,
    trace: list[dict],
    hint: list[str],
) -> tuple[Filters | None, Filters | None, str]:
    """The bounded loop. Returns (chosen, last proposed, stop_reason); an accepted choose's
    familiarity hint is appended to `hint`."""
    chat.system(SELECT_TASK)
    chat.user(
        json.dumps(
            {
                "reader_request": request,
                "product_type": product_type,
                "page_cards": list(cards_summary),
                "fields": list(CATEGORICAL_FIELDS) + ["age_min", "age_max"],
                "turns_available": MAX_TURNS,
            },
            ensure_ascii=False,
        )
    )
    proposed: Filters | None = None
    empty_choices = 0
    for turn in range(1, MAX_TURNS + 1):
        try:
            reply = chat.turn()
        except BudgetError as error:
            trace.append({"turn": turn, "step": "stop", "reason": str(error)})
            return None, proposed, "budget_exhausted"
        except Exception as error:  # a model or network failure must not stop the review
            trace.append({"turn": turn, "step": "stop", "reason": type(error).__name__})
            return None, proposed, "model_error"
        left = MAX_TURNS - turn
        if not reply["tool_calls"]:
            trace.append({"turn": turn, "tool_calls": 0, "tokens": reply["tokens"]})
            chat.user(f"Use the tools and call choose. Turns left: {left}.")
            continue
        for call in reply["tool_calls"]:
            args = call.get("args") or {}
            result = call_tool(store, call["name"], args)
            trace.append(
                {
                    "turn": turn,
                    "tool": call["name"],
                    "args": short(args),
                    "result": short(result, 2_000),
                    "refused": bool(result.get("refused")),
                    "reason": result.get("reason", ""),
                }
            )
            chat.tool_result(
                call["id"], json.dumps({**result, "turns_left": left}, ensure_ascii=False)
            )
            # Filters that passed validation are remembered, even with no match, so that a
            # failed loop relaxes what the model was aiming at instead of the defaults.
            if "count" in result:
                proposed = Filters.model_validate(args["filters"])
            if call["name"] == "choose":
                if result.get("accepted"):
                    hint.append(str(args.get("familiarity_hint") or ""))
                    return proposed, proposed, "chosen"
                if result.get("count") == 0:
                    empty_choices += 1
                    if empty_choices >= MAX_EMPTY_CHOICES:
                        return None, proposed, "no_match"
    return None, proposed, "max_turns"


def select_persona(
    request: str,
    ctx: Context,
    *,
    product_type: str | None,
    cards_summary: Sequence[str],
    store: PersonaStore,
    chat=None,
    ask=None,
    template_path: str | Path | None = None,
    seed: str = DEFAULT_SEED,
) -> dict:
    """The dataset row to explain for, as {uuid, decided_by, filters, match_count, seed,
    stop_reason, trace, reason}; decided_by is uuid, attributes, agent, default or fallback.

    `request` is the free-text wish (ctx.persona_request). `chat` stands in for ToolChat; an
    `ask` given without a chat marks an offline run, so no model is called. Never raises for
    a budget or model failure: it falls back to relaxed filters and says why.
    """
    trace: list[dict] = []
    notes: list[str] = []
    hint: list[str] = []
    try:
        template = load_template(template_path or default_template_path(ctx.rubric_dir))
        defaults = default_filters(product_type, template)
    except TemplateError as error:
        defaults = Filters()
        notes.append(f"기본 필터 없음({error})")

    def result(decided_by: str, filters: Filters, stop_reason: str = "") -> dict:
        filters, count = relax(store, filters, trace)
        relaxed = [t["dropped"] for t in trace if t.get("step") == "relax"]
        if relaxed:
            decided_by = "fallback"
            notes.append(f"조건 완화: {', '.join(relaxed)} 제외")
        row = store.pick(filters, seed) if count else None
        if row is None:
            notes.append("데이터셋에 일치하는 행이 없음")
        return {
            "uuid": row["uuid"] if row else "",
            "decided_by": decided_by if row else "fallback",
            "filters": _dump(filters),
            "match_count": count,
            "seed": seed,
            "stop_reason": stop_reason,
            "trace": trace,
            "reason": "; ".join(notes),
            "familiarity_hint": hint[0] if hint else "",
        }

    if ctx.persona_uuid:
        row = store.row(ctx.persona_uuid)
        if row is not None:
            return {
                "uuid": row["uuid"],
                "decided_by": "uuid",
                "filters": {},
                "match_count": 1,
                "seed": seed,
                "stop_reason": "",
                "trace": trace,
                "reason": "",
            }
        notes.append(f"persona_uuid {ctx.persona_uuid!r}가 데이터셋에 없음")
        return result("fallback", defaults)

    if ctx.persona_attributes is not None:
        try:
            filters = Filters.model_validate(ctx.persona_attributes)
        except ValidationError as error:
            fields = sorted({".".join(str(p) for p in e["loc"]) for e in error.errors()})
            notes.append(f"persona_attributes 형식 오류: {', '.join(fields)}")
            return result("fallback", defaults)
        problems = validate_filters(store, filters)
        if problems:
            notes.append(f"persona_attributes 거부: {'; '.join(problems)}")
            return result("fallback", defaults)
        return result("attributes", filters)

    if request.strip():
        if chat is None and ask is not None:
            notes.append("오프라인 실행이라 모델 없이 기본 필터를 씀")
            return result("fallback", defaults, "no_model")
        if chat is None:
            try:
                chat = ToolChat(ctx.model, TOOLS, label="persona_select")
            except Exception as error:  # e.g. no API key: the review goes on with defaults
                notes.append(f"모델을 준비할 수 없음: {type(error).__name__}")
                return result("fallback", defaults, "model_error")
        chosen, proposed, stop = _agent_filters(
            request, product_type, cards_summary, store, chat, trace, hint
        )
        if chosen is not None:
            return result("agent", chosen, stop)
        notes.append(f"에이전트가 필터를 확정하지 못함({stop})")
        return result("fallback", proposed or defaults, stop)

    return result("default", defaults)


def _legacy(ctx: Context, rubric_dir: str | Path, reason: str) -> dict:
    profile = resolve_profile(ctx.persona_profile or None, Path(rubric_dir) / PROFILES_FILE)
    return {
        "profile": profile,
        "selection": {
            "uuid": "",
            "decided_by": "fallback",
            "filters": {},
            "match_count": 0,
            "seed": DEFAULT_SEED,
            "stop_reason": "",
            "trace": [],
            "reason": reason,
        },
    }


def choose_profile(
    ctx: Context,
    *,
    product_type: str | None,
    cards: Sequence[Mapping[str, Any]],
    data_dir: str | Path,
    rubric_dir: str | Path,
    chat=None,
    ask=None,
) -> dict:
    """{profile, selection}: a dataset row's derived profile when the dataset is on disk,
    else the legacy yaml profile (ctx.persona_profile or the file default) with the reason."""
    missing = missing_shards(data_dir)
    if missing:
        return _legacy(
            ctx,
            rubric_dir,
            f"페르소나 데이터셋 없음: {dataset_dir(data_dir)}에 샤드 {len(missing)}개 누락,"
            " 기존 프로필 사용",
        )
    try:
        store = PersonaStore(dataset_dir(data_dir))
        selection = select_persona(
            ctx.persona_request,
            ctx,
            product_type=product_type,
            cards_summary=summarize_cards(cards),
            store=store,
            chat=chat,
            ask=ask,
            template_path=default_template_path(rubric_dir),
        )
        row = store.row(selection["uuid"]) if selection["uuid"] else None
    except duckdb.Error as error:
        return _legacy(
            ctx,
            rubric_dir,
            f"페르소나 데이터셋을 읽을 수 없음: {type(error).__name__}, 기존 프로필 사용",
        )
    if row is None:
        return _legacy(ctx, rubric_dir, f"{selection['reason']}; 기존 프로필 사용")
    return {
        "profile": resolve_dataset_profile(
            row,
            product_type,
            default_template_path(rubric_dir),
            familiarity=selection.get("familiarity_hint") or None,
        ),
        "selection": selection,
    }
