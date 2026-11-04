"""迁移一致性测试。

这组测试回答一个很实际的问题：
「我改了 core/models.py，忘了写迁移，什么时候会发现问题？」

答案：线上第一张表缺字段的时候。那时已经晚了。
所以这里用 alembic 自己的 check 把「模型」和「迁移」按在一起比对，
任何一边改了另一边没跟上，测试立刻红。
"""
import os
import sys

import pytest
from sqlalchemy import inspect

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from core.db import build_engine  # noqa: E402

EXPECTED_TABLES = {
    "books",
    "units",
    "words",
    "word_senses",
    "practice_sessions",
    "practice_items",
    "skill_progress",
}


@pytest.fixture()
def alembic_env(tmp_path, monkeypatch):
    """把 ECARD_DB_PATH 指向临时库，让 migrations/env.py 连到这个库。"""
    db_path = str(tmp_path / "migrate.db")
    monkeypatch.setenv("ECARD_DB_PATH", db_path)
    cfg = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
    return cfg, db_path


def table_names(db_path: str) -> set[str]:
    engine = build_engine(db_path)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_alembic_ini_is_ascii_only():
    """alembic.ini 里一旦出现中文注释，中文 Windows 下直接 UnicodeDecodeError。

    alembic 用 encoding="locale" 读配置，中文 Windows 的 locale 是 GBK，
    UTF-8 的中文字节解不出来，迁移还没开始就崩。
    """
    with open(os.path.join(PROJECT_ROOT, "alembic.ini"), "rb") as f:
        raw = f.read()
    assert raw.decode("ascii")  # 含非 ASCII 会在这里抛异常


def test_upgrade_head_creates_all_tables(alembic_env):
    cfg, db_path = alembic_env
    command.upgrade(cfg, "head")
    assert EXPECTED_TABLES <= table_names(db_path)


def test_models_and_migrations_are_in_sync(alembic_env):
    """模型与迁移必须完全一致；有差异时 alembic check 会抛异常。"""
    cfg, db_path = alembic_env
    command.upgrade(cfg, "head")
    command.check(cfg)  # 不抛异常即视为一致


def test_downgrade_base_removes_all_tables(alembic_env):
    """能降级才说明 downgrade 脚本真的被写过，而不是 pass。"""
    cfg, db_path = alembic_env
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    remaining = table_names(db_path)
    assert not (EXPECTED_TABLES & remaining)


def test_upgrade_is_idempotent(alembic_env):
    """重复 upgrade head 不应该报错（部署脚本经常被重复执行）。"""
    cfg, db_path = alembic_env
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")
    assert EXPECTED_TABLES <= table_names(db_path)
