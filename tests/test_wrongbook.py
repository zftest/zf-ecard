"""错词本核心口径测试（T5-1 ~ T5-3）。

这里守的不是"功能有没有"，而是**数字对不对**。错词本是全项目最容易
出现「列表说 9 条、角标说 11 条、结果页说新增 7 个」的地方，因为它的
数据源是一张既有列又有行的表，任何一处口径模糊，三方就会各算一套。

守的九条：
1. 同一技能下多个义项**合并成一行**，wrong_count 求和、box 取最小、
   到期时间取最早、主释义取「错的义项里顺序最前」的那个。
2. 同一单词的不同技能**分成多行** —— 「拼写会了、听音没会」是有用信息。
3. 只收 `wrong_count > 0` 且 `status = active` 的行。
4. `due_before` 只影响列表，不影响 summary 角标。
5. `due_today` 按**本地自然日**算，不是 UTC。
6. `mastered_this_week` 用 mastered_at 算，上周掌握的不计入本周。
7. `master` 后 next_review_at 为 None，且该词从列表消失。
8. `reset` 回第 1 盒并立刻到期，该词重新出现在列表。
9. 不在错词本里的 (词, 技能) 返回 None，由路由转 404，不静默成功。
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core import wrongbook
from core.models import SkillProgress, Word

# 固定"现在"：2026-11-06 12:00 UTC = 本地 20:00，周五。
# 用固定值而不是 now()，否则凌晨跑测试和中午跑会得到不同的 day_end。
NOW = dt.datetime(2026, 11, 6, 12, 0, tzinfo=dt.timezone.utc)
LOCAL_TZ = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")


def _utc(*args) -> dt.datetime:
    return dt.datetime(*args, tzinfo=dt.timezone.utc)


def _word_with_two_senses(db) -> tuple[int, list[int], str]:
    """从种子词库里找一个有多个义项的词（例如 class）。"""
    with db.session() as session:
        words = session.scalars(
            select(Word).options(selectinload(Word.senses)).order_by(Word.id)
        ).all()
        for word in words:
            if len(word.senses) >= 2:
                return word.id, [sense.id for sense in word.senses], word.spelling
    raise AssertionError("种子词库里没有多义词，测试前提不成立")


def _any_word(db) -> tuple[int, int]:
    with db.session() as session:
        word = session.scalars(
            select(Word).options(selectinload(Word.senses)).order_by(Word.id)
        ).first()
        return word.id, word.senses[0].id


def _any_two_words(db) -> list[tuple[int, int]]:
    with db.session() as session:
        words = session.scalars(
            select(Word).options(selectinload(Word.senses)).order_by(Word.id).limit(2)
        ).all()
        return [(word.id, word.senses[0].id) for word in words]


def _add(
    db,
    word_id: int,
    sense_id: int,
    skill: str = "spelling",
    *,
    box: int = 1,
    wrong: int = 1,
    correct: int = 0,
    status: str = "active",
    due_at: dt.datetime | None = None,
    last_seen: dt.datetime | None = None,
    last_result: str | None = None,
    mastered_at: dt.datetime | None = None,
) -> None:
    with db.session() as session:
        session.add(
            SkillProgress(
                learner_key="default",
                word_id=word_id,
                sense_id=sense_id,
                skill=skill,
                box_level=box,
                due_at=due_at or NOW,
                correct_count=correct,
                wrong_count=wrong,
                status=status,
                last_seen_at=last_seen,
                last_result=last_result,
                mastered_at=mastered_at,
            )
        )


# ─────────────────────────────────────────────────────────────
# 聚合口径
# ─────────────────────────────────────────────────────────────


def test_multi_sense_rows_merge_into_one_entry(seeded_db):
    """同一技能下两个义项都错了，列表只出一行。"""
    word_id, sense_ids, spelling = _word_with_two_senses(seeded_db)
    _add(seeded_db, word_id, sense_ids[0], box=2, wrong=3, due_at=_utc(2026, 11, 7))
    _add(seeded_db, word_id, sense_ids[1], box=1, wrong=2, due_at=_utc(2026, 11, 6, 10))

    with seeded_db.session() as session:
        entries, total, summary = wrongbook.list_entries(
            session, learner_key="default", now=NOW
        )

    assert total == 1, "同一技能下的多个义项必须合并成一行"
    assert summary["total"] == 1
    entry = entries[0]
    assert entry["form"] == spelling
    assert entry["wrong_count"] == 5, "错误次数要跨义项求和"
    assert entry["box"] == 1, "盒级取最小 —— 最弱的义项才代表真实掌握度"
    assert entry["due_at"] == _utc(2026, 11, 6, 10), "到期时间取最早的那个"
    assert entry["sense_count"] == 2


def test_multi_skill_splits_into_separate_entries(seeded_db):
    """同一个词，拼写错了、听音也错了，是两行 —— 弱项不同。"""
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, "spelling", wrong=1)
    _add(seeded_db, word_id, sense_id, "listening_spelling", wrong=2)

    with seeded_db.session() as session:
        entries, total, _ = wrongbook.list_entries(session, learner_key="default", now=NOW)

    assert total == 2
    skills = sorted(entry["skill"] for entry in entries)
    assert skills == ["listening_spelling", "spelling"]
    counts = {entry["skill"]: entry["wrong_count"] for entry in entries}
    assert counts["listening_spelling"] == 2
    assert counts["spelling"] == 1


def test_only_active_wrong_rows_are_listed(seeded_db):
    """已掌握 / 从没错过 / 被忽略的行都不进错词本。"""
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    _add(seeded_db, word_a, sense_a, wrong=1, status="mastered")
    _add(seeded_db, word_b, sense_b, wrong=0, status="active")

    with seeded_db.session() as session:
        entries, total, _ = wrongbook.list_entries(session, learner_key="default", now=NOW)

    assert total == 0
    assert entries == []


def test_primary_meaning_follows_wrong_sense_not_word_primary(seeded_db):
    """只错了第二个义项时，释义要显示**错的那个**，不是词的主义项。

    否则家长看到「environment 环境」会问「他明明环境会说，错哪了」，
    而实际错的是「自然环境」那个义项。
    """
    word_id, sense_ids, _ = _word_with_two_senses(seeded_db)
    _add(seeded_db, word_id, sense_ids[1], wrong=1)

    with seeded_db.session() as session:
        word = session.get(Word, word_id)
        secondary_meaning = word.senses[1].meaning_zh
        entries, _, _ = wrongbook.list_entries(session, learner_key="default", now=NOW)

    assert entries[0]["meaning_cn"] == secondary_meaning
    assert entries[0]["sense_count"] == 1


# ─────────────────────────────────────────────────────────────
# 排序
# ─────────────────────────────────────────────────────────────


def test_sort_due_puts_overdue_first(seeded_db):
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    _add(seeded_db, word_a, sense_a, due_at=_utc(2026, 11, 20))  # 还没到期
    _add(seeded_db, word_b, sense_b, due_at=_utc(2026, 11, 1))  # 已过期

    with seeded_db.session() as session:
        entries, _, _ = wrongbook.list_entries(
            session, learner_key="default", sort="due", now=NOW
        )

    assert entries[0]["word_id"] == word_b
    assert entries[0]["is_due"] is True
    assert entries[1]["is_due"] is False


def test_sort_wrong_count_desc(seeded_db):
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    _add(seeded_db, word_a, sense_a, wrong=1)
    _add(seeded_db, word_b, sense_b, wrong=7)

    with seeded_db.session() as session:
        entries, _, _ = wrongbook.list_entries(
            session, learner_key="default", sort="wrong_count", now=NOW
        )

    assert entries[0]["word_id"] == word_b
    assert entries[0]["wrong_count"] == 7


def test_sort_recent_puts_never_practiced_last(seeded_db):
    """从没练习过的排最后，而不是排最前（None 不能当 0 处理）。"""
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    _add(seeded_db, word_a, sense_a, last_seen=_utc(2026, 11, 5, 9), last_result="wrong")
    _add(seeded_db, word_b, sense_b, last_seen=None)

    with seeded_db.session() as session:
        entries, _, _ = wrongbook.list_entries(
            session, learner_key="default", sort="recent", now=NOW
        )

    assert entries[0]["word_id"] == word_a
    assert entries[1]["last_seen_at"] is None


# ─────────────────────────────────────────────────────────────
# summary 与筛选的边界
# ─────────────────────────────────────────────────────────────


def test_due_before_filters_list_but_not_summary(seeded_db):
    """筛「只看今天到期」之后，列表变短，但侧边栏角标不能跟着缩水。

    角标跟着筛选变，用户会以为自己弄丢了错词。
    """
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    _add(seeded_db, word_a, sense_a, due_at=_utc(2026, 11, 1))  # 早已到期
    _add(seeded_db, word_b, sense_b, due_at=_utc(2026, 12, 1))  # 下月才到期

    with seeded_db.session() as session:
        entries, total, summary = wrongbook.list_entries(
            session,
            learner_key="default",
            due_before=_utc(2026, 11, 7),
            now=NOW,
        )

    assert total == 1, "列表按时间窗过滤"
    assert summary["total"] == 2, "角标是全部，不受时间窗影响"


def test_summary_total_respects_skill_filter(seeded_db):
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, "spelling", wrong=1)
    _add(seeded_db, word_id, sense_id, "meaning_recall", wrong=1)

    with seeded_db.session() as session:
        _, total, summary = wrongbook.list_entries(
            session, learner_key="default", skill="spelling", now=NOW
        )

    assert total == 1
    assert summary["total"] == 1


def test_due_today_uses_local_calendar_day(seeded_db):
    """本地时间明天凌晨 0:30 到期的，算「今天到期」吗？不算。

    但本地今晚 23:30 到期的必须算今天 —— 若按 UTC 切天会漏掉它，
    于是晚上 8 点之后角标会莫名少一截。
    """
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    # 本地 2026-11-06 23:30 = UTC 15:30，在 day_end（本地 11-07 00:00）之前
    _add(seeded_db, word_a, sense_a, due_at=_utc(2026, 11, 6, 15, 30))
    # 本地 2026-11-07 00:30 = UTC 11-06 16:30，已经越过 day_end
    _add(seeded_db, word_b, sense_b, due_at=_utc(2026, 11, 6, 16, 30))

    with seeded_db.session() as session:
        _, _, summary = wrongbook.list_entries(session, learner_key="default", now=NOW)

    assert summary["due_today"] == 1


def test_mastered_this_week_excludes_last_week(seeded_db):
    (word_a, sense_a), (word_b, sense_b) = _any_two_words(seeded_db)
    # NOW 是本地 11-06（周五），本周一是本地 11-02
    _add(
        seeded_db, word_a, sense_a, wrong=1, status="mastered",
        mastered_at=_utc(2026, 11, 3),  # 本周
    )
    _add(
        seeded_db, word_b, sense_b, wrong=1, status="mastered",
        mastered_at=_utc(2026, 10, 28),  # 上周
    )

    with seeded_db.session() as session:
        _, _, summary = wrongbook.list_entries(session, learner_key="default", now=NOW)

    assert summary["mastered_this_week"] == 1


# ─────────────────────────────────────────────────────────────
# 手动改状态
# ─────────────────────────────────────────────────────────────


def test_master_removes_entry_and_clears_review_time(seeded_db):
    word_id, sense_ids, _ = _word_with_two_senses(seeded_db)
    _add(seeded_db, word_id, sense_ids[0], wrong=2, box=1)
    _add(seeded_db, word_id, sense_ids[1], wrong=1, box=2)

    with seeded_db.session() as session:
        result = wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="master", now=NOW,
        )

    assert result is not None
    assert result["status"] == "mastered"
    assert result["box"] == 5
    assert result["next_review_at"] is None, "已掌握的词没有下次复习时间"
    assert result["affected_senses"] == 2, "两个义项要一起改，否则列表里还剩一半"

    with seeded_db.session() as session:
        _, total, _ = wrongbook.list_entries(session, learner_key="default", now=NOW)
    assert total == 0, "标记已掌握后必须从错词本消失"


def test_reset_brings_mastered_word_back(seeded_db):
    """已掌握的词也能被重置回第 1 盒，重新出现在错词本里。

    这是「取消掌握」的唯一入口：错词本列表里看不到已掌握的词，
    但用户可能在某天发现「这个词他其实还是不会」。
    如果 reset 只允许操作 active 行，这种词就永远没有补救路径
    —— 它的 due_at 还在往后推，永远不会再被抽到。
    """
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, wrong=3, box=5, status="mastered",
         mastered_at=_utc(2026, 10, 1))

    with seeded_db.session() as session:
        result = wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="reset", now=NOW,
        )

    assert result is not None
    assert result["status"] == "active"
    assert result["box"] == 1
    assert result["next_review_at"] == NOW

    with seeded_db.session() as session:
        _, total, _ = wrongbook.list_entries(session, learner_key="default", now=NOW)
    assert total == 1, "取消掌握后必须重新出现在错词本里"


def test_master_twice_is_idempotent(seeded_db):
    """同一个「已掌握」按钮点两次：不报错、不再改库、返回同一状态。"""
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, wrong=1, box=1)

    with seeded_db.session() as session:
        first = wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="master", now=NOW,
        )
    assert first["affected_senses"] == 1

    with seeded_db.session() as session:
        second = wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="master", now=NOW,
        )
    assert second["status"] == "mastered"
    assert second["affected_senses"] == 0, "第二次没有可改的行"


def test_reset_active_entry_sets_box_one_and_due_now(seeded_db):
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, wrong=3, box=4, due_at=_utc(2026, 12, 1))

    with seeded_db.session() as session:
        result = wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="reset", now=NOW,
        )

    assert result["status"] == "active"
    assert result["box"] == 1
    assert result["next_review_at"] == NOW, "重置后立刻到期，下一轮就该练它"


def test_reset_keeps_historical_counts(seeded_db):
    """重置的是掌握度，不是历史事实。累计答对次数不该被清零。"""
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, wrong=2, correct=5, box=3)

    with seeded_db.session() as session:
        wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="reset", now=NOW,
        )

    with seeded_db.session() as session:
        row = session.scalar(select(SkillProgress))
        assert row.correct_count == 5
        assert row.wrong_count == 2


def test_update_missing_entry_returns_none(seeded_db):
    word_id, sense_id = _any_word(seeded_db)
    with seeded_db.session() as session:
        assert wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="spelling", action="master", now=NOW,
        ) is None


def test_update_wrong_skill_returns_none(seeded_db):
    """词在这个技能上错了，但请求改的是另一个技能 —— 必须 404，不能顺手改了。"""
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, "spelling", wrong=1)

    with seeded_db.session() as session:
        assert wrongbook.update_entry(
            session, learner_key="default", word_id=word_id,
            skill="meaning_recall", action="master", now=NOW,
        ) is None


# ─────────────────────────────────────────────────────────────
# 技能分离（T5-3）
# ─────────────────────────────────────────────────────────────


def test_skills_are_isolated_per_word(seeded_db):
    """汉译英答对了，听音写词仍然没有任何进度 —— 两个技能互不影响。

    这条如果坏了，表现是「听音写错一次，把看中文写对的进度也打回去」，
    而且从界面上完全看不出来是什么原因。
    """
    word_id, sense_id = _any_word(seeded_db)
    _add(seeded_db, word_id, sense_id, "spelling", box=5, wrong=0, correct=3,
         status="mastered", mastered_at=_utc(2026, 11, 5))

    with seeded_db.session() as session:
        rows = session.scalars(
            select(SkillProgress).where(SkillProgress.word_id == word_id)
        ).all()
        assert [row.skill for row in rows] == ["spelling"]

        # 听音写词这条技能上，该词是「从未练过」
        listening = session.scalar(
            select(SkillProgress).where(
                SkillProgress.word_id == word_id,
                SkillProgress.skill == "listening_spelling",
            )
        )
        assert listening is None

        # 错词本里也不该出现它（拼写已掌握、听音没练过）
        _, total, _ = wrongbook.list_entries(session, learner_key="default", now=NOW)
        assert total == 0
