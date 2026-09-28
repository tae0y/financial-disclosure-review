"""fetch_product_page against the real sample URLs. Opens a browser and pays for the agent."""

from pathlib import Path

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.product_page import fetch_product_page

SAMPLE_URLS_PATH = Path("data/sample_urls.txt")
URLS = [u for u in SAMPLE_URLS_PATH.read_text().split() if u] if SAMPLE_URLS_PATH.exists() else []


@pytest.mark.use_network
@pytest.mark.use_llm
@pytest.mark.parametrize("url", URLS)
def test_a_sample_url_yields_a_product_and_its_content(url, tmp_path):
    page = fetch_product_page(url, Context(data_dir=str(tmp_path)))
    assert page["url"] == url
    assert set(page) == {
        "url",
        "product",
        "actions",
        "snapshots",
        "html",
        "status",
        "stop_reason",
        "error",
        "coverage",
        "agent_trace",
    }
    assert page["status"] == "완료"
    assert page["product"]["product_name"]
    assert len(page["html"]) > 300
    assert any(snapshot["phase"] == "render" for snapshot in page["snapshots"])
    assert any(action["type"] == "result" for action in page["actions"])
