# Models Guidelines

Standards for creating SQLAlchemy models.

## Required Fields

All models must include:
- `id` - Auto-increment primary key
- `created_at` - Timestamp, set on insert (via `TimestampMixin`)
- `updated_at` - Timestamp, auto-updates on modification (via `TimestampMixin`)

Use `TimestampMixin` from `news_scraper.db.base`.

## Required Methods

- `__repr__` - Return readable string for debugging (include `id` and a key identifier)

## Type Annotations

- Use `Mapped[T]` for all columns
- Use `mapped_column()` instead of `Column()`
- Use `str | None` for optional fields (not `Optional[str]`)

## Naming

- Table names: lowercase, plural, snake_case (`sources`, `news_articles`)
- Model classes: PascalCase, singular (`Source`, `NewsArticle`)

## Constraints

- Always specify `nullable` explicitly
- Add `unique=True` where business logic requires it
- Use appropriate `String` lengths

## Session Usage

Use the `get_session()` context manager:

```python
from news_scraper.db import get_session

with get_session() as session:
    source = Source(name="Example", url="https://example.com")
    session.add(source)
    session.commit()
```

## Example

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from news_scraper.db.base import Base, TimestampMixin


class MyModel(TimestampMixin, Base):
    __tablename__ = "my_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    optional_field: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<MyModel(id={self.id}, name={self.name!r})>"
```
