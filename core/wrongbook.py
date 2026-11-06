"""错词本：`skill_progress` 的查询视图，不是第 8 张表。

单独立一个模块而不是塞进 queries.py，是因为这里有三条**极易写错**的口径，
必须集中在一处并写明理由，否则「列表 9 条、角标 11 条、结果页新增 7 个」
这种三方对不上的账迟早出现：

1. **聚合粒度是 (word_id, skill)，不是进度行。**
   一个词 2 个义项 × 1 个技能 = 2 行进度，但错词本列表若按行展示，
   同一个单词会连着出现两次，两次的「错 N 次」还各不相同。
   孩子看到会以为是程序坏了。所以必须合并成一行。

   合并规则（每条都有代价，选的是不容易骗人的那个）：
       wrong_count  求和   —— 这个词这个技能一共错了几次，这是事实累加
       box          取最小 —— 最弱的义项代表真实掌握度。取最大会显示
                              「快毕业了」，而某个义项其实一次都没会过
       due_at       取最早 —— 最早到期的那个才决定「现在该不该复习」
       status       全 mastered 才算 —— 只要还有一个义项在练，就是没掌握

2. **「已掌握」不显示复习时间。**
   `due_at` 是 NOT NULL 列，标成已掌握后它仍然留在库里（不影响任何查询，
   错词本已排除 mastered）。但接口返回 `next_review_at: null` ——
   已掌握的词没有"下次复习"，返回一个时间会让前端画出一个毫无意义的提醒。

3. **summary 是角标，不受 `due_before` 影响。**
   `due_before` 是翻页浏览用的时间窗。如果角标也跟着它变，
   用户一筛"只看今天到期"，侧边栏的「错词 9 个」立刻变成「6 个」，
   他会以为自己弄丢了词。所以角标只跟随 `skill` 这一维筛选。

为什么聚合在 Python 里做而不是写 SQL：
    规则是"取最小 / 取最早 / 全部满足"，用窗口函数也能写，
    但可读性会差到下一次改动没人敢动。错词本规模是几十到上千行，
    全取回来聚合的开销远小于写错一次统计口径的代价。
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from core.models import Book, SkillProgress, Unit, Word, WordSense
from core.queries import LOCAL_TZ
from core.vocabulary import ACTION_MASTER, ACTION_RESET, MASTER_BOX, WRONGBOOK_SORTS

__all__ = [
    "WRONGBOOK_SORTS",
    "WRONGBOOK_ACTIONS",
    "list_entries",
    "update_entry",
]

WRONGBOOK_ACTIONS: tuple[str, ...] = (ACTION_MASTER, ACTION_RESET)


def _now(now: dt.datetime | None = None) -> dt.datetime:
    if now is None:
        return dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(dt.timezone.utc)


def _local_day_end(moment: dt.datetime) -> dt.datetime:
    """「今天结束」对应的时刻，按本地自然日算。

    必须按本地时区切天：库里存 UTC，若直接拿 UTC 日期算，
    晚上 8 点之后被判到期的词会被算进"明天"，角标当天就少一截。
    """
    local_date = moment.astimezone(LOCAL_TZ).date()
    tomorrow = local_date + dt.timedelta(days=1)
    return dt.datetime.combine(tomorrow, dt.time.min, tzinfo=LOCAL_TZ)


def _local_week_start(moment: dt.datetime) -> dt.datetime:
    """本周一 00:00（本地）。周一算一周的第一天，符合国内习惯。"""
    local_date = moment.astimezone(LOCAL_TZ).date()
    monday = local_date - dt.timedelta(days=local_date.weekday())
    return dt.datetime.combine(monday, dt.time.min, tzinfo=LOCAL_TZ)


def _load_rows(db, learner_key: str, skill: str | None):
    """取错词本原始行：错过且有错、并且没被标成已掌握/忽略。"""
    stmt = (
        select(SkillProgress, Word, WordSense, Unit, Book)
        .join(Word, Word.id == SkillProgress.word_id)
        .join(WordSense, WordSense.id == SkillProgress.sense_id)
        .outerjoin(Unit, Unit.id == Word.unit_id)
        .outerjoin(Book, Book.id == Unit.book_id)
        .where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.wrong_count > 0,
            SkillProgress.status == "active",
        )
    )
    if skill:
        stmt = stmt.where(SkillProgress.skill == skill)
    return db.execute(stmt).all()


def _aggregate(rows) -> dict[tuple[int, str], dict]:
    """把进度行按 (word_id, skill) 合并成错词本条目。"""
    grouped: dict[tuple[int, str], dict] = {}

    for progress, word, sense, unit, book in rows:
        key = (word.id, progress.skill)
        entry = grouped.get(key)
        if entry is None:
            grouped[key] = {
                "word_id": word.id,
                "form": word.spelling,
                "phonetic_uk": word.phonetic_uk,
                "phonetic_us": word.phonetic_us,
                "pos": word.pos,
                "unit_id": word.unit_id,
                "unit_code": unit.unit_code if unit else None,
                "unit_name": unit.unit_name if unit else None,
                "book": book.title if book else None,
                "theme": word.theme,
                "skill": progress.skill,
                "wrong_count": progress.wrong_count or 0,
                "box": progress.box_level,
                "due_at": progress.due_at,
                "last_seen_at": progress.last_seen_at,
                "last_wrong_at": (
                    progress.last_seen_at if progress.last_result == "wrong" else None
                ),
                # 记下涉及到的义项，用于挑主释义与统计"几个意思都错"
                "_senses": [(sense.sense_order, sense.id, sense.meaning_zh)],
            }
            continue

        entry["wrong_count"] += progress.wrong_count or 0
        entry["box"] = min(entry["box"], progress.box_level)
        entry["due_at"] = min(entry["due_at"], progress.due_at)
        entry["_senses"].append((sense.sense_order, sense.id, sense.meaning_zh))

        if progress.last_seen_at is not None:
            if entry["last_seen_at"] is None or progress.last_seen_at > entry["last_seen_at"]:
                entry["last_seen_at"] = progress.last_seen_at
        if progress.last_result == "wrong" and progress.last_seen_at is not None:
            if entry["last_wrong_at"] is None or progress.last_seen_at > entry["last_wrong_at"]:
                entry["last_wrong_at"] = progress.last_seen_at

    # 主释义取"错的义项里 sense_order 最小的那个"，而不是词的主义项 ——
    # 只错了第二个义项时，展示主义的释义会让人对不上自己错的是哪个意思
    for entry in grouped.values():
        senses = sorted(entry.pop("_senses"), key=lambda item: item[0])
        entry["meaning_cn"] = senses[0][2]
        entry["sense_count"] = len(senses)
        entry["sense_ids"] = [item[1] for item in senses]

    return grouped


def _sort_key(sort: str, moment: dt.datetime):
    if sort == "wrong_count":
        return lambda entry: (-entry["wrong_count"], entry["due_at"], entry["word_id"])
    if sort == "recent":
        # 从没练习过的排最后，而不是排最前（None 不能直接参与比较）
        return lambda entry: (
            entry["last_seen_at"] is None,
            -(entry["last_seen_at"] or moment).timestamp(),
            entry["word_id"],
        )
    # due：已到期的排前面，其次按到期时间由早到晚
    return lambda entry: (not entry["is_due"], entry["due_at"], entry["word_id"])


def list_entries(
    db,
    *,
    learner_key: str,
    skill: str | None = None,
    due_before: dt.datetime | None = None,
    sort: str = "due",
    page: int = 1,
    page_size: int = 20,
    now: dt.datetime | None = None,
) -> tuple[list[dict], int, dict]:
    """错词本列表。返回 (当页条目, 筛选后总数, 全局角标摘要)。"""
    moment = _now(now)
    grouped = _aggregate(_load_rows(db, learner_key, skill))

    for entry in grouped.values():
        entry["is_due"] = entry["due_at"] <= moment

    # 角标：只受 skill 影响，不受 due_before / 分页影响（见模块注释第 3 条）
    summary = _summary(db, learner_key, skill, grouped, moment)

    entries = list(grouped.values())
    if due_before is not None:
        entries = [entry for entry in entries if entry["due_at"] <= due_before]

    total = len(entries)
    entries.sort(key=_sort_key(sort, moment))

    start = (page - 1) * page_size
    return entries[start : start + page_size], total, summary


def _summary(db, learner_key: str, skill: str | None, grouped: dict, moment: dt.datetime) -> dict:
    day_end = _local_day_end(moment)
    week_start = _local_week_start(moment)

    due_today = sum(1 for entry in grouped.values() if entry["due_at"] <= day_end)

    # 本周掌握：按 (word, skill) 去重，和 total 同一个口径。
    # mastered_at 为 NULL 的行（0002 迁移之前就掌握的词）不计入任何一周。
    stmt = (
        select(SkillProgress.word_id, SkillProgress.skill)
        .where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.status == "mastered",
            SkillProgress.mastered_at.is_not(None),
            SkillProgress.mastered_at >= week_start,
        )
        .distinct()
    )
    if skill:
        stmt = stmt.where(SkillProgress.skill == skill)
    mastered_this_week = len(db.execute(stmt).all())

    return {
        "total": len(grouped),
        "due_today": due_today,
        "mastered_this_week": mastered_this_week,
    }


def update_entry(
    db,
    *,
    learner_key: str,
    word_id: int,
    skill: str,
    action: str,
    now: dt.datetime | None = None,
) -> dict | None:
    """把某个 (词, 技能) 标成已掌握，或重置回第 1 盒。

    返回 None 表示「这个词在这个技能上从来没有过错」，由路由层转成 404。

    动的是该 (词, 技能) 下的**全部义项**，不是单条进度行 ——
    因为错词本列表是按 (词, 技能) 聚合展示的，只改其中一个义项会出现
    「点了已掌握，列表里这个单词还在」的自相矛盾。

    `reset` 对**已掌握**的词也生效，语义是「取消掌握、拉回来重练」：
    错词本列表里当然看不到已掌握的词，但用户可能在结果页或词库页
    发现「这个词我其实不会」，此时他需要一个入口。只允许重置 active
    行的话，这种词就只能等它自己到复习期，而它永远不会到期。
    """
    moment = _now(now)

    rows = list(
        db.scalars(
            select(SkillProgress).where(
                SkillProgress.learner_key == learner_key,
                SkillProgress.word_id == word_id,
                SkillProgress.skill == skill,
                SkillProgress.wrong_count > 0,
            )
        ).all()
    )
    if not rows:
        return None

    if action == ACTION_MASTER:
        # 已经掌握的不再重复写，但也不报错 —— 同一个按钮点两次不该 404
        targets = [row for row in rows if row.status != "mastered"]
    else:  # ACTION_RESET
        targets = rows

    for row in targets:
        if action == ACTION_MASTER:
            row.status = "mastered"
            row.box_level = MASTER_BOX
            row.mastered_at = moment
            # due_at 保持原值不动：已掌握的词不再看这个字段，
            # presenters 会直接返回 null。把它清零反而是伪造数据。
        else:
            row.status = "active"
            row.box_level = 1
            row.due_at = moment  # 立刻到期，下一轮就该练它
            row.mastered_at = None
            # 累计正确/错误次数不动：那是历史事实，重置的是掌握度不是事实

    db.flush()

    status = "mastered" if action == ACTION_MASTER else "active"
    return {
        "word_id": word_id,
        "skill": skill,
        "status": status,
        "box": min(row.box_level for row in rows) if action == ACTION_MASTER else 1,
        "next_review_at": moment if action == ACTION_RESET else None,
        "updated_at": moment,
        "affected_senses": len(targets),
    }
