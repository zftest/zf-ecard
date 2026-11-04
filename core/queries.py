"""查询层：只做数据访问与聚合，不依赖 Flask、不感知 HTTP。

为什么单独一层：
    控制器要处理参数、状态码、序列化，这些和「怎么查库」是两件事。
    混在一起以后，任何一次 SQL 调整都得连带改接口逻辑，而且没法单独测查询。

几个刻意的实现选择：

1. **状态筛选用 EXISTS 子查询，不用 JOIN。**
   JOIN 会让一个词因为多条进度行而重复出现，`.count()` 出来的总数偏大，
   分页总页数跟着错。EXISTS 保证「一个词一行」。

2. **列表页的进度分两次查，不在 SQL 里拼 JSON。**
   先取一页词（≤100 行），再一次性捞出这批词的进度，
   这是 2 条 SQL 而不是 N+1 条。

3. **今日/趋势按本地时区切天**，不是按 UTC。
   库里存 UTC 是对的，但「今天练了多少」必须按用户所在时区的自然日算，
   否则晚上 8 点之后练的会被算到"明天"。
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from core.models import Book, PracticeItem, PracticeSession, SkillProgress, Unit, Word, WordSense
from core.vocabulary import REVIEWING_BOX, Skill, derive_status, mode_to_skill

# 用户所在时区。库里一律 UTC，展示与"按天"统计按这个时区折算。
LOCAL_TZ = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")

# 弱项主题的最少样本数：练了 1 次全错不该排到第一名
WEAK_THEME_MIN_SAMPLE = 20


def _like(expr, keyword: str):
    """转义 LIKE 通配符。

    用户搜 "100%" 时，不转义会把 % 当成通配符，搜出全部词 —— 看起来"能用"，
    实际是把搜索条件悄悄丢掉了。
    """
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return expr.ilike(f"%{escaped}%", escape="\\")


def _progress_exists(learner_key: str, skill: str, *conditions):
    """构造「该词存在一条符合条件的学习进度」的 EXISTS 条件。"""
    return (
        select(SkillProgress.id)
        .where(
            SkillProgress.word_id == Word.id,
            SkillProgress.learner_key == learner_key,
            SkillProgress.skill == skill,
            *conditions,
        )
        .exists()
    )


# ─────────────────────────────────────────────────────────────
# 词库维度
# ─────────────────────────────────────────────────────────────


def count_words(session) -> int:
    return session.scalar(select(func.count(Word.id))) or 0


def unit_word_counts(session) -> dict[int, int]:
    """{unit_id: 实际词数}。

    这个数字必须由数据算，不能写在前端 ——
    原型阶段写死「Unit 3 · 20 词」而库里只有 13 条，出现过胶囊与摘要自相矛盾。
    """
    rows = session.execute(
        select(Word.unit_id, func.count(Word.id)).group_by(Word.unit_id)
    ).all()
    return {unit_id: count for unit_id, count in rows if unit_id is not None}


def unit_mastered_counts(session, learner_key: str) -> dict[int, int]:
    """{unit_id: 已掌握词数}。按词去重 —— 一个词有多个义项 × 技能，不能重复计。"""
    rows = session.execute(
        select(Word.unit_id, func.count(func.distinct(Word.id)))
        .join(SkillProgress, SkillProgress.word_id == Word.id)
        .where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.status == "mastered",
        )
        .group_by(Word.unit_id)
    ).all()
    return {unit_id: count for unit_id, count in rows if unit_id is not None}


def unit_wrong_counts(session, learner_key: str) -> dict[int, int]:
    """{unit_id: 错词数}。错词本 = 有错且未被忽略的词。"""
    rows = session.execute(
        select(Word.unit_id, func.count(func.distinct(Word.id)))
        .join(SkillProgress, SkillProgress.word_id == Word.id)
        .where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.wrong_count > 0,
            SkillProgress.status == "active",
        )
        .group_by(Word.unit_id)
    ).all()
    return {unit_id: count for unit_id, count in rows if unit_id is not None}


def list_units(session, learner_key: str, book: str | None = None) -> list[dict]:
    """单元列表，带真实词数与掌握数。"""
    query = (
        select(Unit, Book)
        .join(Book, Book.id == Unit.book_id)
        .order_by(Book.id, Unit.sort_order)
    )
    if book:
        # 支持按册次过滤：「七年级上册」或「人教版 2024 七年级上册」都行
        query = query.where(Book.title.like(f"%{book}%"))

    word_counts = unit_word_counts(session)
    mastered = unit_mastered_counts(session, learner_key)
    wrong = unit_wrong_counts(session, learner_key)

    items = []
    for unit, book_row in session.execute(query).all():
        items.append(
            {
                "unit_id": unit.id,
                "unit_code": unit.unit_code,
                "unit_name": unit.unit_name,
                "unit_no": unit.unit_no,
                "is_starter": unit.is_starter,
                "book": book_row.title,
                "book_id": book_row.id,
                "term": book_row.term,
                "word_count": word_counts.get(unit.id, 0),
                "mastered_count": mastered.get(unit.id, 0),
                "wrong_count": wrong.get(unit.id, 0),
            }
        )
    return items


def list_themes(session, learner_key: str) -> list[dict]:
    """主题列表，带真实词数与掌握数。没有主题的词不计入。"""
    rows = session.execute(
        select(Word.theme, func.count(Word.id))
        .where(Word.theme.is_not(None), Word.theme != "")
        .group_by(Word.theme)
        .order_by(func.count(Word.id).desc(), Word.theme)
    ).all()

    mastered_rows = session.execute(
        select(Word.theme, func.count(func.distinct(Word.id)))
        .join(SkillProgress, SkillProgress.word_id == Word.id)
        .where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.status == "mastered",
            Word.theme.is_not(None),
        )
        .group_by(Word.theme)
    ).all()
    mastered = {theme: count for theme, count in mastered_rows}

    return [
        {
            "theme": theme,
            "word_count": count,
            "mastered_count": mastered.get(theme, 0),
        }
        for theme, count in rows
    ]


def _status_condition(learner_key: str, skill: str, status: str):
    """把对外的四态折算成 SQL 条件。

    `new` 是「没有进度行」，必须用 NOT EXISTS；
    其余三态按盒级 + 状态推导，和 derive_status 保持同一套规则。
    """
    if status == "new":
        return ~_progress_exists(learner_key, skill)
    if status == "mastered":
        return _progress_exists(learner_key, skill, SkillProgress.status == "mastered")
    if status == "reviewing":
        return _progress_exists(
            learner_key,
            skill,
            SkillProgress.status != "mastered",
            SkillProgress.box_level >= REVIEWING_BOX,
        )
    # learning
    return _progress_exists(
        learner_key,
        skill,
        SkillProgress.status != "mastered",
        SkillProgress.box_level < REVIEWING_BOX,
    )


def _wrong_count_expr(learner_key: str, skill: str):
    """该词在该技能下的累计错误次数（跨全部义项求和）。用于 wrong_first 排序。"""
    return (
        select(func.coalesce(func.sum(SkillProgress.wrong_count), 0))
        .where(
            SkillProgress.word_id == Word.id,
            SkillProgress.learner_key == learner_key,
            SkillProgress.skill == skill,
        )
        .correlate(Word)
        .scalar_subquery()
    )


def list_words(
    session,
    *,
    learner_key: str,
    skill: str,
    q: str | None = None,
    unit_id: int | None = None,
    theme: str | None = None,
    pos: list[str] | None = None,
    statuses: list[str] | None = None,
    sort: str = "unit",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Word], int]:
    """单词列表（带筛选、排序、分页）。返回 (当页词, 总数)。"""
    query: Select = select(Word)

    if q:
        # 同时搜词形和中文释义：孩子记得住"环境"但想不起 environment 是拼什么
        query = query.where(
            or_(
                _like(Word.spelling, q),
                Word.senses.any(_like(WordSense.meaning_zh, q)),
            )
        )
    if unit_id is not None:
        query = query.where(Word.unit_id == unit_id)
    if theme:
        query = query.where(Word.theme == theme)
    if pos:
        query = query.where(Word.pos.in_(pos))
    if statuses:
        query = query.where(
            or_(*[_status_condition(learner_key, skill, s) for s in statuses])
        )

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0

    if sort == "alpha":
        query = query.order_by(Word.spelling)
    elif sort == "wrong_first":
        query = query.order_by(_wrong_count_expr(learner_key, skill).desc(), Word.id)
    elif sort == "recent":
        query = query.order_by(Word.created_at.desc(), Word.id.desc())
    else:  # unit：先按册、再按单元顺序、最后按录入顺序
        query = query.outerjoin(Unit, Unit.id == Word.unit_id).order_by(
            Unit.book_id, Unit.sort_order, Word.id
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(
        selectinload(Word.senses),
        joinedload(Word.unit).joinedload(Unit.book),
    )
    words = list(session.scalars(query).all())
    return words, total


def get_word(session, word_id: int) -> Word | None:
    return session.scalar(
        select(Word)
        .where(Word.id == word_id)
        .options(
            selectinload(Word.senses),
            joinedload(Word.unit).joinedload(Unit.book),
        )
    )


def progress_for_words(
    session, learner_key: str, skill: str, word_ids: list[int]
) -> dict[int, list[SkillProgress]]:
    """批量取一批词的进度（一条 SQL），避免列表页 N+1。"""
    if not word_ids:
        return {}
    rows = session.scalars(
        select(SkillProgress)
        .where(
            SkillProgress.word_id.in_(word_ids),
            SkillProgress.learner_key == learner_key,
            SkillProgress.skill == skill,
        )
        .order_by(SkillProgress.sense_id, SkillProgress.skill)
    ).all()

    grouped: dict[int, list[SkillProgress]] = {}
    for row in rows:
        grouped.setdefault(row.word_id, []).append(row)
    return grouped


def progress_by_skill(session, learner_key: str, word_id: int) -> list[SkillProgress]:
    """某个词在所有技能上的进度，给词条详情用。"""
    return list(
        session.scalars(
            select(SkillProgress)
            .where(
                SkillProgress.word_id == word_id,
                SkillProgress.learner_key == learner_key,
            )
            .order_by(SkillProgress.skill, SkillProgress.sense_id)
        ).all()
    )


# ─────────────────────────────────────────────────────────────
# 学习统计
# ─────────────────────────────────────────────────────────────


def _local_day_start(day: dt.date) -> dt.datetime:
    """本地某天 00:00 对应的 UTC 时刻。"""
    return dt.datetime.combine(day, dt.time.min, tzinfo=LOCAL_TZ).astimezone(dt.timezone.utc)


def status_totals(session, learner_key: str) -> dict[str, int]:
    """按词去重统计 学习中 / 复习中 / 已掌握 / 错词本。

    「一个词」的口径是 word_id，不是进度行 ——
    一个词有 2 个义项 × 4 个技能最多 8 行，按行数统计会虚高 8 倍。
    """
    learning: set[int] = set()
    reviewing: set[int] = set()
    mastered: set[int] = set()
    for word_id, db_status, box in session.execute(
        select(SkillProgress.word_id, SkillProgress.status, SkillProgress.box_level).where(
            SkillProgress.learner_key == learner_key
        )
    ).all():
        state = derive_status(box, db_status)
        if state == "mastered":
            mastered.add(word_id)
        elif state == "reviewing":
            reviewing.add(word_id)
        else:
            learning.add(word_id)

    wrong = session.scalar(
        select(func.count(func.distinct(SkillProgress.word_id))).where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.wrong_count > 0,
            SkillProgress.status == "active",
        )
    )
    return {
        "learning": len(learning - mastered - reviewing),
        "reviewing": len(reviewing - mastered),
        "mastered": len(mastered),
        "wrongbook": wrong or 0,
    }


def today_summary(session, learner_key: str, daily_goal: int = 20) -> dict:
    """今日已作答数、正确率、连续天数。"""
    today = dt.datetime.now(LOCAL_TZ).date()
    start = _local_day_start(today)

    rows = session.execute(
        select(PracticeItem.is_correct, PracticeItem.first_try_correct)
        .join(PracticeSession, PracticeSession.id == PracticeItem.session_id)
        .where(
            PracticeSession.learner_key == learner_key,
            PracticeItem.answered_at.is_not(None),
            PracticeItem.answered_at >= start,
        )
    ).all()

    answered = len(rows)
    correct = sum(1 for is_correct, _ in rows if is_correct)
    accuracy = round(correct / answered, 4) if answered else None

    return {
        "date": today.isoformat(),
        "goal": daily_goal,
        "done": answered,
        "accuracy": accuracy,
        "streak_days": streak_days(session, learner_key, today),
    }


def _answered_dates(session, learner_key: str) -> set[dt.date]:
    rows = session.scalars(
        select(PracticeItem.answered_at)
        .join(PracticeSession, PracticeSession.id == PracticeItem.session_id)
        .where(
            PracticeSession.learner_key == learner_key,
            PracticeItem.answered_at.is_not(None),
        )
    ).all()
    # 库里是 UTC，按本地时区折算成自然日
    return {ts.astimezone(LOCAL_TZ).date() for ts in rows if ts is not None}


def streak_days(session, learner_key: str, today: dt.date | None = None) -> int:
    """连续练习天数。

    今天还没练不算断 —— 否则早上打开首页会看到「连续 0 天」，
    而昨天明明练过。从今天或昨天往前数，遇到空档就停。
    """
    today = today or dt.datetime.now(LOCAL_TZ).date()
    days = _answered_dates(session, learner_key)
    if not days:
        return 0

    cursor = today if today in days else today - dt.timedelta(days=1)
    if cursor not in days:
        return 0

    count = 0
    while cursor in days:
        count += 1
        cursor -= dt.timedelta(days=1)
    return count


def trend(session, learner_key: str, days: int = 7) -> list[dict]:
    """近 N 天趋势。没练的那天 accuracy 为 None，前端要断线而不是画成 0。"""
    today = dt.datetime.now(LOCAL_TZ).date()
    first_day = today - dt.timedelta(days=days - 1)
    start = _local_day_start(first_day)

    rows = session.execute(
        select(PracticeItem.answered_at, PracticeItem.is_correct)
        .join(PracticeSession, PracticeSession.id == PracticeItem.session_id)
        .where(
            PracticeSession.learner_key == learner_key,
            PracticeItem.answered_at.is_not(None),
            PracticeItem.answered_at >= start,
        )
    ).all()

    buckets: dict[dt.date, list[bool]] = {}
    for answered_at, is_correct in rows:
        day = answered_at.astimezone(LOCAL_TZ).date()
        buckets.setdefault(day, []).append(bool(is_correct))

    result = []
    for offset in range(days):
        day = first_day + dt.timedelta(days=offset)
        answers = buckets.get(day, [])
        result.append(
            {
                "date": day.isoformat(),
                "answered": len(answers),
                "accuracy": round(sum(answers) / len(answers), 4) if answers else None,
            }
        )
    return result


def stats_by_skill(session, learner_key: str) -> list[dict]:
    """按技能维度统计掌握分布与正确率。

    必须分技能：会写不等于听得懂，合并成一个总分会让听音写词的成绩
    永远被拼写成绩掩盖。
    """
    rows = session.execute(
        select(
            SkillProgress.skill,
            SkillProgress.status,
            SkillProgress.box_level,
            SkillProgress.word_id,
            SkillProgress.correct_count,
            SkillProgress.wrong_count,
        ).where(SkillProgress.learner_key == learner_key)
    ).all()

    buckets: dict[str, dict] = {}
    for skill, db_status, box, word_id, correct, wrong in rows:
        bucket = buckets.setdefault(
            skill,
            {"learning": set(), "reviewing": set(), "mastered": set(), "correct": 0, "wrong": 0},
        )
        state = derive_status(box, db_status)
        bucket[state].add(word_id)
        bucket["correct"] += correct or 0
        bucket["wrong"] += wrong or 0

    result = []
    for skill, bucket in buckets.items():
        total_answers = bucket["correct"] + bucket["wrong"]
        result.append(
            {
                "skill": skill,
                "learning": len(bucket["learning"] - bucket["mastered"] - bucket["reviewing"]),
                "reviewing": len(bucket["reviewing"] - bucket["mastered"]),
                "mastered": len(bucket["mastered"]),
                "accuracy": (
                    round(bucket["correct"] / total_answers, 4) if total_answers else None
                ),
            }
        )
    result.sort(key=lambda item: item["skill"])
    return result


def weak_themes(
    session, learner_key: str, min_sample: int = WEAK_THEME_MIN_SAMPLE
) -> list[dict]:
    """正确率最低的主题。样本太少的主题不参与排名。"""
    rows = session.execute(
        select(
            Word.theme,
            PracticeItem.is_correct,
        )
        .join(Word, Word.id == PracticeItem.word_id)
        .join(PracticeSession, PracticeSession.id == PracticeItem.session_id)
        .where(
            PracticeSession.learner_key == learner_key,
            PracticeItem.is_correct.is_not(None),
            Word.theme.is_not(None),
        )
    ).all()

    buckets: dict[str, list[bool]] = {}
    for theme, is_correct in rows:
        buckets.setdefault(theme, []).append(bool(is_correct))

    ranked = []
    for theme, answers in buckets.items():
        if len(answers) < min_sample:
            continue
        ranked.append(
            {
                "theme": theme,
                "accuracy": round(sum(answers) / len(answers), 4),
                "sampled": len(answers),
            }
        )
    ranked.sort(key=lambda item: (item["accuracy"], -item["sampled"]))
    return ranked


def first_activity_at(session, learner_key: str) -> dt.datetime | None:
    """该 learner 最早一次作答时间，用来当「加入时间」。

    MVP 没有 learners 表（单人使用，引入了就要做登录），
    所以 created_at 只能由最早的活动时间推算；从未练习过则为 None。
    """
    return session.scalar(
        select(func.min(PracticeItem.answered_at))
        .join(PracticeSession, PracticeSession.id == PracticeItem.session_id)
        .where(PracticeSession.learner_key == learner_key)
    )
