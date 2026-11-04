"""蓝图对象与请求级依赖。

单独放一个模块，是为了避免「蓝图定义在 __init__、路由又 import __init__」
造成的循环导入 —— 这类问题在测试里表现成 ImportError，
在生产里表现成启动即崩，排查成本远高于多建一个文件。
"""
from __future__ import annotations

from flask import Blueprint, current_app, g
from sqlalchemy.orm import Session

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# 供 app 层钩子判断「这个请求是不是新接口」，从而只在 /api/v1 上做事，
# 不改变旧页面的任何行为
API_PREFIX = "/api/v1"


def get_session() -> Session:
    """当前请求专属的数据库会话（由 before_request 打开）。"""
    session = g.get("db_session")
    if session is None:  # pragma: no cover - 只会在忘记注册蓝图钩子时发生
        raise RuntimeError("数据库会话未初始化：确认 register_api_v1 已执行")
    return session


@bp.before_request
def _open_session() -> None:
    database = current_app.extensions.get("db")
    if database is None:  # pragma: no cover
        raise RuntimeError("app.extensions['db'] 缺失：create_app 未调用 core.db.init_app")
    g.db_session = database.session_factory()


@bp.teardown_request
def _close_session(exc: BaseException | None) -> None:
    session = g.pop("db_session", None)
    if session is None:
        return
    if exc is not None:
        # 读接口正常不会写库，但一旦将来某个 GET 顺手写了缓存，
        # 异常时必须回滚，否则半截数据会被下一次请求读到
        session.rollback()
    session.close()
