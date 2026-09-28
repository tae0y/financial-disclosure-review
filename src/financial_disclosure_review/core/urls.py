"""Which URLs the service may open.

A review drives a real browser to whatever URL it is given, so accepting a URL means agreeing to
make a request from the server's network. An address only the server can reach — loopback, the
private ranges a container network uses (the worker itself is `http://agent:8100`), link-local
(cloud metadata answers at 169.254.169.254) — or a scheme other than http(s) would let a caller
read through the service what they cannot read directly. `url_problem` names the first reason a
URL may not be opened, or returns "" when it may.

Both ends call it: the gateway before a job exists, and `fetch_product_page` right before the
browser starts, so the CLI and a worker reached by some other route are covered too.
"""

import ipaddress
import socket
from collections.abc import Callable, Sequence
from urllib.parse import urlsplit


def resolve(host: str) -> list[str]:
    """Every address the host name resolves to right now."""
    return sorted({str(info[4][0]) for info in socket.getaddrinfo(host, None)})


def _address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    address = ipaddress.ip_address(value.split("%", 1)[0])
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def _allowed(host: str, allowed_hosts: Sequence[str]) -> bool:
    return any(
        host == entry or host.endswith("." + entry)
        for entry in (h.strip().lower().rstrip(".") for h in allowed_hosts)
        if entry
    )


def url_problem(
    url: str,
    allowed_hosts: Sequence[str] = (),
    resolver: Callable[[str], list[str]] | None = None,
) -> str:
    """Why this URL may not be opened, or "" when it may.

    `allowed_hosts`, when given, is the only set of domains accepted (a subdomain of an entry
    counts). Every address the host resolves to must be a public one; a name that does not
    resolve is refused rather than guessed about.
    """
    resolver = resolver or resolve
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return f"scheme {parts.scheme or '(none)'!r} is not http or https"
    if parts.username or parts.password:
        return "credentials inside the URL are not accepted"
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        return "the URL has no host"
    if allowed_hosts and not _allowed(host, allowed_hosts):
        return f"host {host!r} is not in the allowed list"
    try:
        addresses = [_address(host)]
    except ValueError:
        try:
            addresses = [_address(value) for value in resolver(host)]
        except (OSError, UnicodeError, ValueError) as error:
            return f"host {host!r} does not resolve ({type(error).__name__})"
    if not addresses:
        return f"host {host!r} does not resolve"
    for address in addresses:
        if not address.is_global:
            return f"host {host!r} is a non-public address ({address})"
    return ""
