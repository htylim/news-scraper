"""seed lanacion source

Revision ID: 94ac8a40f2db
Revises: 4cbaaf9285fb
Create Date: 2026-01-29 15:19:25.126639

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "94ac8a40f2db"
down_revision: str | Sequence[str] | None = "4cbaaf9285fb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed La Nacion source."""
    op.execute(
        """
        INSERT INTO sources (name, url, is_enabled, created_at, updated_at)
        SELECT
            'lanacion',
            'https://www.lanacion.com.ar',
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM sources WHERE name = 'lanacion'
        )
        """
    )


def downgrade() -> None:
    """Remove La Nacion source."""
    op.execute("DELETE FROM sources WHERE name = 'lanacion'")
