"""Parser for La Nacion news site."""

from __future__ import annotations

from typing import cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from news_scraper.parsers.base import BaseParser, ParsedArticleData
from news_scraper.parsers.registry import register_parser
from news_scraper.parsers.utils import first_srcset_url, resolve_url


@register_parser("lanacion")
class LaNacionParser(BaseParser):
    """Parser for La Nacion front page HTML."""

    base_url = "https://www.lanacion.com.ar"
    allowed_hosts = {"www.lanacion.com.ar", "lanacion.com.ar"}

    def iter_article_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find article cards with ln-card class."""
        return cast(list[Tag], soup.find_all("article", class_="ln-card"))

    def parse_article_element(self, element: Tag) -> ParsedArticleData | None:
        """Extract article data from an ln-card article element."""
        url = self._extract_url(element)
        title = self._extract_headline(element)
        if not title or not url:
            return None

        return {
            "title": title,
            "url": url,
            "summary": self._extract_summary(element),
            "image_url": self._extract_image_url(element),
        }

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element."""
        link = element.find("a", class_="ln-link")
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = resolve_url(self.base_url, self.allowed_hosts, href)
                if resolved:
                    return resolved

        link = element.find("a", href=True)
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                return resolve_url(self.base_url, self.allowed_hosts, href)

        return None

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from article element."""
        h1 = element.find("h1")
        if h1:
            text = (h1.get_text(strip=False) or "").strip()
            if text:
                return text

        h2 = element.find("h2")
        if h2:
            text = (h2.get_text(strip=False) or "").strip()
            if text:
                return text

        return None

    def _extract_summary(self, element: Tag) -> str | None:
        """Extract summary from article element."""
        h1 = element.find("h1")
        h2 = element.find("h2")
        if h1 and h2:
            text: str = h2.get_text(strip=True)
            if text:
                return text

        h3 = element.find("h3")
        if h3:
            text = h3.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element."""
        img = element.find("img")
        if img and isinstance(img, Tag):
            for attr in ("src", "data-src"):
                src = img.get(attr)
                if src and isinstance(src, str):
                    return self._resolve_image_url(src)

            for attr in ("srcset", "data-srcset"):
                srcset = img.get(attr)
                if srcset and isinstance(srcset, str):
                    candidate = first_srcset_url(srcset)
                    if candidate:
                        return self._resolve_image_url(candidate)

        return None

    def _resolve_image_url(self, url: str) -> str:
        """Resolve potentially relative image URL to absolute."""
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return urljoin(self.base_url, url)
        return url
