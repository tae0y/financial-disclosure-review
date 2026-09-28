"""Exports the OpenAPI document to `docs/openapi.yaml`; a test fails if it drifts from the code."""

import sys
from pathlib import Path
from typing import Any

import yaml

HEADER = """\
# Generated from the FastAPI app — do not edit by hand.
#
# Regenerate after any change to a route, a request model or a response model:
#     uv run python -m financial_disclosure_review.serving.openapi
#
# tests/serving/test_openapi.py fails when this file and the code disagree.
"""


def default_path() -> Path:
    """`docs/openapi.yaml`, found from this file rather than the working directory."""
    return Path(__file__).resolve().parents[3] / "docs" / "openapi.yaml"


def document() -> dict[str, Any]:
    """The spec the running service would serve, built without binding a port."""
    from .api.app import create_app

    return create_app().openapi()


def render(spec: dict[str, Any]) -> str:
    """Deterministic YAML: sorted keys, block style, real UTF-8 rather than escapes."""
    return HEADER + yaml.safe_dump(
        spec, sort_keys=True, allow_unicode=True, default_flow_style=False, width=100
    )


def write(path: Path | None = None) -> Path:
    target = path or default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(document()), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    target = write(Path(argv[0]) if argv else None)
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
