"""词库维度：单元列表、主题列表。

这两个接口的唯一作用是给设置页提供**真实**选项与数量。
词数必须后端算，前端不许写死 —— 原型阶段写死「Unit 3 · 20 词」
而库里只有 13 条，出现胶囊与摘要自相矛盾。
"""
from __future__ import annotations

from flask import jsonify, request

from api.v1.blueprint import bp, get_session
from api.v1.params import UnitsQuery, ThemesQuery, parse_query
from core import queries


@bp.get("/units")
def list_units():
    """单元列表，带每个单元的实际词数、已掌握数、错词数。"""
    params = parse_query(UnitsQuery, request.args)
    items = queries.list_units(get_session(), params.learner_id, params.book)
    return jsonify({"items": items})


@bp.get("/themes")
def list_themes():
    """主题列表，带每个主题的实际词数与已掌握数。"""
    params = parse_query(ThemesQuery, request.args)
    items = queries.list_themes(get_session(), params.learner_id)
    return jsonify({"items": items})
