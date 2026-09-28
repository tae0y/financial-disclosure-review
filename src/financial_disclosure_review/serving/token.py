"""Issues a `fdr_`-prefixed bearer token (traceable by scanners) for the gateway's credential."""

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
