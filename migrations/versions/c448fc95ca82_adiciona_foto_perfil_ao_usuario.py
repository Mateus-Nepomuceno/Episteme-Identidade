"""adiciona_foto_perfil_ao_usuario

Revision ID: c448fc95ca82
Revises: c775a07c90c9
Create Date: 2026-11-22 15:09:36.762641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c448fc95ca82'
down_revision: Union[str, Sequence[str], None] = 'c775a07c90c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'usuarios',
        sa.Column('foto_dados', sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        'usuarios',
        sa.Column('foto_tipo', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('usuarios', 'foto_tipo')
    op.drop_column('usuarios', 'foto_dados')
