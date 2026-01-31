"""seed lapoliticaonline source

Revision ID: f08672783f59
Revises: 94ac8a40f2db
Create Date: 2026-01-31 19:13:24.418690

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f08672783f59"
down_revision: str | Sequence[str] | None = "94ac8a40f2db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed La Política Online source."""
    op.execute(
        """
        INSERT INTO sources (name, url, is_enabled, created_at, updated_at)
        SELECT
            'lapoliticaonline',
            'https://www.lapoliticaonline.com',
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM sources WHERE name = 'lapoliticaonline'
        )
        """
    )


def downgrade() -> None:
    """Remove La Política Online source."""
    op.execute("DELETE FROM sources WHERE name = 'lapoliticaonline'")
