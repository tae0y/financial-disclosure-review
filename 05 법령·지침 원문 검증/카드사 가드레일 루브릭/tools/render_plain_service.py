"""Verify every quote in plain_service_rubric.yaml against the source snapshots, then render the
three-axis (설명의무·표시방법·쉬운말) reference sheet `03 설명의무·표시방법·쉬운말 루브릭 대조표.md`.

Same flat schema and rendering as verify_and_render.py — this file just points it at the
three-axis rubric. Quotes are inlined per item (no more `from:` cross-file lookup), so this
script needs nothing from card_guardrail_rubric.yaml.

    uv run --no-project --with pyyaml python tools/render_plain_service.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_and_render as base  # noqa: E402

RUBRIC = base.ROOT / "plain_service_rubric.yaml"
SHEET = base.ROOT / "03 설명의무·표시방법·쉬운말 루브릭 대조표.md"


def main() -> int:
    return base.render(RUBRIC, SHEET, "카드사 설명의무·표시방법·쉬운말 가드레일 루브릭", "render_plain_service.py")


if __name__ == "__main__":
    sys.exit(main())
