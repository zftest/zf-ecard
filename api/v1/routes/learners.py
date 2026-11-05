"""学习者档案与统计总览。

MVP 没有 learners 表：单人自用引入登录只会增加摩擦，反而记不住密码。
所以 `learner_id` 是一个固定的 `default`，档案里的 `settings` 是服务端默认值，
前端可自行用 localStorage 覆盖（例如「今天想练 30 个」）。

`created_at` 不是编的：取该学习者最早一次作答时间。从未练习则为 null。
宁可返回 null，也不要返回 `datetime.now()` 骗人。
"""
from __future__ import annotations

from flask import jsonify, request

from api.v1.blueprint import bp, get_session
from api.v1.errors import NotFound
from api.v1.params import LearnerQuery, StatsQuery, parse_query
from api.v1.presenters import iso
from core import queries

DEFAULT_LEARNER_ID = "default"

DEFAULT_SETTINGS = {
    "daily_goal": 20,
    "default_mode": "zh_to_en",
    "accent": "uk",
    "hint_enabled": True,
}


def ensure_learner(learner_id: str) -> None:
    """MVP 只有一个学习者。其他 ID 一律 404，而不是静默当成 default。

    静默兜底会让前端拼错 ID 时也能"正常工作"，等到真要支持多用户那天，
    才发现所有历史数据都挂在同一个 key 上。
    """
    if learner_id != DEFAULT_LEARNER_ID:
        raise NotFound(f"学习者不存在：{learner_id}")


@bp.get("/learners/<learner_id>")
def get_learner(learner_id: str):
    """学习者档案 + 今日概览 + 累计分布，驱动首页。"""
    parse_query(LearnerQuery, request.args)
    ensure_learner(learner_id)
    session = get_session()

    return jsonify(
        {
            "learner_id": learner_id,
            "nickname": "同学",
            "created_at": iso(queries.first_activity_at(session, learner_id)),
            "settings": DEFAULT_SETTINGS,
            "today": queries.today_summary(
                session, learner_id, DEFAULT_SETTINGS["daily_goal"]
            ),
            "totals": queries.status_totals(session, learner_id),
        }
    )


@bp.get("/learners/<learner_id>/stats/overview")
def get_stats_overview(learner_id: str):
    """按技能拆分的掌握分布、近 N 日趋势、薄弱主题。"""
    params = parse_query(StatsQuery, request.args)
    ensure_learner(learner_id)
    session = get_session()

    return jsonify(
        {
            "by_skill": queries.stats_by_skill(session, learner_id),
            "trend": queries.trend(session, learner_id, params.days),
            "weak_themes": queries.weak_themes(session, learner_id),
        }
    )
