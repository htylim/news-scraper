"""Parser for La Política Online news site."""

from __future__ import annotations

from typing import cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from news_scraper.parsers.base import BaseParser, ParsedArticleData
from news_scraper.parsers.registry import register_parser
from news_scraper.parsers.utils import first_srcset_url, resolve_url


@register_parser("lapoliticaonline")
class LaPoliticaOnlineParser(BaseParser):
    """Parser for La Política Online front page HTML."""

    base_url = "https://www.lapoliticaonline.com"
    allowed_hosts = {"www.lapoliticaonline.com", "lapoliticaonline.com"}

    def iter_article_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find article headlines with h2.title class."""
        return cast(list[Tag], soup.find_all("h2", class_="title"))

    def parse_article_element(self, element: Tag) -> ParsedArticleData | None:
        """Extract article data from an h2.title element."""
        title = self._extract_headline(element)
        url = self._extract_url(element)
        if not title or not url:
            return None

        return {
            "title": title,
            "url": url,
            "summary": None,  # Not present in HTML structure
            "image_url": self._extract_image_url(element),
        }

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from h2.title element."""
        link = element.find("a")
        if link:
            text: str = link.get_text(strip=True)
            if text:
                return text
        return None

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element."""
        link = element.find("a")
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = resolve_url(self.base_url, self.allowed_hosts, href)
                if resolved:
                    return resolved
        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element.

        Images are in the parent div.noticia container.
        """

        def resolve_image_from_tag(image_tag: Tag | None) -> str | None:
            if not image_tag or not isinstance(image_tag, Tag):
                return None
            # Try src first (most common), then data-src for lazy loading
            for attr in ("src", "data-src"):
                src = image_tag.get(attr)
                if src and isinstance(src, str):
                    # Skip data URIs (base64 encoded images)
                    if src.startswith("data:"):
                        continue
                    return self._resolve_image_url(src)

            # Fall back to srcset/data-srcset for responsive images
            for attr in ("srcset", "data-srcset"):
                srcset = image_tag.get(attr)
                if srcset and isinstance(srcset, str):
                    candidate = first_srcset_url(srcset)
                    if candidate and not candidate.startswith("data:"):
                        return self._resolve_image_url(candidate)
            return None

        link = element.find("a")
        href = link.get("href") if link and isinstance(link, Tag) else None

        # Prefer per-article container to avoid cross-article image mismatches.
        item_container = element.find_parent("div", class_="item")
        if item_container:
            if href and isinstance(href, str):
                anchor = item_container.find("a", href=href)
                image_url = resolve_image_from_tag(
                    anchor.find("img") if anchor else None
                )
                if image_url:
                    return image_url

            image_url = resolve_image_from_tag(item_container.find("img"))
            if image_url:
                return image_url

        # Fall back to parent div.noticia container
        parent = element.find_parent("div", class_="noticia")
        if parent:
            if href and isinstance(href, str):
                anchor = parent.find("a", href=href)
                image_url = resolve_image_from_tag(
                    anchor.find("img") if anchor else None
                )
                if image_url:
                    return image_url

            image_url = resolve_image_from_tag(parent.find("img"))
            if image_url:
                return image_url

        return None

    def _resolve_image_url(self, url: str) -> str:
        """Resolve potentially relative image URL to absolute."""
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return urljoin(self.base_url, url)
        return url
