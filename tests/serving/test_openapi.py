"""The committed spec is an artifact other people generate clients from, so it must not drift."""

import yaml

from financial_disclosure_review.serving.openapi import default_path, document, render


def test_the_committed_spec_matches_the_code() -> None:
    """Fails whenever a route or a model changed without regenerating the file.

    Fix by running:  uv run python -m financial_disclosure_review.serving.openapi
    """
    committed = default_path()
    assert committed.exists(), f"{committed} is missing; regenerate it"
    assert committed.read_text(encoding="utf-8") == render(document())


def test_every_v1_route_requires_the_api_key() -> None:
    """An unauthenticated /v1 route would be a hole the document hides."""
    spec = document()
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            security = operation.get("security")
            if path.startswith("/v1/"):
                assert security == [{"APIKeyHeader": []}], f"{method.upper()} {path}"
            else:
                assert security is None, f"{method.upper()} {path} should stay open"


def test_the_key_is_declared_as_a_header_scheme() -> None:
    scheme = document()["components"]["securitySchemes"]["APIKeyHeader"]
    assert scheme["type"] == "apiKey"
    assert scheme["in"] == "header"
    assert scheme["name"] == "X-API-Key"


def test_health_routes_stay_reachable_without_a_credential() -> None:
    paths = document()["paths"]
    assert paths["/healthz"]["get"].get("security") is None
    assert paths["/readyz"]["get"].get("security") is None


def test_the_committed_file_is_parseable_yaml_with_the_expected_shape() -> None:
    spec = yaml.safe_load(default_path().read_text(encoding="utf-8"))
    assert spec["openapi"].startswith("3.1")
    assert spec["info"]["title"] == "Financial Disclosure Review API"
    assert {"reviews", "health"} == {tag["name"] for tag in spec["tags"]}
    assert set(spec["paths"]) == {
        "/healthz",
        "/readyz",
        "/v1/reviews",
        "/v1/reruns",
        "/v1/reviews/{job_id}",
        "/v1/reviews/{job_id}/report.md",
    }


def test_operation_ids_are_client_friendly() -> None:
    """Generated clients name methods after these, so they are part of the contract."""
    spec = document()
    ids = {
        operation["operationId"]
        for operations in spec["paths"].values()
        for operation in operations.values()
    }
    assert ids == {
        "getHealth",
        "getReadiness",
        "submitReview",
        "submitRerun",
        "listReviews",
        "getReview",
        "getReviewReportMarkdown",
    }
