"""The reusable site rule: where it is stored, whether it still fits, and what it reaches."""

import json
import os
import re
import threading
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from bs4 import BeautifulSoup

from ...core.text import norm
from .html import extract_pieces, merge_pieces, outside_signature
from .session import PageSession


def page_family(url: str) -> str:
    """URL pattern of a page family: product slug -> *, numeric folders -> #, query names kept."""
    parts = urlparse(url)
    segments = [re.sub(r"^\d+$", "#", s) for s in parts.path.split("/") if s]
    if segments:
        _, dot, ext = segments[-1].rpartition(".")
        segments[-1] = "*" + (dot + ext if dot else "")
    names = ",".join(sorted(k for k, _ in parse_qsl(parts.query, keep_blank_values=True)))
    return "/" + "/".join(segments) + (f"?{names}" if names else "")


def rule_path(rules_dir: Path, url: str, viewport: str) -> Path:
    family = re.sub(r"[^\w.-]+", "_", page_family(url)).strip("_")
    return rules_dir / f"{urlparse(url).hostname}__{family}__{viewport}.json"


def load_rule(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def save_rule(path: Path, rule: dict) -> None:
    """Written beside the target and swapped in, so a run reading the rule while another saves
    it sees one whole file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(rule, ensure_ascii=False, indent=1))
    os.replace(tmp, path)


def check_rule(html: str, rule: dict) -> list[str]:
    """Structural gate before a saved rule is used. Empty list means the rule may be reused."""
    soup = BeautifulSoup(html, "html.parser")
    reasons = []
    for selector in rule["include"]:
        try:
            count = len(soup.select(selector))
        except Exception as error:
            reasons.append(f"include {selector!r} is invalid: {error}")
            continue
        stored = rule["counts"].get(selector, 0)
        if stored and count == 0:
            reasons.append(f"include {selector!r} matches 0 (was {stored})")
        elif count < stored:
            reasons.append(
                f"include {selector!r} matches {count}, fewer than the {stored} it covered"
            )
    for step in rule["steps"]:
        if step["action"] == "expand" and not soup.select(step["selector"]):
            reasons.append(f"step expand {step['selector']!r} matches 0")
    for mark in rule["landmarks"]:
        found = soup.select(mark["selector"])
        if not any(
            el.name == mark["tag"].lower() and (not mark["role"] or el.get("role") == mark["role"])
            for el in found
        ):
            reasons.append(
                f"landmark {mark['selector']!r} <{mark['tag']}> role={mark['role']!r} missing"
            )
    named = soup.select_one(rule["name_selector"])
    if named is None or norm(rule["product_name"]) not in norm(named.get_text(" ")):
        reasons.append("name_selector no longer contains the stored product name")
    if "outside" not in rule:
        reasons.append("no stored outside-content signature: coverage cannot be established")
    else:
        new = sorted(
            set(outside_signature(html, rule["include"], rule["exclude"])) - set(rule["outside"])
        )
        if new:
            reasons.append(
                f"{len(new)} new text regions outside the selected content, e.g. {new[:3]}"
            )
    return reasons


def execute_rule(sess: PageSession, rule: dict) -> dict:
    """Replay the saved steps on the freshly loaded page and merge every captured state."""
    view = (rule["include"], rule["exclude"])
    default_html = sess.last_html
    sess.states = [extract_pieces(sess.last_html, *view)]
    sess.view = view
    step_results = []
    for step in rule["steps"]:
        if step["action"] == "scroll":
            sess.scroll_step()
            changed = sess.snapshot_if_changed("expanded", "scroll")
            step_results.append({"action": "scroll", "new_state": bool(changed)})
        else:
            step_results.append(
                {
                    "action": "expand",
                    "selector": step["selector"],
                    **sess.click_matches(step["selector"], "expanded"),
                }
            )
    sess.view = None
    kept, html = merge_pieces(sess.states)
    named = BeautifulSoup(default_html, "html.parser").select_one(rule["name_selector"])
    return {
        "pieces": kept,
        "html": html,
        "steps": step_results,
        "name_text": named.get_text(" ", strip=True) if named else "",
        "states": len(sess.states),
    }


def validate_output(rule: dict, content: dict) -> list[str]:
    errors = []
    text = " ".join(p["text"] for p in content["pieces"])
    if not content["html"].strip():
        errors.append("html is empty")
    if norm(rule["product_name"]) not in norm(text) and norm(rule["product_name"]) not in norm(
        content["name_text"]
    ):
        errors.append("product name missing from selected content")
    active = {p["selector"] for p in content["pieces"]}
    for selector in rule.get("active_includes", []):
        if selector not in active:
            errors.append(f"include {selector!r} contributed no text")
    if rule.get("content_chars") and len(text) < 0.5 * rule["content_chars"]:
        errors.append(f"selected content shrank to {len(text)} chars from {rule['content_chars']}")
    for step in content["steps"]:
        if step["action"] == "expand" and step["matched"] and not step["clicked"]:
            errors.append(f"expand {step['selector']!r} clicked nothing: {step['skipped']}")
    return errors


def product_from(rule: dict, content: dict) -> dict:
    return {
        "product_name": rule["product_name"],
        "summary": rule["summary"],
        "evidence": rule["evidence"],
    }


def finalize_rule(sess: PageSession, rule: dict) -> tuple[dict, dict]:
    """Reload the page, replay the proposal like a reuse visit would, and store what it reached."""
    sess.phase = "render"
    sess.goto(sess.url, count=False)
    soup = BeautifulSoup(sess.last_html, "html.parser")
    rule["counts"] = {s: len(soup.select(s)) for s in rule["include"]}
    rule["outside"] = outside_signature(sess.last_html, rule["include"], rule["exclude"])
    content = execute_rule(sess, rule)
    rule["active_includes"] = sorted({p["selector"] for p in content["pieces"]})
    rule["content_chars"] = sum(len(p["text"]) for p in content["pieces"])
    return rule, content
