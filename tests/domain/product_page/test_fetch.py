"""fetch_product_page against the real sample URLs. Opens a browser and pays for the agent."""

from pathlib import Path

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.product_page import fetch_product_page

URLS = [u for u in Path("data/sample_urls.txt").read_text().split() if u]


@pytest.mark.use_network
@pytest.mark.use_llm
@pytest.mark.parametrize("url", URLS)
def test_a_sample_url_yields_a_product_and_its_content(url, tmp_path):
    page = fetch_product_page(url, Context(data_dir=str(tmp_path)))
    assert page["url"] == url
    assert set(page) == {"url", "product", "actions", "snapshots", "html"}
    assert page["product"]["product_name"]
    assert len(page["html"]) > 300
    assert any(snapshot["phase"] == "render" for snapshot in page["snapshots"])
    assert any(action["type"] == "result" for action in page["actions"])
