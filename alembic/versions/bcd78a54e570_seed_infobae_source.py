"""seed infobae source

Revision ID: bcd78a54e570
Revises: 4fc40fb00ec0
Create Date: 2026-01-25 13:40:59.708448

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bcd78a54e570"
down_revision: str | Sequence[str] | None = "4fc40fb00ec0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed infobae source."""
    op.execute(
        """
        INSERT INTO sources (name, url, is_enabled, created_at, updated_at)
        SELECT
            'infobae',
            'https://www.infobae.com',
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM sources WHERE name = 'infobae'
        )
        """
    )


def downgrade() -> None:
    """Remove infobae source."""
    op.execute("DELETE FROM sources WHERE name = 'infobae'")
