"""Every eval result names the implementation, code, prompts and gold it measured (audit
2026-09-29 R3), so results of different generations cannot be read as one another."""

import hashlib
import json

from financial_disclosure_review.evaluation.run_meta import run_meta


def test_the_metadata_names_the_implementation_prompts_and_gold(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps({"version": "ai-draft-260929", "pages": []}), encoding="utf-8")
    meta = run_meta("linking_agent", prompts={"system": "You link cases."}, gold=gold)
    assert meta["implementation"] == "linking_agent"
    assert meta["prompt_sha256"] == {"system": hashlib.sha256(b"You link cases.").hexdigest()[:12]}
    assert meta["gold"]["version"] == "ai-draft-260929"
    assert meta["gold"]["sha256"] == hashlib.sha256(gold.read_bytes()).hexdigest()[:12]
    assert set(meta) >= {"commit", "dirty", "recorded_at"}


def test_a_missing_gold_file_is_recorded_as_missing_not_raised(tmp_path):
    meta = run_meta("page_agent", gold=tmp_path / "absent.json")
    assert meta["gold"] == {"path": str(tmp_path / "absent.json"), "missing": True}
    assert meta["prompt_sha256"] == {}


def test_outside_a_git_checkout_the_commit_is_unknown(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    meta = run_meta("x", repo=tmp_path)
    assert meta["commit"] == "unknown"
