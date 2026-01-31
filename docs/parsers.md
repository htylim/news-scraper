# Parsers

How to add a new site parser.

## Checklist

- Add a new parser in `src/news_scraper/parsers/sites/<source>.py`
- Subclass `BaseParser` and set:
  - `base_url` (canonical site URL)
  - `allowed_hosts` (hostnames allowed for articles)
- Register it with `@register_parser("<source>")`
- Add the module import to `load_site_parsers()` in `src/news_scraper/parsers/__init__.py`
- Implement:
  - `iter_article_elements(soup)` to yield candidates
  - `parse_article_element(element)` to return `ParsedArticleData` or `None`
- Use `resolve_url(base_url, allowed_hosts, href)` to normalize URLs
- Use `first_srcset_url(srcset)` when extracting from `srcset`
- Keep required fields:
  - `title` and `url` must be non-empty
- Optional fields:
  - `summary`, `image_url`, `published_at`, `authors`
- Add/adjust tests:
  - `tests/parsers/sites/test_<source>.py` for site-specific extraction
  - `tests/parsers/test_base.py` for shared behavior if needed
- If adding fixtures, place them in `tests/fixtures/`
- Run quality gates:
  - `uv run pytest`
  - `uv run pre-commit run --all-files`
