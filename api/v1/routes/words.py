"""单词库：列表查询与详情。

两个容易做错的地方，这里都处理了：

1. **列表的 `progress` 可能是 null**（这个词还没学过）。
   前端不能直接 `word.progress.status`，否则第一次打开词库页就白屏。
   这不是"前端小心点"能解决的，接口本身要允许 null 并把它写进契约。

2. **`skill` 参数是题型名，库里存的是技能名。**
   换算只在 core.vocabulary 里做一次，路由层不允许出现 `spelling` 这种字面量。
"""
from __future__ import annotations

from flask import jsonify, request

from api.v1.blueprint import bp, get_session
from api.v1.errors import NotFound
from api.v1.params import WordDetailQuery, WordListQuery, parse_query
from api.v1.presenters import (
    present_pagination,
    present_word_brief,
    present_word_detail,
)
from core import queries
from core.vocabulary import mode_to_skill


@bp.get("/words")
def list_words():
    """单词列表：搜索、按单元/主题/词性/状态筛选、排序、分页。"""
    params = parse_query(WordListQuery, request.args)
    session = get_session()
    skill = mode_to_skill(params.skill)

    words, total = queries.list_words(
        session,
        learner_key=params.learner_id,
        skill=skill,
        q=params.q,
        unit_id=params.unit,
        theme=params.theme,
        pos=params.pos,
        statuses=params.status,
        sort=params.sort,
        page=params.page,
        page_size=params.page_size,
    )

    # 一次捞出整页的进度，避免每个词查一次的 N+1
    progresses = queries.progress_for_words(
        session, params.learner_id, skill, [word.id for word in words]
    )

    return jsonify(
        {
            "items": [
                present_word_brief(word, progresses.get(word.id, [])) for word in words
            ],
            "pagination": present_pagination(params.page, params.page_size, total),
        }
    )


@bp.get("/words/<int:word_id>")
def get_word(word_id: int):
    """单词详情：全部义项、例句、发音与逐技能进度。"""
    params = parse_query(WordDetailQuery, request.args)
    session = get_session()

    word = queries.get_word(session, word_id)
    if word is None:
        raise NotFound("单词不存在")

    progresses = queries.progress_by_skill(session, params.learner_id, word.id)
    return jsonify(present_word_detail(word, progresses))
