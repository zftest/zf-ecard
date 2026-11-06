"""add skill_progress.mastered_at

Revision ID: 0002_mastered_at
Revises: 0001_initial
Create Date: 2026-11-06

为什么要单独一列：
    B5 的错词本要给一个「本周掌握 N 个」的数字。用 last_seen_at 近似是错的 ——
    一个上周就已经掌握、本周只是又答对一次的词，会因为 last_seen_at 被刷新
    而算进本周，于是这个数字永远偏高，而且偏得没有规律。指标一旦说谎，
    用户就不会再看它。宁可加一列，也不要留一个自己都不敢信的统计。

为什么是 nullable：
    已经存在的进度行不知道当初是什么时候掌握的。留 NULL 的含义是
    「本迁移之前的事，不计入任何一周」—— 这比拿 created_at 或
    last_seen_at 编一个时间更诚实。

为什么不需要回填：
    NULL 不会被任何统计口径计入「本周掌握」，历史数据自然从下周起
    开始正常累计，不产生一次性尖峰。
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_mastered_at'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite 加可空列是瞬时的（不重写表），因此无需 batch_alter_table
    op.add_column(
        'skill_progress',
        sa.Column('mastered_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table('skill_progress') as batch_op:
        batch_op.drop_column('mastered_at')
