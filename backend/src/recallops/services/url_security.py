import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

Resolver = Callable[[str, int], Awaitable[list[str]]]


def _is_public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return bool(address.is_global)


async def _resolve_addresses(hostname: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    records = await loop.getaddrinfo(
        hostname,
        port,
        type=socket.SOCK_STREAM,
    )
    return sorted({record[4][0] for record in records})


async def validate_safe_evidence_url(
    value: str,
    *,
    resolver: Resolver = _resolve_addresses,
) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ValueError("only HTTPS evidence URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL credentials are not allowed")
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL hostname is required")
    lowered = hostname.casefold().rstrip(".")
    if (
        lowered == "localhost"
        or lowered.endswith(".localhost")
        or lowered.endswith(".local")
        or lowered.endswith(".internal")
    ):
        raise ValueError("private network destinations are not allowed")
    port = parsed.port or 443
    try:
        addresses = [str(ipaddress.ip_address(hostname))]
    except ValueError:
        try:
            addresses = await resolver(hostname, port)
        except OSError as error:
            raise ValueError("URL hostname could not be resolved") from error
    if not addresses or not all(_is_public_address(address) for address in addresses):
        raise ValueError("private network destinations are not allowed")
    return value
