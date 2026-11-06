"""练习会话的生命周期：抽题 → 判题 → 落进度 → 收尾。

它属于 core 层（不 import flask），因为这里面每一条规则都会被
「练习页」「结果页」「错词本」「统计」四个地方同时依赖，
一旦写得含糊，四个页面的数字就会各说一套。

四个刻意的取舍：

1. **一道题只记一次进度。**
   同一题重复提交会覆盖作答记录（以最后一次为准），但**不再动盒子与错词计数**。
   否则孩子反复试到对为止，盒子会被刷到第 5 盒，错词本也永远是空的。

2. **`first_try_correct` 只在第一次提交时确定。**
   它的意思是"第一遍独立答对"，重试答对不能改写这个事实，
   否则首答正确率会变成"最终正确率"，指标就失去意义了。

3. **会话没有 `expires_at` 列，过期时间由 `started_at + 2h` 现算。**
   存一列就要多一个写入点和一次迁移，而它是纯派生值 ——
   派生值存库，迟早出现「表里写 10:00 过期、代码按 12:00 算」的分歧。

4. **作答即写进度，不在收尾时批量补写。**
   中途关掉页面（真实使用里非常常见）不该丢掉已经答过的题。
"""
from __future__ import annotations

import datetime as dt
import math
import random

from sqlalchemy import and_, select

from core import grading, selection
from core.audio import has_any_audio
from core.models import Book, PracticeItem, PracticeSession, SkillProgress, Unit, Word, WordSense
from core.srs import is_mastered, schedule
from core.vocabulary import mode_to_skill

DEFAULT_LEARNER = "default"

# 会话有效期。2 小时足够写完 20 题，又不至于让"昨天的会话"今早还能续
SESSION_TTL = dt.timedelta(hours=2)

STATUS_RUNNING = "running"
STATUS_FINISHED = "finished"
STATUS_EXPIRED = "expired"

# 听音题在没有音频文件时照样能出题，但必须给前端一个明确的降级信号
WARNING_POOL_INSUFFICIENT = "POOL_INSUFFICIENT"
WARNING_AUDIO_UNAVAILABLE = "AUDIO_UNAVAILABLE"


def _now(now: dt.datetime | None = None) -> dt.datetime:
    if now is None:
        return dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(dt.timezone.utc)


def expires_at(session_row: PracticeSession) -> dt.datetime:
    """会话到期时间（派生值，不落库）。"""
    started = session_row.started_at or _now()
    if started.tzinfo is None:
        started = started.replace(tzinfo=dt.timezone.utc)
    return started + SESSION_TTL


def session_state(session_row: PracticeSession, now: dt.datetime | None = None) -> str:
    """running / finished / expired。

    先判 finished 再判过期：已结束的会话不该因为放了两小时就变成"过期"，
    否则结果页刷新一次就提示"请重新开始"，而成绩明明还在。
    """
    if session_row.status == STATUS_FINISHED:
        return STATUS_FINISHED
    if _now(now) >= expires_at(session_row):
        return STATUS_EXPIRED
    return STATUS_RUNNING


# ─────────────────────────────────────────────────────────────
# 抽题
# ─────────────────────────────────────────────────────────────


def candidate_senses(
    db,
    *,
    learner_key: str,
    skill: str,
    range_type: str,
    range_value: str | None,
) -> list[dict]:
    """候选池：一个**义项**是一道题。

    为什么不以"词"为单位：
        「class」的「班级」和「课堂」是两个义项，错词本必须分开记。
        按词抽题会让同一拼写出现两次相同题干，孩子会以为程序坏了。
    """
    stmt = (
        select(
            Word.id.label("word_id"),
            Word.spelling,
            Word.phonetic_uk,
            Word.phonetic_us,
            Word.theme,
            WordSense.id.label("sense_id"),
            WordSense.sense_order,
            WordSense.meaning_zh,
            WordSense.accepted,
            SkillProgress.box_level,
            SkillProgress.wrong_count,
            SkillProgress.status.label("progress_status"),
            Unit.sort_order,
            Unit.unit_name,
            Book.id.label("book_id"),
        )
        .join(WordSense, WordSense.word_id == Word.id)
        .outerjoin(
            SkillProgress,
            and_(
                SkillProgress.word_id == Word.id,
                SkillProgress.sense_id == WordSense.id,
                SkillProgress.learner_key == learner_key,
                SkillProgress.skill == skill,
            ),
        )
        .outerjoin(Unit, Unit.id == Word.unit_id)
        .outerjoin(Book, Book.id == Unit.book_id)
    )

    if range_type == "unit":
        stmt = stmt.where(Word.unit_id == int(range_value or 0))
    elif range_type == "theme":
        stmt = stmt.where(Word.theme == range_value)
    elif range_type == "wrongbook":
        # 错词本 = 有错且没被家长手动忽略
        stmt = stmt.where(
            SkillProgress.wrong_count > 0,
            SkillProgress.status == "active",
        )
    # all：不加范围条件

    rows = db.execute(stmt).all()
    return [
        {
            "word_id": row.word_id,
            "spelling": row.spelling,
            "phonetic_uk": row.phonetic_uk,
            "phonetic_us": row.phonetic_us,
            "theme": row.theme,
            "sense_id": row.sense_id,
            "sense_order": row.sense_order,
            "meaning_zh": row.meaning_zh,
            "accepted": list(row.accepted or []),
            "box": row.box_level,
            "wrong_count": row.wrong_count or 0,
            "progress_status": row.progress_status,
            "unit_name": row.unit_name,
            "order_key": (
                row.book_id or 0,
                row.sort_order or 0,
                row.word_id,
                row.sense_order or 0,
            ),
        }
        for row in rows
    ]


def _collapse_by_word(rows: list[dict]) -> list[dict]:
    """英译汉按词合并义项。

    题干是英文单词，一个词出两次一模一样的题没有意义；
    而判题要接受该词的**任意一个**义项，否则孩子答"课堂"会被判错。
    """
    grouped: dict[int, dict] = {}
    for row in rows:
        primary = grouped.get(row["word_id"])
        if primary is None:
            grouped[row["word_id"]] = {**row, "sibling_meanings": [], "sibling_accepted": []}
            continue
        primary["sibling_meanings"].append(row["meaning_zh"])
        primary["sibling_accepted"].extend(row["accepted"])
        primary["sibling_accepted"].append(row["meaning_zh"])
    return list(grouped.values())


def build_question(mode: str, row: dict) -> tuple[str, str, list[str]]:
    """按题型生成 (题干, 标准答案, 额外可接受写法)。"""
    if mode == "zh_to_en":
        return row["meaning_zh"], row["spelling"], []
    if mode == "audio_to_en":
        # 题干为空：前端只能靠音频。词形绝不能下发，否则等于直接给答案
        return "", row["spelling"], []
    if mode == "phonetic_to_en":
        return "", row["spelling"], []
    if mode == "en_to_zh":
        accepted = list(row.get("sibling_accepted") or []) + list(row.get("sibling_meanings") or [])
        return row["spelling"], row["meaning_zh"], accepted
    raise ValueError(f"未知题型：{mode}")


def create_session(
    db,
    *,
    learner_key: str,
    mode: str,
    range_type: str,
    range_value: str | None,
    size: int,
    order: str = "random",
    hint_enabled: bool = True,
    rng: random.Random | None = None,
) -> tuple[PracticeSession, list[dict]]:
    """建会话并落题。返回 (会话, warnings)。

    池子不足**不是错误**：用户选了 50 题但单元里只有 18 个词，
    这时出 18 题并明确告知，比返回 409 让他自己数词数要好。
    真正需要拦的是池子为空 —— 那样连一道题都出不来。
    """
    skill = mode_to_skill(mode)
    pool = candidate_senses(
        db,
        learner_key=learner_key,
        skill=skill,
        range_type=range_type,
        range_value=range_value,
    )
    if mode == "en_to_zh":
        pool = _collapse_by_word(pool)

    chosen, insufficient = selection.pick(pool, size, order, rng)

    session_row = PracticeSession(
        learner_key=learner_key,
        mode=mode,
        range_type=range_type,
        range_value=range_value,
        size=len(chosen),
        order_strategy=order,
        hint_enabled=hint_enabled,
        status=STATUS_RUNNING,
    )
    db.add(session_row)
    db.flush()  # 需要 session_row.id 才能挂子项

    for seq, row in enumerate(chosen, start=1):
        prompt, expected, accepted = build_question(mode, row)
        db.add(
            PracticeItem(
                session_id=session_row.id,
                seq=seq,
                word_id=row["word_id"],
                sense_id=row["sense_id"],
                mode=mode,
                prompt_snapshot=prompt,
                expected_snapshot=expected,
                accepted_snapshot=accepted,
            )
        )

    warnings: list[dict] = []
    if insufficient:
        warnings.append(
            {
                "code": WARNING_POOL_INSUFFICIENT,
                # 题池按"义项"计，一个词有 2 个释义就是 2 道题，
                # 所以这里说"道题"而不是"个词"，否则会和单元列表的词数对不上
                "message": f"该范围只有 {len(pool)} 道可出的题，已按 {len(pool)} 题出题",
            }
        )
    if mode == "audio_to_en" and not _any_audio(chosen):
        warnings.append(
            {
                "code": WARNING_AUDIO_UNAVAILABLE,
                "message": "音频还没生成，这一轮先用设备语音代替（音色不是真人）",
            }
        )

    db.flush()
    return session_row, warnings


def _any_audio(rows: list[dict]) -> bool:
    """抽到的题里是否有任何一个词存在音频文件。

    直接看文件而不是查配置：B6 把 mp3 灌进 data/audio 之后，
    这里会自动从"降级"变成"正常"，不需要回来改代码。
    """
    return any(has_any_audio(row["word_id"]) for row in rows)


# ─────────────────────────────────────────────────────────────
# 判题与进度
# ─────────────────────────────────────────────────────────────


def submit_answer(
    db,
    *,
    session_row: PracticeSession,
    item: PracticeItem,
    answer: str,
    hint_used: bool = False,
    elapsed_ms: int | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """判一道题并落库。返回响应所需的全部数据（不含 item_id）。"""
    moment = _now(now)
    lang = grading.ZH_LANG if item.mode == "en_to_zh" else grading.EN_LANG
    first_submission = (item.attempts or 0) == 0

    result = grading.grade(
        answer,
        item.expected_snapshot,
        lang=lang,
        accepted=list(item.accepted_snapshot or []),
        hint_used=hint_used,
    )

    item.user_answer = (answer or "")[:200]
    item.normalized_answer = result.normalized_input
    item.is_correct = result.correct
    # 用累计值：这一题只要用过一次提示，就不再算独立答对
    item.hint_used = bool(item.hint_used or hint_used)
    if first_submission:
        item.first_try_correct = result.correct and not item.hint_used
    item.attempts = (item.attempts or 0) + 1
    if elapsed_ms is not None:
        item.duration_ms = elapsed_ms
    item.answered_at = moment

    progress_updated = None
    if first_submission:
        progress_updated = _apply_progress(
            db, session_row.learner_key, item, correct=result.correct,
            hint_used=item.hint_used, moment=moment,
        )

    db.flush()

    return {
        "result": result,
        "progress_updated": progress_updated,
        "session_progress": session_progress(session_row),
    }


def _apply_progress(
    db,
    learner_key: str,
    item: PracticeItem,
    *,
    correct: bool,
    hint_used: bool,
    moment: dt.datetime,
) -> dict:
    """把一次作答折算成盒子升降，并写回 skill_progress。"""
    skill = mode_to_skill(item.mode)
    row = db.scalar(
        select(SkillProgress).where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.word_id == item.word_id,
            SkillProgress.sense_id == item.sense_id,
            SkillProgress.skill == skill,
        )
    )
    box_before = row.box_level if row else None

    if row is None:
        row = SkillProgress(
            learner_key=learner_key,
            word_id=item.word_id,
            sense_id=item.sense_id,
            skill=skill,
            box_level=1,
            due_at=moment,
            correct_count=0,
            wrong_count=0,
            status="active",
        )
        db.add(row)

    decision = schedule(box_before, correct, hint_used, now=moment)

    row.box_level = decision.box_level
    row.due_at = decision.due_at
    row.last_seen_at = moment
    row.last_result = "correct" if correct else "wrong"
    row.correct_count = (row.correct_count or 0) + (1 if correct else 0)
    row.wrong_count = (row.wrong_count or 0) + (0 if correct else 1)
    # 已掌握 = 到第 5 盒且独立答对够 3 次；错一次就退回 active（SRS 已经把它打回第 1 盒）
    new_status = "mastered" if is_mastered(row.box_level, row.correct_count) else "active"
    if new_status == "mastered" and row.status != "mastered":
        # 只在「刚刚变成已掌握」时记时间；一直是 mastered 的不刷新，
        # 否则连续答对会把 mastered_at 一路推后，「本周掌握」就永远只统计最近几天
        row.mastered_at = moment
    elif new_status != "mastered":
        # 答错退回 active：这一列必须跟着清空，否则「本周掌握」会把
        # 已经被打回重练的词继续算成掌握
        row.mastered_at = None
    row.status = new_status

    return {
        "skill": item.mode,
        "box_before": box_before,
        "box_after": row.box_level,
        "next_review_at": row.due_at,
        "reason": decision.reason,
    }


def session_progress(session_row: PracticeSession) -> dict:
    """会话内已答/对/错。按题去重 —— 重复提交不重复计数。"""
    answered = [item for item in session_row.items if item.answered_at is not None]
    correct = sum(1 for item in answered if item.is_correct)
    return {
        "answered": len(answered),
        "correct": correct,
        "wrong": len(answered) - correct,
    }


# ─────────────────────────────────────────────────────────────
# 收尾
# ─────────────────────────────────────────────────────────────


def finish_session(
    db, session_row: PracticeSession, now: dt.datetime | None = None
) -> dict:
    """汇总本次成绩。幂等：重复调用不会重复写库、数字不变。

    错词本不是单独一张表（见 core/models.py 的说明），它由
    skill_progress 派生，所以在作答时就已经"写进"错词本了。
    这里只做统计，不再补写 —— 重复调用因此天然幂等。
    """
    moment = _now(now)
    items = list(session_row.items)
    answered = [item for item in items if item.answered_at is not None]
    correct_items = [item for item in answered if item.is_correct]
    wrong_items = [item for item in answered if not item.is_correct]

    if session_row.status != STATUS_FINISHED:
        session_row.status = STATUS_FINISHED
        session_row.finished_at = moment

    answered_count = len(answered)
    correct_count = len(correct_items)
    first_try = sum(1 for item in answered if item.first_try_correct)
    hint_count = sum(1 for item in answered if item.hint_used)

    elapsed = [
        item.duration_ms for item in answered if item.duration_ms is not None
    ]
    if session_row.finished_at and session_row.started_at:
        duration_ms = int(
            (session_row.finished_at - session_row.started_at).total_seconds() * 1000
        )
    else:  # pragma: no cover - finished_at 刚被赋值，走不到
        duration_ms = None

    words = load_words(db, [item.word_id for item in items])
    details = []
    for item in wrong_items:
        word = words.get(item.word_id)
        progress = _find_progress(db, session_row.learner_key, item)
        details.append(
            {
                "item_id": item.id,
                "word_id": item.word_id,
                "form": word.spelling if word else "",
                "meaning_cn": item.expected_snapshot if item.mode == "en_to_zh" else (
                    item.prompt_snapshot or ""
                ),
                "user_answer": item.user_answer,
                "expected": item.expected_snapshot,
                "near_miss": _near_miss(item),
                "next_review_at": progress.due_at if progress else None,
            }
        )

    wrongbook_added = sum(
        1
        for detail in details
        if _is_first_wrong(db, session_row.learner_key, detail["word_id"])
    )

    next_due = [detail["next_review_at"] for detail in details if detail["next_review_at"]]
    return {
        "session_id": session_row.id,
        "mode": session_row.mode,
        "status": session_row.status,
        "size": session_row.size,
        "answered": answered_count,
        "correct": correct_count,
        "wrong": answered_count - correct_count,
        "accuracy": round(correct_count / answered_count, 4) if answered_count else None,
        "first_try_correct": first_try,
        "first_try_accuracy": (
            round(first_try / answered_count, 4) if answered_count else None
        ),
        "hint_used_count": hint_count,
        "duration_ms": duration_ms,
        "avg_elapsed_ms": round(sum(elapsed) / len(elapsed)) if elapsed else None,
        "wrong_items": details,
        "wrongbook_added": wrongbook_added,
        "next_review_at": min(next_due) if next_due else None,
        "suggestions": _suggestions(details, words, answered_count, correct_count),
    }


def _near_miss(item: PracticeItem) -> bool:
    """结果页不给 diff，只用 distance 复核一次"很接近"。"""
    if item.mode == "en_to_zh":
        return False
    return grading.grade(
        item.user_answer, item.expected_snapshot,
        accepted=list(item.accepted_snapshot or []),
    ).near_miss


def _find_progress(db, learner_key: str, item: PracticeItem):
    return db.scalar(
        select(SkillProgress).where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.word_id == item.word_id,
            SkillProgress.sense_id == item.sense_id,
            SkillProgress.skill == mode_to_skill(item.mode),
        )
    )


def _is_first_wrong(db, learner_key: str, word_id: int) -> bool:
    """该词是否本次才进错词本（累计只错过这一次）。

    错词本没有单独的表，无法直接判断"新增"，只能由累计次数反推：
    错 1 次的词就是这批新进来的。这个口径写在这里而不是散在调用方，
    否则将来换一种判法会出现"结果页说新增 9 个、错词本只有 7 个"。
    """
    total = db.scalar(
        select(SkillProgress.wrong_count).where(
            SkillProgress.learner_key == learner_key,
            SkillProgress.word_id == word_id,
        )
    )
    return (total or 0) == 1


def load_words(db, word_ids: list[int]) -> dict[int, Word]:
    """批量取词，避免逐题查一次（一页 20 题就是 20 条 SQL）。"""
    ids = {wid for wid in word_ids if wid}
    if not ids:
        return {}
    rows = db.scalars(select(Word).where(Word.id.in_(ids))).all()
    return {word.id: word for word in rows}


def _suggestions(
    details: list[dict], words: dict[int, Word], answered: int, correct: int
) -> list[str]:
    """规则生成的中文建议。不用 AI：它慢、会变，而且这里根本不需要发挥。"""
    if answered == 0:
        return ["这一轮没有作答记录，下次答完记得点结束"]
    if not details:
        return ["全部答对。下次可以把题量增加到 30 个，或者换听音题试试"]

    unit_counter: dict[str, int] = {}
    for detail in details:
        word = words.get(detail["word_id"])
        unit_name = word.unit.unit_name if word and word.unit else None
        if unit_name:
            unit_counter[unit_name] = unit_counter.get(unit_name, 0) + 1

    tips: list[str] = []
    wrong_words = len({detail["word_id"] for detail in details})
    tips.append(
        f"明天先复习这 {wrong_words} 个错词，预计 {max(3, math.ceil(wrong_words * 0.5))} 分钟"
    )

    if unit_counter:
        unit_name, count = max(unit_counter.items(), key=lambda pair: pair[1])
        if count >= 3 and count * 2 >= len(details):
            tips.append(f"错词集中在 {unit_name}，共 {count} 个，可以整单元再默一遍")

    return tips
