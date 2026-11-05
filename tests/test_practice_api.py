"""练习接口契约测试（T4-4 ~ T4-7）。

守的十条"一改就静默出错"的约定：

1. 出题响应**不能**带答案（`expected` / 汉译英的 `form`）。
2. 答错返回 200，不是 4xx —— 否则前端把业务结果当网络故障。
3. `first_try_correct = correct && !hint_used`，这是首答正确率的定义。
4. 同一题重复提交覆盖成绩、但**不重复计数、不重复升盒**。
5. 结束接口幂等：调用两次数字完全一样。
6. 已结束 / 已过期会话提交答案返 409，不是 500。
7. 空词池返 409 EMPTY_POOL，不是 200 + 空列表。
8. 池子不足返实际题数 + warnings，不是 500、也不是硬凑。
9. 进度按技能分开记：汉译英答对不影响听音写词。
10. 别人的 item_id 塞进来必须 404，不能"顺手"判了。
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from core.models import PracticeItem, PracticeSession, SkillProgress


def _unit(api, *, min_words: int = 1, max_words: int | None = None) -> dict:
    for unit in api.get("/api/v1/units").get_json()["items"]:
        count = unit["word_count"]
        if count >= min_words and (max_words is None or count <= max_words):
            return unit
    raise AssertionError("种子词库里找不到符合条件的单元")


def _create(api, **overrides):
    unit = overrides.pop("unit", None) or _unit(api, min_words=10)
    payload = {
        "learner_id": "default",
        "range": "unit",
        "range_value": str(unit["unit_id"]),
        "mode": "zh_to_en",
        "size": 10,
        "order": "sequential",
        "hint_enabled": True,
    }
    payload.update(overrides)
    return api.post("/api/v1/practice/sessions", json=payload)


def _expected(api_app, item_id: int) -> str:
    db = api_app.extensions["db"]
    with db.session() as session:
        return session.get(PracticeItem, item_id).expected_snapshot


def _answer(api, session_id: int, item_id: int, answer: str, **extra):
    payload = {"item_id": item_id, "answer": answer}
    payload.update(extra)
    return api.post(
        f"/api/v1/practice/sessions/{session_id}/answers", json=payload
    )


# ─────────────────────────────────────────────────────────────
# 建会话
# ─────────────────────────────────────────────────────────────


def test_create_session_returns_items_without_answers(api):
    resp = _create(api)
    assert resp.status_code == 201
    body = resp.get_json()

    assert body["status"] == "running"
    assert body["size"] == len(body["items"]) == 10
    assert body["progress"] == {"answered": 0, "correct": 0, "wrong": 0}
    assert body["expires_at"].endswith("+08:00")

    first = body["items"][0]
    assert first["prompt"], "汉译英必须给中文题干"
    assert first["hint"].startswith(first["hint"][0]) and "_" in first["hint"]
    # 答案绝不能被下发
    assert "expected" not in first
    assert "form" not in first, "汉译英的 form 就是答案本身"


def test_create_session_reports_pool_shortage(api):
    """选 20 题但单元只有几个词：出实际题数 + 明确告知，而不是报错。

    注意题池按「义项」计：一个词有 2 个释义就是 2 道题，
    所以题数可能**大于**单元列表里的词数，这是设计如此，不是 bug。
    """
    unit = _unit(api, min_words=1, max_words=8)
    resp = _create(api, unit=unit, size=20)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["size"] == len(body["items"])
    assert body["size"] >= unit["word_count"]
    assert body["warnings"][0]["code"] == "POOL_INSUFFICIENT"


def test_create_session_empty_pool_returns_409(api):
    unit = _unit(api, min_words=0, max_words=0)
    resp = _create(api, unit=unit, size=10)
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "EMPTY_POOL"


def test_create_session_unknown_learner_returns_404(api):
    resp = _create(api, learner_id="typo")
    assert resp.status_code == 404


def test_create_session_unit_range_requires_value(api):
    resp = api.post(
        "/api/v1/practice/sessions",
        json={"range": "unit", "mode": "zh_to_en", "size": 10},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["details"][0]["field"] == "range_value"


def test_create_session_rejects_missing_mode(api):
    resp = api.post("/api/v1/practice/sessions", json={"range": "all"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(item["field"] == "mode" for item in body["error"]["details"])


def test_create_session_rejects_too_small_size(api):
    resp = _create(api, size=3)
    assert resp.status_code == 400


def test_create_session_bad_json_returns_validation_error(api):
    resp = api.post(
        "/api/v1/practice/sessions", data="not-json", content_type="application/json"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_audio_session_warns_when_no_audio_files(api):
    """还没生成音频时必须明确告知降级，而不是给一个点了没声音的页面。"""
    resp = _create(api, mode="audio_to_en")
    assert resp.status_code == 201
    body = resp.get_json()
    codes = [warn["code"] for warn in body.get("warnings", [])]
    assert "AUDIO_UNAVAILABLE" in codes
    item = body["items"][0]
    assert item["prompt"] is None, "听音题不能给题干，给了就是给答案"
    assert item["audio_available"] is False


# ─────────────────────────────────────────────────────────────
# 提交答案
# ─────────────────────────────────────────────────────────────


def test_correct_answer_returns_200_and_advances_box(api, api_app):
    body = _create(api).get_json()
    item = body["items"][0]
    expected = _expected(api_app, item["item_id"])

    resp = _answer(api, body["session_id"], item["item_id"], expected.upper())
    assert resp.status_code == 200
    result = resp.get_json()

    assert result["correct"] is True
    assert result["first_try_correct"] is True
    assert result["distance"] == 0
    assert result["progress_updated"]["box_before"] is None
    assert result["progress_updated"]["box_after"] == 2
    assert result["session_progress"] == {"answered": 1, "correct": 1, "wrong": 0}


def test_wrong_answer_is_200_not_4xx(api):
    body = _create(api).get_json()
    item = body["items"][0]

    resp = _answer(api, body["session_id"], item["item_id"], "zzz")
    assert resp.status_code == 200, "判错是业务结果，不能当 HTTP 错误"
    result = resp.get_json()

    assert result["correct"] is False
    assert result["first_try_correct"] is False
    assert result["progress_updated"]["box_after"] == 1
    assert result["feedback"]


def test_empty_answer_is_graded_not_rejected(api):
    """直接点"不会"也是合法作答，不该返 400。"""
    body = _create(api).get_json()
    item = body["items"][0]

    resp = _answer(api, body["session_id"], item["item_id"], "")
    assert resp.status_code == 200
    assert resp.get_json()["correct"] is False


def test_hint_used_kills_first_try_but_keeps_correct(api, api_app):
    body = _create(api).get_json()
    item = body["items"][0]
    expected = _expected(api_app, item["item_id"])

    result = _answer(
        api, body["session_id"], item["item_id"], expected, hint_used=True
    ).get_json()
    assert result["correct"] is True
    assert result["first_try_correct"] is False
    assert "提示" in result["feedback"]


def test_resubmit_overwrites_but_does_not_double_count(api, api_app):
    """重复提交不重复升盒、不重复计数，也不改写首答结论。"""
    body = _create(api).get_json()
    item = body["items"][0]
    expected = _expected(api_app, item["item_id"])

    first = _answer(api, body["session_id"], item["item_id"], "zzz").get_json()
    assert first["progress_updated"] is not None

    second = _answer(api, body["session_id"], item["item_id"], expected).get_json()
    assert second["correct"] is True
    assert second["first_try_correct"] is False, "首答错了就是错了，重试不能翻案"
    assert second["progress_updated"] is None, "同一题不再重复升盒"
    assert second["session_progress"]["answered"] == 1

    db = api_app.extensions["db"]
    with db.session() as session:
        rows = session.scalars(
            select(SkillProgress).where(SkillProgress.word_id == item["word_id"])
        ).all()
        assert sum(row.wrong_count for row in rows) == 1
        assert sum(row.correct_count for row in rows) == 0, "重试答对不再计入正确数"


def test_item_from_other_session_returns_404(api):
    first = _create(api).get_json()
    second = _create(api).get_json()

    resp = _answer(api, first["session_id"], second["items"][0]["item_id"], "hello")
    assert resp.status_code == 404


def test_progress_is_separated_by_skill(api, api_app):
    """汉译英答对，不代表听音写词会了 —— 两条进度必须独立。"""
    body = _create(api).get_json()
    item = body["items"][0]
    expected = _expected(api_app, item["item_id"])
    _answer(api, body["session_id"], item["item_id"], expected)

    db = api_app.extensions["db"]
    with db.session() as session:
        skills = {
            row.skill
            for row in session.scalars(
                select(SkillProgress).where(SkillProgress.word_id == item["word_id"])
            ).all()
        }
    assert skills == {"spelling"}, "只应写入 zh_to_en 对应的 spelling 进度"


# ─────────────────────────────────────────────────────────────
# 查询与结束
# ─────────────────────────────────────────────────────────────


def test_get_session_supports_resume(api):
    body = _create(api).get_json()
    resp = api.get(f"/api/v1/practice/sessions/{body['session_id']}")
    assert resp.status_code == 200
    resumed = resp.get_json()
    assert resumed["session_id"] == body["session_id"]
    assert len(resumed["items"]) == body["size"]


def test_get_session_include_answers(api, api_app):
    body = _create(api).get_json()
    item = body["items"][0]
    _answer(api, body["session_id"], item["item_id"], "zzz")

    detail = api.get(
        f"/api/v1/practice/sessions/{body['session_id']}?include_answers=true"
    ).get_json()
    assert detail["answers"][0]["correct"] is False
    assert detail["answers"][0]["user_answer"] == "zzz"


def test_get_missing_session_returns_404(api):
    assert api.get("/api/v1/practice/sessions/999999").status_code == 404


def test_finish_aggregates_and_is_idempotent(api, api_app):
    body = _create(api, size=5).get_json()
    session_id = body["session_id"]
    items = body["items"]

    _answer(api, session_id, items[0]["item_id"], _expected(api_app, items[0]["item_id"]))
    _answer(api, session_id, items[1]["item_id"], _expected(api_app, items[1]["item_id"]))
    _answer(api, session_id, items[2]["item_id"], "zzz")

    first = api.post(f"/api/v1/practice/sessions/{session_id}/finish", json={})
    assert first.status_code == 200
    summary = first.get_json()

    assert summary["status"] == "finished"
    assert summary["answered"] == 3
    assert summary["correct"] == 2
    assert summary["wrong"] == 1
    assert summary["answered"] == summary["correct"] + summary["wrong"]
    assert summary["accuracy"] == pytest.approx(2 / 3, rel=1e-3)
    assert summary["first_try_correct"] == 2
    assert len(summary["wrong_items"]) == 1
    assert summary["suggestions"], "结果页必须给一句可执行建议"

    second = api.post(f"/api/v1/practice/sessions/{session_id}/finish", json={})
    assert second.get_json() == summary, "重复结束必须返回同一份数字"


def test_answer_after_finish_returns_409(api):
    body = _create(api, size=5).get_json()
    session_id = body["session_id"]
    api.post(f"/api/v1/practice/sessions/{session_id}/finish", json={})

    resp = _answer(api, session_id, body["items"][0]["item_id"], "hello")
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "SESSION_FINISHED"


def test_expired_session_returns_409(api, api_app):
    body = _create(api, size=5).get_json()
    session_id = body["session_id"]

    db = api_app.extensions["db"]
    with db.session() as session:
        row = session.get(PracticeSession, session_id)
        row.started_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)

    resp = _answer(api, session_id, body["items"][0]["item_id"], "hello")
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


def test_finish_empty_session_reports_zero_not_error(api):
    """开了题一道没答就结束：数字全 0，但不能 500。"""
    body = _create(api, size=5).get_json()
    summary = api.post(
        f"/api/v1/practice/sessions/{body['session_id']}/finish", json={}
    ).get_json()
    assert summary["answered"] == 0
    assert summary["accuracy"] is None
    assert summary["wrong_items"] == []
