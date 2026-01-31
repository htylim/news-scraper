"""Image helpers for parsers."""

from __future__ import annotations


def first_srcset_url(srcset: str) -> str | None:
    """Extract the first URL from a srcset string."""
    if not srcset.strip():
        return None
    first_entry = srcset.split(",")[0].strip()
    if not first_entry:
        return None
    return first_entry.split()[0]
