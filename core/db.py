"""数据库连接与会话管理。

SQLite 的三个 PRAGMA 是刻意开的，缺一个都会在真实使用中出问题：

    journal_mode=WAL   导出 PNG 时（Playwright 另起进程读库）不阻塞答题写入
    foreign_keys=ON    SQLite 默认**不**校验外键，不开就会留下孤儿义项
    busy_timeout=5000  并发写入时等 5 秒再报错，而不是立刻 database is locked
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from core.models import Base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "app.db")

# 内存库专用标识：不建目录、不走 WAL（WAL 对 :memory: 无意义）
MEMORY_MARKERS = (":memory:", "file::memory:")


def resolve_db_path(explicit: str | None = None) -> str:
    """决定数据库文件路径。

    优先级：显式参数 > 环境变量 ECARD_DB_PATH > data/app.db。
    环境变量这一层让测试与 CI 可以完全不碰真实库。
    """
    if explicit:
        return explicit
    env = os.environ.get("ECARD_DB_PATH")
    if env:
        return env
    return DEFAULT_DB_PATH


def _is_memory(path: str) -> bool:
    return any(marker in path for marker in MEMORY_MARKERS)


def build_engine(db_path: str | None = None, echo: bool = False) -> Engine:
    """按路径建 Engine，并挂上 SQLite PRAGMA。"""
    path = resolve_db_path(db_path)
    memory = _is_memory(path)

    if not memory:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

    url = "sqlite+pysqlite:///:memory:" if memory else f"sqlite+pysqlite:///{path}"
    engine = create_engine(
        url,
        echo=echo,
        future=True,
        # Flask 的多线程 dev server 下，连接会被不同线程复用
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        try:
            if not memory:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    return engine


class Database:
    """Engine + Session 工厂的轻封装。

    用法：
        db = Database()
        with db.session() as s:
            s.add(word)

    退出 with 时自动 commit，抛异常自动 rollback —— 调用方不需要记着写这两行。
    """

    def __init__(self, db_path: str | None = None, echo: bool = False) -> None:
        self.path = resolve_db_path(db_path)
        self.engine: Engine = build_engine(self.path, echo=echo)
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,  # commit 后仍可读对象属性，避免懒加载报错
            future=True,
        )

    @contextmanager
    def session(self, commit: bool = True) -> Iterator[Session]:
        """开一个会话。commit=False 时正常执行但最终回滚。

        commit=False 是给「空跑」用的：调用方写的是与正式导入完全相同的代码，
        区别只在最后不提交。这样空跑的结果不可能和真实导入不一致 ——
        如果用 `if not dry_run` 之类的分支去模拟，两边迟早会漂移，
        而空跑恰恰是用户判断「要不要真的导入」的唯一依据。

        回滚前 session.flush() 过的数据在会话内仍然可查，
        所以空跑照样能打印出「导入后每个单元有多少词」。
        """
        session = self.session_factory()
        try:
            yield session
            if commit:
                session.commit()
            else:
                session.rollback()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all(self) -> None:
        """按模型建表。

        仅用于测试与本地快速起步；正式环境请用 Alembic 迁移，
        否则以后加字段无法回退。
        """
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        """删表（仅测试用）。"""
        Base.metadata.drop_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()


_default_db: Database | None = None


def get_database() -> Database:
    """进程内默认数据库单例（供 B3 的 API 层与脚本使用）。"""
    global _default_db
    if _default_db is None:
        _default_db = Database()
    return _default_db


def init_app(app) -> None:
    """把数据库挂到 Flask 应用上。

    用 app.extensions 而不是模块级全局，测试可以给每个 app 注入独立的临时库，
    不会互相污染。
    """
    db_path = app.config.get("DB_PATH") or resolve_db_path()
    database = Database(db_path)
    app.extensions["db"] = database
    app.config["DB_PATH"] = database.path
    return database
