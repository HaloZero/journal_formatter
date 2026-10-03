"""add full text search index on journal_entry.entry_text

Revision ID: 1674c0fbd989
Revises: 0ca92536faf5
Create Date: 2026-10-03 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '1674c0fbd989'
down_revision = '0ca92536faf5'
branch_labels = None
depends_on = None


def upgrade():
    # Expression index, not a stored tsvector column - journal_entry is small enough
    # (one row per day) that computing to_tsvector() per query is cheap, so this skips
    # the extra generated-column/trigger upkeep a materialized tsvector would need.
    op.execute(
        "CREATE INDEX ix_journal_entry_entry_text_fts "
        "ON journal_entry USING GIN (to_tsvector('english', entry_text))"
    )


def downgrade():
    op.execute("DROP INDEX ix_journal_entry_entry_text_fts")
