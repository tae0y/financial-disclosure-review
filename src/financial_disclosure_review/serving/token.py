"""Issuing the API token.

The gateway authenticates a pre-issued, fixed bearer token rather than minting per-caller
credentials: there is no user model here, and a run costs money, so the point is to name who may
spend it. Issue one, put it in the gateway's environment, and hand it to the caller.

    uv run python -m financial_disclosure_review.serving.token

The `fdr_` prefix is deliberate. A bare random string in a leaked log or a committed file is
unidentifiable; a prefixed one is matched by secret scanners and can be traced back to this
service and revoked.
"""

import secrets

PREFIX = "fdr_"
ENTROPY_BYTES = 32


def new_token() -> str:
    """A URL-safe token with 256 bits of entropy behind the prefix."""
    return PREFIX + secrets.token_urlsafe(ENTROPY_BYTES)


def main() -> int:
    print(new_token())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
