# Financial Disclosure Review

Reviews a Korean financial-product web page for the explanation duty and the display method,
and converts its explanation into plain Korean, as one LangGraph app.

Work in progress: the product-page, classification, display-method, plain-language,
explanation-duty and verification modules are built; the report module and the retry branch are
stubs, so a failed verification still ends the graph.

## Install

```bash
cp .env.example .env   # then set OPENAI_API_KEY
uv sync --extra dev
uv run playwright install chromium
```

## Run

The reference DB has to exist before a review; `build-db` reads the rubric yaml files and
writes `data/reference.sqlite`.

```bash
uv run python -m financial_disclosure_review build-db
uv run python -m financial_disclosure_review review "https://<product page>"
uv run python -m financial_disclosure_review rerun --thread review-260927-101500 \
    --from-node judge_display_method
```

`--model`, `--data-dir`, `--db-path` and `--checkpoints` override the defaults in
`core/context.py`. Both `review` and `rerun` print a summary of the final State.

## Test

```bash
uv run pytest                                # free checks only
uv run pytest -m "use_llm or use_network"    # paid model calls and live sites
```

`use_llm` costs money and `use_network` opens external sites, so both are excluded by default.
The browser test in `tests/domain/product_page/test_session.py` carries no marker: it renders a local
HTML fixture and reaches no network.

## Docs

- `docs/design.md` — principles, package layout, input, graph, State, rubrics, checkpoints
- `docs/src-layout-migration.md` — what moved out of the notebook, and what changed with it
- `docs/product_page.md`, `docs/classification.md`, `docs/display_check.md`,
  `docs/plain_language.md`, `docs/explanation_duty_check.md` — per-domain rules
- `localdocs/` — plans, worklog and ADRs (local only)
