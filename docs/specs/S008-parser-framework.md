# Goal
Refactor the parser architecture so adding new site parsers is consistent, low-effort, and does not assume a single CSS selector per site. Provide a base parsing workflow that handles cross-cutting concerns (logging, dedupe, position assignment), while allowing each parser to supply its own article discovery strategy. Example usage: a new parser only implements `iter_article_elements()` and `parse_article_element()` and registers itself with `@register_parser("source")`.

# Problem / Context
Current parsers duplicate the same parse loop and differ in error handling and URL normalization. A shared base would reduce duplication, but we cannot assume a single `find_all()` selector for future sites. We need a base that enforces behavior without constraining how articles are discovered.

# Deliverables
- Introduce a `BaseParser` abstract class that owns the parsing workflow and requires subclasses to implement article discovery and per-article extraction.
- Support multiple or non-CSS-based discovery by requiring a `iter_article_elements()` method instead of a single selector.
- Consolidate shared behavior in `BaseParser.parse()`:
  - BeautifulSoup initialization (or override hook like `build_soup(html)` for non-standard parsing)
  - Per-candidate error isolation and logging (skip the failing element, continue loop)
  - URL-based deduplication using the normalized URL as the key (override-able in subclasses if needed)
  - 1-based position assignment based on discovery order
- Assume BeautifulSoup usage and `Tag` elements:
  - `iter_article_elements(soup: BeautifulSoup) -> Iterable[Tag]`
  - `parse_article_element(element: Tag) -> ParsedArticleData | None`
- Define `ParsedArticleData` as a TypedDict with explicit fields and optionality:
  - Required: `title: str`, `url: str`
  - Optional: `summary: str | None`, `image_url: str | None`
  - Optional (allowed but unused in `ParsedArticle` for now): `published_at: datetime | None`, `authors: list[str] | None`
  - Any additional fields must be documented and either mapped or explicitly ignored.
- Specify the exact mapping from `ParsedArticleData` to `ParsedArticle`:
  - `title` → `ParsedArticle.headline` (trim whitespace, must be non-empty)
  - `url` → `ParsedArticle.url` (must already be normalized by `resolve_url`)
  - `summary` → `ParsedArticle.summary` (default `None` if missing/blank)
  - `image_url` → `ParsedArticle.image_url` (default `None` if missing/blank)
  - `position` is assigned in `BaseParser.parse()` and is never provided by site parsers
  - `published_at` and `authors` are ignored for now; if/when added to `ParsedArticle`, update this mapping
- Parsers receive `base_url` and `allowed_hosts` as class attributes on `BaseParser` with per-parser overrides in subclasses. If this becomes limiting, we can switch to constructor args in a follow-up.
- Add shared URL and image helpers in `parsers/utils/`:
  - `resolve_url(base_url, allowed_hosts, href)` that:
    - rejects empty/fragment-only hrefs
    - resolves relative/protocol-relative URLs
    - rejects external hosts (define subdomain rules and case sensitivity)
    - rejects empty/root paths
    - strips query params and fragments (La Nacion behavior as the default; allow override if needed)
  - `first_srcset_url(srcset)`
- Create a lightweight registry module (`parsers/registry.py`) with a `@register_parser("source")` decorator. `parsers/__init__.py` should only re-export `get_parser`, `ParsedArticle`, and `ParserNotFoundError`.
  - Registry should raise on duplicate source names.
  - `get_parser()` should raise `ParserNotFoundError` on unknown sources with a clear message.
- Move site parsers into `parsers/sites/` and convert them to subclasses of `BaseParser`.
- Ensure consistent logging behavior across parsers (use `log.exception` inside the base loop) and include `source`, `url`, and `position` in log metadata.
- Document the “how to add a parser” checklist in a new doc page (`docs/parsers.md`) and reference it in the documentation section.
- Add/adjust tests (mirror production structure):
  - Move site parser tests under `tests/parsers/sites/` to match `src/news_scraper/parsers/sites/`.
  - Keep shared parser tests in `tests/parsers/` (e.g., `test_base.py`, `test_registry.py`).
  - Unit tests for `BaseParser` behavior using a minimal stub parser:
    - dedupe on normalized URL
    - position assignment in discovery order
    - per-element error isolation with logged exception
  - Parser-specific tests that only validate site-specific logic (not parse loop).

Reference code in this spec is for clarity only; do not copy-paste blindly.

Example interface (reference only):
```python
class BaseParser:
    def parse(self, html: str) -> list[ParsedArticle]:
        ...

    @abstractmethod
    def iter_article_elements(
        self, soup: BeautifulSoup
    ) -> Iterable[Tag]:
        ...

    @abstractmethod
    def parse_article_element(
        self, element: Tag
    ) -> ParsedArticleData | None:
        ...
```

# Acceptance Criteria
- [ ] New parsers can implement article discovery without a single selector assumption.
- [ ] Shared parse loop exists in `BaseParser.parse()` with consistent error handling, dedupe, and position assignment.
- [ ] Existing parsers are migrated to `BaseParser` and moved under `parsers/sites/`.
- [ ] Registry uses decorator-based registration; no manual dict edits when adding parsers.
- [ ] URL normalization behavior is consistent across parsers or explicitly overridden (including `allowed_hosts` rules).
- [ ] Tests cover base behavior (dedupe, position, error isolation) and parser-specific extraction.
- [ ] Documentation includes a clear “add new parser” checklist in `docs/parsers.md`.
- [ ] `uv run pytest`
- [ ] `uv run pre-commit run --all-files`

# File Summary
- New: `src/news_scraper/parsers/registry.py`
- New: `src/news_scraper/parsers/utils/__init__.py`
- New: `src/news_scraper/parsers/utils/url.py`
- New: `src/news_scraper/parsers/utils/images.py`
- New: `docs/parsers.md`
- Move/Update: `src/news_scraper/parsers/infobae.py` -> `src/news_scraper/parsers/sites/infobae.py`
- Move/Update: `src/news_scraper/parsers/lanacion.py` -> `src/news_scraper/parsers/sites/lanacion.py`
- Update: `src/news_scraper/parsers/base.py`
- Update: `src/news_scraper/parsers/__init__.py`
- Move/Update: `tests/parsers/test_infobae.py` -> `tests/parsers/sites/test_infobae.py`
- Move/Update: `tests/parsers/test_lanacion.py` -> `tests/parsers/sites/test_lanacion.py`
- Update: tests for base parser and registry

# Open Questions / Resolved Decisions
- Resolved: Do not require a single CSS selector; use `iter_article_elements()` to allow any discovery strategy.
- Resolved: Keep BeautifulSoup mandatory for now; elements are `Tag`.
- Resolved: URL normalization follows current La Nacion behavior (strip query/fragment, reject root/fragment-only).
