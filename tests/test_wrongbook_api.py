"""错词本接口契约测试（T5-1 / T5-2）。

守的七条：
1. `skill` 入参与出参都是**题型名**（zh_to_en），不是库里的技能名（spelling）。
2. `summary` 是角标数据源，不随 `due_before` 缩水。
3. 非法 `skill` / `sort` / `action` 返 400 且带中文字段提示。
4. 不存在的 (词, 技能) 返 404，而不是 200 + 空对象。
5. 拼错 learner_id 返 404，不静默兜底成 default。
6. `master` 后 `next_review_at` 为 null。
7. `due_before` 不带时区时按本地时区解释，不能当 UTC。
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.models import SkillProgress, Word

NOW_UTC = dt.datetime.now(dt.timezone.utc)


def _pick(api_app) -> tuple[int, int]:
    db = api_app.extensions["db"]
    with db.session() as session:
        word = session.scalars(
            select(Word).options(selectinload(Word.senses)).order_by(Word.id)
        ).first()
        return word.id, word.senses[0].id


def _seed(api_app, *, skill="spelling", wrong=1, box=1, due_at=None, status="active"):
    word_id, sense_id = _pick(api_app)
    db = api_app.extensions["db"]
    with db.session() as session:
        session.add(
            SkillProgress(
                learner_key="default",
                word_id=word_id,
                sense_id=sense_id,
                skill=skill,
                box_level=box,
                due_at=due_at or NOW_UTC,
                correct_count=0,
                wrong_count=wrong,
                status=status,
            )
        )
    return word_id


# ─────────────────────────────────────────────────────────────
# 列表
# ─────────────────────────────────────────────────────────────


def test_list_returns_contract_shape(api_app, api):
    word_id = _seed(api_app)

    resp = api.get("/api/v1/learners/default/wrongbook")
    assert resp.status_code == 200
    body = resp.get_json()

    assert set(body) == {"items", "pagination", "summary"}
    assert body["pagination"]["total"] == 1
    item = body["items"][0]
    assert item["word_id"] == word_id
    assert item["skill"] == "zh_to_en", "出参必须是题型名，不是库里的技能名"
    assert item["is_due"] is True
    assert item["next_review_at"].endswith("+08:00")
    assert set(item["audio"]) == {"uk", "us"}
    assert "phonetic_uk" in item and "meaning_cn" in item


def test_skill_filter_accepts_mode_name(api_app, api):
    """`?skill=zh_to_en` 要能筛出 spelling 技能的行。"""
    word_id = _seed(api_app, skill="spelling")
    with api_app.extensions["db"].session() as session:
        sense_id = session.scalar(
            select(SkillProgress.sense_id).where(SkillProgress.word_id == word_id)
        )
    with api_app.extensions["db"].session() as session:
        session.add(
            SkillProgress(
                learner_key="default", word_id=word_id, sense_id=sense_id,
                skill="meaning_recall", box_level=1, due_at=NOW_UTC,
                correct_count=0, wrong_count=1, status="active",
            )
        )

    resp = api.get("/api/v1/learners/default/wrongbook?skill=zh_to_en")
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    assert len(items) == 1
    assert items[0]["skill"] == "zh_to_en"

    resp = api.get("/api/v1/learners/default/wrongbook?skill=en_to_zh")
    assert [item["skill"] for item in resp.get_json()["items"]] == ["en_to_zh"]


def test_summary_not_shrunk_by_due_before(api_app, api):
    """筛时间窗只影响列表，角标不能跟着变。"""
    _seed(api_app, due_at=NOW_UTC - dt.timedelta(days=5))

    resp = api.get(
        "/api/v1/learners/default/wrongbook",
        query_string={"due_before": "2020-01-01T00:00:00+08:00"},
    )
    body = resp.get_json()
    assert body["pagination"]["total"] == 0
    assert body["summary"]["total"] == 1


def test_due_before_without_timezone_is_local(api_app, api):
    """不带时区的时间按本地时区解释。

    这条防的是「筛今天到期却少了几条」：若把 naive 时间当 UTC，
    实际边界会提前 8 小时，本地今晚到期的词就筛不出来了。
    """
    _seed(api_app, due_at=NOW_UTC)

    resp = api.get(
        "/api/v1/learners/default/wrongbook",
        query_string={"due_before": "2099-01-01T00:00:00"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["pagination"]["total"] == 1


def test_invalid_skill_returns_400(api):
    resp = api.get("/api/v1/learners/default/wrongbook?skill=spelling")
    assert resp.status_code == 400
    detail = resp.get_json()["error"]["details"][0]
    assert detail["field"] == "skill"
    assert "取值必须是" in detail["message"]


def test_invalid_sort_returns_400(api):
    resp = api.get("/api/v1/learners/default/wrongbook?sort=random")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_due_before_returns_400(api):
    resp = api.get("/api/v1/learners/default/wrongbook?due_before=yesterday")
    assert resp.status_code == 400
    detail = resp.get_json()["error"]["details"][0]
    assert "ISO 8601" in detail["message"]


def test_unknown_learner_returns_404(api):
    resp = api.get("/api/v1/learners/lrn_default/wrongbook")
    assert resp.status_code == 404, "拼错 learner_id 必须 404，不能静默当成 default"


def test_empty_wrongbook_returns_zero_not_error(api):
    resp = api.get("/api/v1/learners/default/wrongbook")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["items"] == []
    assert body["pagination"]["total"] == 0
    assert body["summary"] == {"total": 0, "due_today": 0, "mastered_this_week": 0}


# ─────────────────────────────────────────────────────────────
# 手动改状态
# ─────────────────────────────────────────────────────────────


def test_patch_master(api_app, api):
    word_id = _seed(api_app)

    resp = api.patch(
        f"/api/v1/learners/default/wrongbook/{word_id}",
        json={"skill": "zh_to_en", "action": "master"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "mastered"
    assert body["box"] == 5
    assert body["next_review_at"] is None, "已掌握的词没有下次复习时间"
    assert body["affected_senses"] >= 1

    listed = api.get("/api/v1/learners/default/wrongbook").get_json()
    assert listed["items"] == []


def test_patch_reset(api_app, api):
    word_id = _seed(api_app, box=4)

    resp = api.patch(
        f"/api/v1/learners/default/wrongbook/{word_id}",
        json={"skill": "zh_to_en", "action": "reset"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "learning"
    assert body["box"] == 1
    assert body["next_review_at"] is not None


def test_patch_missing_entry_returns_404(api_app, api):
    word_id, _ = _pick(api_app)

    resp = api.patch(
        f"/api/v1/learners/default/wrongbook/{word_id}",
        json={"skill": "zh_to_en", "action": "master"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_patch_wrong_skill_returns_404(api_app, api):
    """词在拼写上错过，但请求改的是词义 —— 不能顺手把拼写的改了。"""
    word_id = _seed(api_app, skill="spelling")

    resp = api.patch(
        f"/api/v1/learners/default/wrongbook/{word_id}",
        json={"skill": "en_to_zh", "action": "master"},
    )
    assert resp.status_code == 404


def test_patch_invalid_action_returns_400(api_app, api):
    word_id = _seed(api_app)

    resp = api.patch(
        f"/api/v1/learners/default/wrongbook/{word_id}",
        json={"skill": "zh_to_en", "action": "delete"},
    )
    assert resp.status_code == 400
    detail = resp.get_json()["error"]["details"][0]
    assert detail["field"] == "action"


def test_patch_without_body_returns_400(api_app, api):
    word_id = _seed(api_app)

    resp = api.patch(f"/api/v1/learners/default/wrongbook/{word_id}")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"
