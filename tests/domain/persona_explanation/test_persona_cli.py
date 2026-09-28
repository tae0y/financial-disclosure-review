"""CLI: persona options reach Context, and fetch-personas reports what it downloaded."""

import pytest

from financial_disclosure_review import __main__ as cli
from financial_disclosure_review.domain.persona_explanation.dataset import SHARDS, dataset_dir


def parse(*argv: str):
    return cli.resolve_paths(cli.parser().parse_args(list(argv)))


def test_review_persona_options_reach_the_context():
    args = parse(
        "review",
        "https://example.com",
        "--persona",
        "70대 은퇴자",
        "--persona-uuid",
        "a" * 32,
        "--persona-attr",
        "age_min=70",
        "--persona-attr",
        "province=서울,경기",
    )
    ctx = cli.context_from(args)
    assert ctx.persona_request == "70대 은퇴자"
    assert ctx.persona_uuid == "a" * 32
    assert ctx.persona_attributes == {"age_min": 70, "province": ["서울", "경기"]}


def test_without_persona_options_the_context_keeps_its_defaults():
    ctx = cli.context_from(parse("review", "https://example.com"))
    assert ctx.persona_request == "" and ctx.persona_uuid == ""
    assert ctx.persona_attributes is None
    assert cli.context_from(parse("build-db")).persona_attributes is None


def test_a_bad_persona_attribute_is_a_usage_error(capsys):
    with pytest.raises(SystemExit):
        parse("review", "u", "--persona-attr", "income=high")
    assert "income" in capsys.readouterr().err


def test_fetch_personas_reports_the_download_and_fails_on_a_failed_shard(tmp_path, monkeypatch):
    calls = []

    def fake_ensure(data_dir, **_):
        calls.append(data_dir)
        return {
            "dir": str(dataset_dir(data_dir)),
            "ok": False,
            "shards": [
                {"shard": "a", "status": "downloaded", "bytes": 10},
                {"shard": "b", "status": "failed", "bytes": 0, "reason": "OSError: x"},
            ],
        }

    monkeypatch.setattr(cli, "ensure_dataset", fake_ensure)
    assert cli.main(["fetch-personas", "--data-dir", str(tmp_path)]) == 1
    assert calls == [str(tmp_path)]


def test_fetch_personas_if_missing_skips_a_complete_dataset(tmp_path, monkeypatch, capsys):
    folder = dataset_dir(tmp_path)
    folder.mkdir(parents=True)
    for shard in SHARDS:
        (folder / shard).write_bytes(b"x")
    monkeypatch.setattr(cli, "ensure_dataset", lambda *a, **k: pytest.fail("downloaded"))
    assert cli.main(["fetch-personas", "--if-missing", "--data-dir", str(tmp_path)]) == 0
    assert "present" in capsys.readouterr().out
