"""Blocks SSRF: rejects loopback, private/link-local, and non-http(s) URLs before a fetch."""

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
    """Why this URL may not open, or "" (checks allowed_hosts; address must resolve public)."""
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
