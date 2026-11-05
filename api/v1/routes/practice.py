"""练习与判题接口：建会话、续答、提交答案、结束。

四个接口的边界只有一条最容易被写错：

    **判错是业务结果，不是 HTTP 错误。**

答错返回 200 + `correct: false`。只有会话不存在 / 已结束 / 已过期这类
协议层问题才返 4xx。这条不统一，前端拦截器会把"答错"当成"请求失败"
弹全局红条，孩子每答错一次就弹一次"网络异常"。
"""
from __future__ import annotations

from flask import jsonify, request
from sqlalchemy import select

from api.v1.blueprint import bp, get_session
from api.v1.errors import (
    EmptyPool,
    NotFound,
    SessionExpired,
    SessionFinished,
    bad_request,
)
from api.v1.params import (
    CreateSessionBody,
    SessionQuery,
    SubmitAnswerBody,
    parse_body,
    parse_query,
)
from api.v1.presenters import present_finish, present_grade, present_session
from api.v1.routes.learners import ensure_learner
from core import practice
from core.models import PracticeItem, PracticeSession


@bp.post("/practice/sessions")
def create_practice_session():
    """按「范围 + 题型 + 题量 + 顺序」抽题，返回可直接作答的题目。"""
    params = parse_body(CreateSessionBody, request.get_json(silent=True))
    ensure_learner(params.learner_id)

    if params.range in ("unit", "theme") and not params.range_value:
        raise bad_request("range_value", f"range={params.range} 时必须提供 range_value")
    if params.range == "unit":
        try:
            int(params.range_value or "")
        except ValueError:
            raise bad_request("range_value", "range=unit 时必须是整数单元 ID") from None

    db = get_session()
    session_row, warnings = practice.create_session(
        db,
        learner_key=params.learner_id,
        mode=params.mode,
        range_type=params.range,
        range_value=params.range_value,
        size=params.size,
        order=params.order,
        hint_enabled=params.hint_enabled,
    )
    if session_row.size == 0:
        # 空池子是 409 而不是 200：前端据此弹"换个范围"，而不是渲染一个空答题页
        raise EmptyPool("该范围没有可练的词，请先导入词库或更换范围")

    db.commit()

    items = list(session_row.items)
    words = practice.load_words(db, [item.word_id for item in items])
    return (
        jsonify(present_session(session_row, items, words, warnings=warnings)),
        201,
    )


@bp.get("/practice/sessions/<int:session_id>")
def get_practice_session(session_id: int):
    """断点续答：刷新页面后拿回同一批题与当前进度。"""
    params = parse_query(SessionQuery, request.args)
    db = get_session()

    session_row = db.get(PracticeSession, session_id)
    if session_row is None:
        raise NotFound("练习会话不存在")
    if practice.session_state(session_row) == practice.STATUS_EXPIRED:
        raise SessionExpired("本次练习已超过 2 小时，请重新开始")

    items = list(session_row.items)
    words = practice.load_words(db, [item.word_id for item in items])
    return jsonify(
        present_session(
            session_row, items, words, include_answers=params.include_answers
        )
    )


@bp.post("/practice/sessions/<int:session_id>/answers")
def submit_answer(session_id: int):
    """判一道题，并即时更新该词在对应技能上的盒子与下次复习时间。"""
    params = parse_body(SubmitAnswerBody, request.get_json(silent=True))
    db = get_session()

    session_row = db.get(PracticeSession, session_id)
    if session_row is None:
        raise NotFound("练习会话不存在")

    state = practice.session_state(session_row)
    if state == practice.STATUS_EXPIRED:
        raise SessionExpired("本次练习已超过 2 小时，请重新开始")
    if state == practice.STATUS_FINISHED:
        raise SessionFinished("本次练习已结束，请重新开始")

    item = db.scalar(
        select(PracticeItem).where(
            PracticeItem.id == params.item_id,
            PracticeItem.session_id == session_id,
        )
    )
    if item is None:
        raise NotFound("题目不存在")

    payload = practice.submit_answer(
        db,
        session_row=session_row,
        item=item,
        answer=params.answer,
        hint_used=params.hint_used,
        elapsed_ms=params.elapsed_ms or None,
    )
    db.commit()

    return jsonify(present_grade(item, payload))


@bp.post("/practice/sessions/<int:session_id>/finish")
def finish_practice_session(session_id: int):
    """结束会话并汇总成绩。幂等：重复调用数字不变、不重复计数。"""
    db = get_session()

    session_row = db.get(PracticeSession, session_id)
    if session_row is None:
        raise NotFound("练习会话不存在")
    if practice.session_state(session_row) == practice.STATUS_EXPIRED:
        raise SessionExpired("本次练习已超过 2 小时，请重新开始")

    summary = practice.finish_session(db, session_row)
    db.commit()

    return jsonify(present_finish(summary))
