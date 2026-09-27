"""CLI: run one review, re-run a thread from a node, or build the reference DB."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver

from .core.context import Context, default_data_dir, default_db_path, default_rubric_dir
from .core.state import empty_state
from .graph.build import build_review_graph
from .knowledge.build import build_rubric_db


def default_checkpoint_path(data_dir: str) -> str:
    return str(Path(data_dir) / "checkpoints.sqlite")


def context_from(args: argparse.Namespace) -> Context:
    return Context(model=args.model, data_dir=args.data_dir, db_path=args.db_path)


def print_summary(state: dict) -> None:
    page = state.get("product_page") or {}
    print("url:", page.get("url"))
    print("product:", json.dumps(page.get("product"), ensure_ascii=False))
    print("html chars:", len(page.get("html") or ""))
    print("classification:", json.dumps(state.get("classification"), ensure_ascii=False))
    check = state.get("display_check") or {}
    judgments = check.get("judgments") or {}
    print("display_check status:", judgments.get("status"))
    for row in check.get("items") or []:
        print(f"  {row['code']}: {row['verdict']} | {row['reason']}")

    plain = state.get("plain_language") or {}
    print(
        "plain_language:",
        f"{len(plain.get('accepted_blocks') or [])} blocks kept,",
        f"{len(plain.get('contract_errors') or [])} sent back to the original",
    )
    duty = state.get("explanation_duty_check") or {}
    applied = [row for row in duty.get("items") or [] if row.get("applied")]
    print(
        "explanation_duty_check:",
        f"{len(applied)}/{len(duty.get('items') or [])} items applied,",
        f"{len(duty.get('fidelity') or [])} fidelity differences",
    )
    verification = state.get("verification") or {}
    print(
        "verification:",
        f"passed={verification.get('passed')}",
        f"failed={verification.get('failed_modules')}",
        f"loop={verification.get('loop_count')}",
    )


def review(args: argparse.Namespace) -> int:
    thread_id = args.thread or f"review-{datetime.now().strftime('%y%m%d-%H%M%S')}"
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    state = empty_state()
    state["product_page"] = {"url": args.url}
    print("thread:", thread_id)
    with SqliteSaver.from_conn_string(args.checkpoints) as saver:
        final = build_review_graph(saver).invoke(state, config, context=context_from(args))
    print_summary(final)
    return 0


def rerun(args: argparse.Namespace) -> int:
    config: RunnableConfig = {"configurable": {"thread_id": args.thread}}
    with SqliteSaver.from_conn_string(args.checkpoints) as saver:
        graph = build_review_graph(saver)
        before = next(
            (s for s in graph.get_state_history(config) if args.from_node in s.next), None
        )
        if before is None:
            print(f"thread {args.thread!r} has no checkpoint whose next node is {args.from_node!r}")
            return 1
        final = graph.invoke(None, before.config, context=context_from(args))
    print_summary(final)
    return 0


def build_db(args: argparse.Namespace) -> int:
    counts = build_rubric_db(args.rubric_dir, args.db_path)
    print(f"rubric DB {args.db_path}: {counts}")
    return 0


def parser() -> argparse.ArgumentParser:
    data_dir = default_data_dir()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", default=Context.model)
    common.add_argument("--data-dir", default=data_dir)
    common.add_argument("--db-path", default=default_db_path())
    common.add_argument("--checkpoints", default=default_checkpoint_path(data_dir))

    root = argparse.ArgumentParser(
        prog="financial_disclosure_review", description=__doc__, parents=[common]
    )
    commands = root.add_subparsers(dest="command", required=True)

    one = commands.add_parser("review", help="review one product page URL", parents=[common])
    one.add_argument("url")
    one.add_argument("--thread", default="", help="thread id; a timestamped one by default")
    one.set_defaults(run=review)

    again = commands.add_parser("rerun", help="re-run a thread from one node", parents=[common])
    again.add_argument("--thread", required=True)
    again.add_argument("--from-node", required=True)
    again.set_defaults(run=rerun)

    build = commands.add_parser(
        "build-db", help="build the reference DB from the rubric yaml", parents=[common]
    )
    build.add_argument("--rubric-dir", default=default_rubric_dir())
    build.set_defaults(run=build_db)
    return root


def main(argv: list[str] | None = None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    args = parser().parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
