"""错词本：列表与手动改状态。

两条边界：

1. **列表按 (词, 技能) 一行。** 同一单词的不同技能分开显示，
   因为「拼写会了、听音还没会」是有意义的信息；同一技能下的多个义项合并。
   详见 core/wrongbook.py 的聚合规则。

2. **`master` 之后 `next_review_at` 是 null，不是某个时间。**
   已掌握的词没有"下次复习"。返回一个时间会让前端画出一个
   永远点不掉的提醒，用户只能手动关掉它。
"""
from __future__ import annotations

from flask import jsonify, request

from api.v1.blueprint import bp, get_session
from api.v1.errors import NotFound
from api.v1.params import UpdateWrongbookBody, WrongbookQuery, parse_body, parse_query
from api.v1.presenters import (
    present_pagination,
    present_wrongbook_entry,
    present_wrongbook_update,
)
from api.v1.routes.learners import ensure_learner
from core import wrongbook
from core.vocabulary import mode_to_skill


@bp.get("/learners/<learner_id>/wrongbook")
def list_wrongbook(learner_id: str):
    """错词本列表。默认按到期优先排序，`summary` 是侧边栏角标的数据源。"""
    params = parse_query(WrongbookQuery, request.args)
    ensure_learner(learner_id)

    db = get_session()
    entries, total, summary = wrongbook.list_entries(
        db,
        learner_key=learner_id,
        # 入参是题型名，查询层用技能名（见 core/vocabulary.py 的换算说明）
        skill=mode_to_skill(params.skill) if params.skill else None,
        due_before=params.due_before,
        sort=params.sort,
        page=params.page,
        page_size=params.page_size,
    )

    return jsonify(
        {
            "items": [present_wrongbook_entry(entry) for entry in entries],
            "pagination": present_pagination(params.page, params.page_size, total),
            "summary": summary,
        }
    )


@bp.patch("/learners/<learner_id>/wrongbook/<int:word_id>")
def update_wrongbook_entry(learner_id: str, word_id: int):
    """标记「已掌握」或「重置重练」。

    动作作用在该 (词, 技能) 下的**全部义项**上：
    列表是按 (词, 技能) 一行展示的，只改一个义项会出现
    「点了已掌握，这个单词还在列表里」的自相矛盾。
    返回的 `affected_senses` 就是这个动作实际改了几个义项。
    """
    params = parse_body(UpdateWrongbookBody, request.get_json(silent=True))
    ensure_learner(learner_id)

    db = get_session()
    result = wrongbook.update_entry(
        db,
        learner_key=learner_id,
        word_id=word_id,
        skill=mode_to_skill(params.skill),
        action=params.action,
    )
    if result is None:
        raise NotFound("该词不在此技能维度的错词本中")
    db.commit()

    return jsonify(present_wrongbook_update(result))
