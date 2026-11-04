"""Alembic 运行环境。

数据库地址不写在 alembic.ini 里，而是复用 core.db.resolve_db_path()，
保证「迁移用的库」和「应用连的库」永远是同一个，
不会出现「迁移跑在 A 库、程序连 B 库」这种最难查的问题。

切换库只要设环境变量：
    ECARD_DB_PATH=D:/tmp/x.db alembic upgrade head
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context

# 让 alembic 能 import 到项目内的 core 包
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import build_engine, resolve_db_path  # noqa: E402
from core.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return f"sqlite+pysqlite:///{resolve_db_path()}"


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不连库。"""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：真正连库执行。"""
    engine = build_engine()
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite 不支持 ALTER COLUMN，批处理模式会用「建新表-搬数据-换名」实现
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
