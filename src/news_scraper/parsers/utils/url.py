"""URL helpers for parsers."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse


def resolve_url(base_url: str, allowed_hosts: set[str], href: str) -> str | None:
    """Resolve and normalize an article URL.

    Rules:
    - Reject empty or fragment-only hrefs.
    - Resolve relative/protocol-relative URLs using base_url.
    - Reject external hosts (case-insensitive, allow subdomains).
    - Reject empty/root paths.
    - Strip query parameters and fragments.
    """
    stripped = href.strip()
    if not stripped or stripped.startswith("#"):
        return None

    resolved = urljoin(base_url, stripped)
    parsed = urlparse(resolved)

    if parsed.scheme not in {"http", "https"}:
        return None

    host = parsed.netloc.lower()
    allowed = {h.lower() for h in allowed_hosts}
    if not _is_allowed_host(host, allowed):
        return None

    if not parsed.path or parsed.path == "/":
        return None

    return parsed._replace(query="", fragment="").geturl()


def _is_allowed_host(host: str, allowed_hosts: set[str]) -> bool:
    """Check if host is allowed; subdomains are accepted."""
    if host in allowed_hosts:
        return True
    return any(host.endswith(f".{allowed}") for allowed in allowed_hosts)
