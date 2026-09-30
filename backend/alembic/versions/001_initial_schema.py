"""001 初始建表

建立全部业务表、索引与 CHECK 约束。模型是唯一事实来源，因此这里直接以
``Base.metadata`` 建表（等价于 autogenerate 产物的第一版），保证迁移产物与
``app/models`` 完全一致。

Revision ID: 001
Revises: None
"""

from __future__ import annotations

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models import Base  # 延迟导入，避免迁移与运行时模型耦合

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import Base

    Base.metadata.drop_all(bind=op.get_bind())
