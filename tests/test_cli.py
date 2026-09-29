from pathlib import Path

from financial_disclosure_review.__main__ import parser, resolve_paths


def parse(*argv: str):
    return resolve_paths(parser().parse_args(list(argv)))


def test_global_options_before_the_subcommand_are_kept():
    args = parse("--data-dir", "data/x", "--checkpoints", "data/x/cp.sqlite", "review", "u")
    assert args.data_dir == "data/x"
    assert args.checkpoints == "data/x/cp.sqlite"


def test_options_after_the_subcommand_still_work():
    args = parse("review", "--data-dir", "data/y", "--max-usd", "0.5", "u")
    assert args.data_dir == "data/y"
    assert args.max_usd == 0.5


def test_after_the_subcommand_wins_over_before():
    args = parse("--model", "a", "review", "--model", "b", "u")
    assert args.model == "b"


def test_checkpoints_follow_data_dir_when_not_given():
    args = parse("--data-dir", "data/z", "review", "u")
    assert Path(args.checkpoints) == Path("data/z") / "checkpoints.sqlite"
