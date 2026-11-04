"""/api/v1 接口契约测试。

这些测试守的不是"能返回 200"，而是几条**一改就静默出错**的约定：

1. 分页的 `total` 必须是去重后的词数。
   一旦有人把 EXISTS 改成 JOIN，`total` 会因为一个词多条义项而虚高，
   前端分页从第 2 页开始就会漏词 —— 页面看起来完全正常。
2. 列表里的 `progress` 允许为 null（新词还没学过）。
3. 错误一律是同一个 JSON 结构，包括"路径打错"这种路由级 404。
4. 500 不许把异常字符串返回出去。
5. `/api/v1` 的任何改动都不影响旧路由。
"""
from __future__ import annotations

import datetime as dt

import pytest

from core.models import SkillProgress, Word, WordSense


def _json(response) -> dict:
    return response.get_json()


# ─────────────────────────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────────────────────────


def test_health_reports_word_count(api):
    resp = api.get("/api/v1/health")
    assert resp.status_code == 200
    body = _json(resp)
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["words_count"] == 50
    assert body["server_time"].endswith("+08:00"), "时间必须带时区偏移"


def test_health_degrades_on_empty_library(api_app, db):
    """库能连但没词 -> degraded，让前端提示"先导入词库"而不是抽题时才报错。"""
    from core.db import Database

    empty = Database(str(db.path) + ".empty")
    empty.create_all()
    try:
        application = __import__("app").create_app({"DB_PATH": empty.path})
        client = application.test_client()
        body = _json(client.get("/api/v1/health"))
        assert body["database"] == "degraded"
        assert body["words_count"] == 0
    finally:
        empty.dispose()


# ─────────────────────────────────────────────────────────────
# 单元 / 主题
# ─────────────────────────────────────────────────────────────


def test_units_return_real_word_counts(api):
    """词数必须来自数据库，不是前端硬编码。

    原型阶段写死「Unit 3 · 20 词」而库里只有 13 条，出现胶囊与摘要打架。
    """
    body = _json(api.get("/api/v1/units"))
    items = {item["unit_code"] + item["term"]: item for item in body["items"]}
    assert len(body["items"]) == 18
    assert items["SU01上册"]["word_count"] == 10
    assert items["SU02上册"]["word_count"] == 16
    assert items["U02上册"]["word_count"] == 6
    # 还没录词的单元必须如实返回 0，不能藏起来
    assert items["U03上册"]["word_count"] == 0


def test_units_filter_by_book(api):
    body = _json(api.get("/api/v1/units?book=下册"))
    assert body["items"], "下册应至少有一个单元"
    assert all(item["term"] == "下册" for item in body["items"])


def test_themes_return_counts_and_exclude_null(api):
    body = _json(api.get("/api/v1/themes"))
    themes = {item["theme"]: item for item in body["items"]}
    assert themes["日常交际"]["word_count"] == 10
    assert None not in themes, "没有主题的词不应单独成一类"


# ─────────────────────────────────────────────────────────────
# 单词列表
# ─────────────────────────────────────────────────────────────


def test_words_pagination_total_is_distinct_words(api):
    """总数按词去重。用 JOIN 实现的话 'class' 有两个义项会被数两次。"""
    body = _json(api.get("/api/v1/words?page=1&page_size=20"))
    assert body["pagination"]["total"] == 50
    assert body["pagination"]["total_pages"] == 3
    assert len(body["items"]) == 20

    last = _json(api.get("/api/v1/words?page=3&page_size=20"))
    assert last["pagination"]["total"] == 50
    assert len(last["items"]) == 10


def test_words_pages_do_not_overlap(api):
    first = _json(api.get("/api/v1/words?page=1&page_size=10"))
    second = _json(api.get("/api/v1/words?page=2&page_size=10"))
    ids_first = {item["word_id"] for item in first["items"]}
    ids_second = {item["word_id"] for item in second["items"]}
    assert ids_first.isdisjoint(ids_second)


def test_words_search_by_spelling_and_meaning(api):
    by_form = _json(api.get("/api/v1/words?q=hello"))
    assert [item["form"] for item in by_form["items"]] == ["hello"]

    # 搜中文释义：孩子记得住"环境"但想不起拼写
    by_meaning = _json(api.get("/api/v1/words?q=爷爷"))
    assert by_meaning["pagination"]["total"] == 1
    assert by_meaning["items"][0]["form"] == "grandpa"


def test_words_search_wildcard_is_escaped(api):
    """搜 `%` 不能被当成通配符返回全表 —— 那是静默丢掉搜索条件。"""
    body = _json(api.get("/api/v1/words?q=%25"))
    assert body["pagination"]["total"] == 0


def test_words_filter_by_unit_and_theme(api):
    units = _json(api.get("/api/v1/units"))
    su01 = next(item for item in units["items"] if item["unit_code"] == "SU01"
                and item["term"] == "上册")

    by_unit = _json(api.get(f"/api/v1/words?unit={su01['unit_id']}"))
    assert by_unit["pagination"]["total"] == 10

    by_theme = _json(api.get("/api/v1/words?theme=颜色"))
    assert by_theme["pagination"]["total"] == 6


def test_words_filter_by_multiple_pos(api):
    body = _json(api.get("/api/v1/words?pos=int."))
    assert body["pagination"]["total"] > 0
    assert all(item["pos"] == "int." for item in body["items"])


def test_words_list_progress_is_null_when_never_practised(api):
    """没学过的词 progress 为 null。前端不处理就会白屏。"""
    body = _json(api.get("/api/v1/words?page_size=5"))
    assert all(item["progress"] is None for item in body["items"])


def test_words_include_multi_sense_count(api):
    body = _json(api.get("/api/v1/words?q=class"))
    item = body["items"][0]
    assert item["sense_count"] == 2


def test_words_sort_alpha(api):
    body = _json(api.get("/api/v1/words?sort=alpha&page_size=5"))
    forms = [item["form"] for item in body["items"]]
    assert forms == sorted(forms)


def test_words_sort_wrong_first_puts_wrong_words_on_top(seeded_db, api):
    """错得多的排前面。用相关子查询实现，不能因为 JOIN 把总数算错。"""
    with seeded_db.session() as session:
        word = session.query(Word).filter_by(spelling="hello").one()
        sense = session.query(WordSense).filter_by(word_id=word.id).one()
        session.add(
            SkillProgress(
                learner_key="default",
                word_id=word.id,
                sense_id=sense.id,
                skill="spelling",
                box_level=1,
                due_at=dt.datetime.now(dt.timezone.utc),
                wrong_count=9,
            )
        )

    body = _json(api.get("/api/v1/words?sort=wrong_first&page_size=3"))
    assert body["items"][0]["form"] == "hello"
    assert body["pagination"]["total"] == 50, "排序不应改变总数"


# ─────────────────────────────────────────────────────────────
# 掌握状态筛选（依赖 EXISTS，最容易写错的一块）
# ─────────────────────────────────────────────────────────────


def _add_progress(seeded_db, spelling: str, box: int, db_status: str = "active"):
    with seeded_db.session() as session:
        word = session.query(Word).filter_by(spelling=spelling).one()
        sense = session.query(WordSense).filter_by(word_id=word.id).one()
        session.add(
            SkillProgress(
                learner_key="default",
                word_id=word.id,
                sense_id=sense.id,
                skill="spelling",
                box_level=box,
                due_at=dt.datetime.now(dt.timezone.utc),
                status=db_status,
            )
        )


def test_status_new_excludes_words_with_progress(seeded_db, api):
    assert _json(api.get("/api/v1/words?status=new"))["pagination"]["total"] == 50

    _add_progress(seeded_db, "hello", box=2)

    body = _json(api.get("/api/v1/words?status=new"))
    assert body["pagination"]["total"] == 49
    assert "hello" not in [item["form"] for item in body["items"][:50]]


def test_status_learning_and_reviewing_split_by_box(seeded_db, api):
    _add_progress(seeded_db, "hello", box=2)  # learning
    _add_progress(seeded_db, "pen", box=4)  # reviewing

    learning = _json(api.get("/api/v1/words?status=learning"))
    reviewing = _json(api.get("/api/v1/words?status=reviewing"))

    assert [item["form"] for item in learning["items"]] == ["hello"]
    assert [item["form"] for item in reviewing["items"]] == ["pen"]


def test_status_mastered(seeded_db, api):
    _add_progress(seeded_db, "hello", box=5, db_status="mastered")

    body = _json(api.get("/api/v1/words?status=mastered"))
    assert [item["form"] for item in body["items"]] == ["hello"]
    assert body["items"][0]["progress"]["status"] == "mastered"


def test_status_filter_accepts_multiple_values(seeded_db, api):
    _add_progress(seeded_db, "hello", box=2)
    _add_progress(seeded_db, "pen", box=4)

    body = _json(api.get("/api/v1/words?status=learning,reviewing"))
    assert body["pagination"]["total"] == 2


def test_status_filter_is_scoped_to_requested_skill(seeded_db, api):
    """在 zh_to_en 下练过，不代表 audio_to_en 也算学过。"""
    _add_progress(seeded_db, "hello", box=2)  # skill = spelling

    by_spelling = _json(api.get("/api/v1/words?status=learning&skill=zh_to_en"))
    by_listening = _json(api.get("/api/v1/words?status=learning&skill=audio_to_en"))

    assert by_spelling["pagination"]["total"] == 1
    assert by_listening["pagination"]["total"] == 0


# ─────────────────────────────────────────────────────────────
# 单词详情
# ─────────────────────────────────────────────────────────────


def test_word_detail_returns_all_senses_with_accepted(api):
    listing = _json(api.get("/api/v1/words?q=grandpa"))
    word_id = listing["items"][0]["word_id"]

    detail = _json(api.get(f"/api/v1/words/{word_id}"))
    assert detail["form"] == "grandpa"
    assert detail["senses"][0]["meaning_cn"] == "爷爷"
    # accepted 是中文题判对判错的关键，必须完整返回
    assert detail["senses"][0]["accepted"] == ["祖父", "外公", "姥爷"]


def test_word_detail_multi_sense_ordered(api):
    listing = _json(api.get("/api/v1/words?q=class"))
    word_id = listing["items"][0]["word_id"]

    detail = _json(api.get(f"/api/v1/words/{word_id}"))
    assert [sense["meaning_cn"] for sense in detail["senses"]] == ["班级", "课"]
    assert [sense["sense_order"] for sense in detail["senses"]] == [1, 2]


def test_word_detail_404(api):
    resp = api.get("/api/v1/words/999999")
    assert resp.status_code == 404
    body = _json(resp)
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["request_id"] == resp.headers["X-Request-Id"]


# ─────────────────────────────────────────────────────────────
# 学习者与统计
# ─────────────────────────────────────────────────────────────


def test_learner_profile(api):
    body = _json(api.get("/api/v1/learners/default"))
    assert body["learner_id"] == "default"
    assert body["settings"]["daily_goal"] == 20
    # 从未练习 -> 没有"加入时间"，返回 null 而不是编一个当前时间
    assert body["created_at"] is None
    assert body["today"]["done"] == 0
    assert body["today"]["accuracy"] is None
    assert body["today"]["streak_days"] == 0
    assert body["totals"] == {
        "learning": 0,
        "reviewing": 0,
        "mastered": 0,
        "wrongbook": 0,
    }


def test_learner_unknown_id_is_404_not_silent_default(api):
    """拼错 ID 必须报错。静默当成 default 会让所有数据挂到同一个 key 上。"""
    resp = api.get("/api/v1/learners/typo")
    assert resp.status_code == 404
    assert "typo" in resp.get_json()["error"]["message"]


def test_stats_overview_shape(api):
    body = _json(api.get("/api/v1/learners/default/stats/overview?days=7"))
    assert len(body["trend"]) == 7
    assert all(entry["accuracy"] is None for entry in body["trend"])
    assert body["by_skill"] == []
    assert body["weak_themes"] == []


def test_stats_days_must_be_allowed_value(api):
    resp = api.get("/api/v1/learners/default/stats/overview?days=9")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_stats_counts_words_not_progress_rows(seeded_db, api):
    """一个词 2 义项 × 2 技能 = 4 行进度，但只能算 1 个词。"""
    with seeded_db.session() as session:
        word = session.query(Word).filter_by(spelling="class").one()
        senses = session.query(WordSense).filter_by(word_id=word.id).all()
        for sense in senses:
            for skill in ("spelling", "listening_spelling"):
                session.add(
                    SkillProgress(
                        learner_key="default",
                        word_id=word.id,
                        sense_id=sense.id,
                        skill=skill,
                        box_level=2,
                        due_at=dt.datetime.now(dt.timezone.utc),
                    )
                )

    body = _json(api.get("/api/v1/learners/default"))
    assert body["totals"]["learning"] == 1, "应按 word_id 去重"
    assert body["totals"]["mastered"] == 0


# ─────────────────────────────────────────────────────────────
# 统一错误结构与请求追踪
# ─────────────────────────────────────────────────────────────


def test_validation_error_has_details(api):
    resp = api.get("/api/v1/words?page_size=999")
    assert resp.status_code == 400
    body = _json(resp)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "page_size"


def test_unknown_enum_gets_chinese_message(api):
    resp = api.get("/api/v1/words?skill=bad")
    detail = _json(resp)["error"]["details"][0]
    assert detail["field"] == "skill"
    assert "取值必须是" in detail["message"]


def test_routing_404_is_json_not_html(api):
    """路径打错也必须是统一 JSON。

    路由阶段的 404 发生在"知道属于哪个蓝图"之前，
    只用蓝图错误处理会漏掉，前端于是收到 HTML，response.json() 直接抛错。
    """
    resp = api.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert resp.is_json
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_method_not_allowed_is_json(api):
    resp = api.post("/api/v1/words")
    assert resp.status_code == 405
    assert resp.is_json
    assert resp.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_request_id_is_generated_and_echoed(api):
    resp = api.get("/api/v1/health")
    request_id = resp.headers["X-Request-Id"]
    assert len(request_id) == 8


def test_request_id_from_client_is_preserved(api):
    resp = api.get("/api/v1/health", headers={"X-Request-Id": "my-trace-001"})
    assert resp.headers["X-Request-Id"] == "my-trace-001"


def test_request_id_appears_in_error_body(api):
    resp = api.get("/api/v1/words/999999")
    assert resp.get_json()["request_id"] == resp.headers["X-Request-Id"]


def test_internal_error_does_not_leak_exception(api, monkeypatch):
    """500 只回固定文案。异常字符串里常带文件路径、SQL、甚至密钥片段。"""
    import core.queries as queries

    def _boom(session):  # noqa: ANN001
        raise RuntimeError("secret-detail-should-not-leak")

    monkeypatch.setattr(queries, "count_words", _boom)

    resp = api.get("/api/v1/health")
    assert resp.status_code == 500
    body = resp.get_json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "服务器内部错误"
    assert "secret-detail-should-not-leak" not in resp.get_data(as_text=True)


# ─────────────────────────────────────────────────────────────
# 与旧路由的隔离
# ─────────────────────────────────────────────────────────────


def test_legacy_404_still_returns_html(api):
    """旧页面的 404 必须保持 HTML，且不带 X-Request-Id。"""
    resp = api.get("/poster/not-a-real-id")
    assert resp.status_code == 404
    assert not resp.is_json
    assert "X-Request-Id" not in resp.headers


def test_legacy_index_still_renders(api):
    resp = api.get("/")
    assert resp.status_code == 200
    assert not resp.is_json
    assert "X-Request-Id" not in resp.headers
