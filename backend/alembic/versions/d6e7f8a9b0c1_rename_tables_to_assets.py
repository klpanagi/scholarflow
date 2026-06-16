"""rename tables to assets

Revision ID: d6e7f8a9b0c1
Revises: c5d8e1f2a3b4
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'd6e7f8a9b0c1'
down_revision = 'c5d8e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename tables from papers/paper_chunks to assets/asset_chunks
    op.execute("ALTER TABLE IF EXISTS paper_chunks RENAME TO asset_chunks")
    op.execute("ALTER TABLE IF EXISTS papers RENAME TO assets")
    
    # Rename foreign key constraint
    op.execute("ALTER TABLE IF EXISTS asset_chunks DROP CONSTRAINT IF EXISTS paper_chunks_paper_id_fkey")
    op.execute("ALTER TABLE IF EXISTS asset_chunks ADD CONSTRAINT asset_chunks_asset_id_fkey FOREIGN KEY (paper_id) REFERENCES assets(id)")
    
    # Rename indexes
    op.execute("ALTER INDEX IF EXISTS ix_papers_arxiv_id RENAME TO ix_assets_arxiv_id")
    op.execute("ALTER INDEX IF EXISTS ix_papers_doi RENAME TO ix_assets_doi")


def downgrade() -> None:
    # Rename indexes back
    op.execute("ALTER INDEX IF EXISTS ix_assets_arxiv_id RENAME TO ix_papers_arxiv_id")
    op.execute("ALTER INDEX IF EXISTS ix_assets_doi RENAME TO ix_papers_doi")
    
    # Rename foreign key constraint back
    op.execute("ALTER TABLE IF EXISTS asset_chunks DROP CONSTRAINT IF EXISTS asset_chunks_asset_id_fkey")
    op.execute("ALTER TABLE IF EXISTS asset_chunks ADD CONSTRAINT paper_chunks_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES papers(id)")
    
    # Rename tables back
    op.execute("ALTER TABLE IF EXISTS assets RENAME TO papers")
    op.execute("ALTER TABLE IF EXISTS asset_chunks RENAME TO paper_chunks")
