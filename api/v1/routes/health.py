"""健康检查。

给两件事用：
    1. 部署探针（进程活着 + 库能读）
    2. 前端启动时自检 —— 词库是空的就提示"先导入词库"，
       而不是让用户点开始默写后收到一个 `EMPTY_POOL`
"""
from __future__ import annotations

import logging

from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError

from api.v1.blueprint import bp, get_session
from api.v1.errors import ServiceUnavailable
from api.v1.presenters import iso
from core import queries
from core.models import utcnow

logger = logging.getLogger(__name__)

API_VERSION = "0.1.0"


@bp.get("/health")
def health():
    """确认 Flask 进程与 SQLite 可用，并回报词库条数。"""
    session = get_session()
    try:
        words_count = queries.count_words(session)
    except SQLAlchemyError:
        # 500 只回固定文案，堆栈进日志（不能把 SQL 语句漏给前端）
        logger.exception("health check: 数据库不可用")
        raise ServiceUnavailable("数据库不可用") from None

    return jsonify(
        {
            "status": "ok",
            "version": API_VERSION,
            # 能连上但表是空的 -> degraded：服务活着，但没有词可用
            "database": "ok" if words_count > 0 else "degraded",
            "words_count": words_count,
            "server_time": iso(utcnow()),
        }
    )
