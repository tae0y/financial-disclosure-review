"""url_problem: which submitted URLs the service refuses to open, decided without a network."""

import pytest

from financial_disclosure_review.core.urls import url_problem


def resolver_to(*addresses: str):
    def resolve(host: str) -> list[str]:
        return list(addresses)

    return resolve


def unresolvable(host: str) -> list[str]:
    raise OSError("no such host")


PUBLIC = resolver_to("211.45.27.10")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8100/run",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.8/",
        "http://192.168.0.1/admin",
        "http://100.64.0.1/",
        "http://0.0.0.0:8000/",
        "http://[::1]:8000/",
        "http://[::ffff:127.0.0.1]/",
    ],
)
def test_an_address_only_the_server_can_reach_is_refused(url):
    assert "non-public address" in url_problem(url, resolver=PUBLIC)


def test_a_name_that_resolves_inside_the_network_is_refused():
    # The worker's compose service name, and localhost, resolve to private addresses.
    assert "non-public" in url_problem("http://agent:8100/run", resolver=resolver_to("172.18.0.3"))
    assert "non-public" in url_problem("http://localhost/", resolver=resolver_to("127.0.0.1"))


def test_one_private_address_among_public_ones_is_enough_to_refuse():
    mixed = resolver_to("211.45.27.10", "10.1.2.3")
    assert "non-public" in url_problem("https://card.example.com/", resolver=mixed)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("file:///etc/passwd", "is not http or https"),
        ("ftp://files.example.com/a", "is not http or https"),
        ("https://user:secret@card.example.com/", "credentials"),
        ("https:///no-host", "no host"),
    ],
)
def test_a_url_of_the_wrong_shape_is_refused(url, expected):
    assert expected in url_problem(url, resolver=PUBLIC)


def test_a_name_that_does_not_resolve_is_refused_not_guessed():
    assert "does not resolve" in url_problem("https://nowhere.invalid/", resolver=unresolvable)


def test_a_public_product_page_is_accepted():
    url = "https://www.lottecard.co.kr/app/LPCDXAA_V001.lc?vtCdKndC=P13379-A13379"
    assert url_problem(url, resolver=PUBLIC) == ""


def test_the_allowed_list_admits_its_domains_and_their_subdomains_only():
    allowed = ("lottecard.co.kr",)
    assert url_problem("https://www.lottecard.co.kr/x", allowed, resolver=PUBLIC) == ""
    assert url_problem("https://lottecard.co.kr/x", allowed, resolver=PUBLIC) == ""
    assert "not in the allowed list" in url_problem(
        "https://lottecard.co.kr.evil.example/x", allowed, resolver=PUBLIC
    )
    assert "not in the allowed list" in url_problem(
        "https://www.samsungfire.com/", allowed, resolver=PUBLIC
    )
