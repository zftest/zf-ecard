"""把 ORM 对象转成 API 响应结构。

单独一层的理由：同一个 Word 在「列表」和「详情」里字段不一样
（列表给主释义，详情给全部义项 + 逐技能进度）。如果让路由自己拼 dict，
两处写法迟早会不一致，前端就要为同一个词写两套解析。

时间统一按本地时区输出并带偏移量（`+08:00`）：
   库里存 UTC 是对的，但接口返回裸时间或 UTC 都会被前端误解成"本地时间"，
   于是"下次复习"显示成凌晨 4 点。带偏移量就消灭了这种歧义。
"""
from __future__ import annotations

import datetime as dt

from core.audio import audio_flags
from core.grading import make_hint
from core.models import PracticeItem, PracticeSession, SkillProgress, Word
from core.practice import expires_at, session_progress, session_state
from core.queries import LOCAL_TZ
from core.vocabulary import derive_status, skill_to_mode

# 需要孩子写英文的题型：只有这几种才给"首字母 + 下划线"的提示
EN_OUTPUT_MODES = ("zh_to_en", "audio_to_en", "phonetic_to_en")


def iso(value: dt.datetime | None) -> str | None:
    """UTC -> 本地时区的 ISO 8601 字符串（带偏移量）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(LOCAL_TZ).isoformat(timespec="seconds")


def present_pagination(page: int, page_size: int, total: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def present_progress(progress: SkillProgress) -> dict:
    return {
        "skill": skill_to_mode(progress.skill),
        "box": progress.box_level,
        "status": derive_status(progress.box_level, progress.status),
        "correct_count": progress.correct_count,
        "wrong_count": progress.wrong_count,
        "next_review_at": iso(progress.due_at),
    }


def _pick_progress(word: Word, progresses: list[SkillProgress]) -> SkillProgress | None:
    """列表里一个词只显示一条进度，优先取主义项（sense_order 最小）的那条。"""
    if not progresses:
        return None
    primary = word.senses[0].id if word.senses else None
    for progress in progresses:
        if progress.sense_id == primary:
            return progress
    return progresses[0]


def present_word_brief(word: Word, progresses: list[SkillProgress]) -> dict:
    """单词列表项：主释义 + 一条进度，够列表展示，不含例句。"""
    primary_sense = word.senses[0] if word.senses else None
    progress = _pick_progress(word, progresses)
    unit = word.unit

    return {
        "word_id": word.id,
        "form": word.spelling,
        "phonetic_uk": word.phonetic_uk,
        "phonetic_us": word.phonetic_us,
        "pos": word.pos,
        "unit_id": word.unit_id,
        "unit_code": unit.unit_code if unit else None,
        "unit_name": unit.unit_name if unit else None,
        "book": unit.book.title if unit and unit.book else None,
        "theme": word.theme,
        "meaning_cn": primary_sense.meaning_zh if primary_sense else None,
        "sense_count": len(word.senses),
        "audio": audio_flags(word.id),
        "progress": present_progress(progress) if progress else None,
    }


def present_word_detail(word: Word, progresses: list[SkillProgress]) -> dict:
    """单词详情：全部义项 + 逐技能进度。"""
    unit = word.unit
    by_skill = [present_progress(progress) for progress in progresses]

    return {
        "word_id": word.id,
        "form": word.spelling,
        "phonetic_uk": word.phonetic_uk,
        "phonetic_us": word.phonetic_us,
        "pos": word.pos,
        "unit_id": word.unit_id,
        "unit_code": unit.unit_code if unit else None,
        "unit_name": unit.unit_name if unit else None,
        "book": unit.book.title if unit and unit.book else None,
        "theme": word.theme,
        "source": word.source,
        "source_license": word.source_license,
        "verify_status": word.verify_status,
        "senses": [
            {
                "sense_id": sense.id,
                "sense_order": sense.sense_order,
                "meaning_cn": sense.meaning_zh,
                "accepted": sense.accepted or [],
                "example_en": sense.example_en,
                "example_cn": sense.example_zh,
            }
            for sense in word.senses
        ],
        "audio": audio_flags(word.id),
        "progress_by_skill": by_skill,
    }


# ─────────────────────────────────────────────────────────────
# 练习会话与判题
# ─────────────────────────────────────────────────────────────


def present_item(item: PracticeItem, words: dict[int, Word], hint_enabled: bool) -> dict:
    """一道题的对外结构。

    `prompt` 与 `phonetic` 是**互斥**的：听音题/音标题不能带词形，
    否则打开 devtools 就能看到答案。这不是防作弊，是防止"手滑把答案渲染出来"。
    """
    word = words.get(item.word_id)
    prompt: str | None = None
    phonetic: str | None = None
    available = False

    if item.mode in ("zh_to_en", "en_to_zh"):
        prompt = item.prompt_snapshot
    elif item.mode == "phonetic_to_en":
        phonetic = (word.phonetic_uk or word.phonetic_us) if word else None
    elif item.mode == "audio_to_en":
        available = audio_flags(item.word_id)["uk"] or audio_flags(item.word_id)["us"]

    hint = None
    if hint_enabled and item.mode in EN_OUTPUT_MODES:
        hint = make_hint(item.expected_snapshot)

    payload = {
        "item_id": item.id,
        "index": item.seq,
        "word_id": item.word_id,
        "sense_id": item.sense_id,
        "prompt": prompt,
        "phonetic": phonetic,
        "audio_available": available,
        "hint": hint,
        "answered": item.answered_at is not None,
    }

    # 只有英译汉可以回传词形 —— 它的题干本来就是词形。
    # 汉译英/听音写词/音标写词一旦带上 form，等于把答案直接放进响应里。
    if item.mode == "en_to_zh":
        payload["form"] = word.spelling if word else None
    return payload


def present_session(
    session_row: PracticeSession,
    items: list[PracticeItem],
    words: dict[int, Word],
    *,
    warnings: list[dict] | None = None,
    include_answers: bool = False,
) -> dict:
    """会话主体。`status` 用现算的三态，不是库里的两态。"""
    payload = {
        "session_id": session_row.id,
        "learner_id": session_row.learner_key,
        "mode": session_row.mode,
        "range": session_row.range_type,
        "range_value": session_row.range_value,
        "order": session_row.order_strategy,
        "hint_enabled": session_row.hint_enabled,
        "size": session_row.size,
        "status": session_state(session_row),
        "started_at": iso(session_row.started_at),
        "created_at": iso(session_row.started_at),
        "expires_at": iso(expires_at(session_row)),
        "progress": session_progress(session_row),
        "items": [
            present_item(item, words, session_row.hint_enabled) for item in items
        ],
    }
    if include_answers:
        payload["answers"] = [
            {
                "item_id": item.id,
                "user_answer": item.user_answer,
                "expected": item.expected_snapshot,
                "correct": item.is_correct,
                "first_try_correct": item.first_try_correct,
                "hint_used": item.hint_used,
                "answered_at": iso(item.answered_at),
            }
            for item in items
            if item.answered_at is not None
        ]
    if warnings:
        payload["warnings"] = warnings
    return payload


def present_grade(item: PracticeItem, payload: dict) -> dict:
    """判题响应。字段顺序与文档一致，前端可照抄。"""
    result = payload["result"]
    return {
        "item_id": item.id,
        "correct": result.correct,
        "near_miss": result.near_miss,
        "distance": result.distance,
        "expected": result.expected,
        "normalized_input": result.normalized_input,
        "diff": result.diff,
        "hint_used": item.hint_used,
        "first_try_correct": bool(item.first_try_correct),
        "feedback": result.feedback,
        "progress_updated": _present_progress_updated(payload["progress_updated"]),
        "session_progress": payload["session_progress"],
        "answered_at": iso(item.answered_at),
    }


def _present_progress_updated(updated: dict | None) -> dict | None:
    if updated is None:
        # 重复提交同一题：不再动盒子和错词计数，但要让前端知道"没白提交"
        return None
    return {
        "skill": updated["skill"],
        "box_before": updated["box_before"],
        "box_after": updated["box_after"],
        "next_review_at": iso(updated["next_review_at"]),
        "reason": updated["reason"],
    }


def present_finish(summary: dict) -> dict:
    """结果页数据。时间字段统一转 ISO。"""
    payload = dict(summary)
    payload["next_review_at"] = iso(summary.get("next_review_at"))
    payload["wrong_items"] = [
        {**item, "next_review_at": iso(item.get("next_review_at"))}
        for item in summary.get("wrong_items", [])
    ]
    return payload


# ─────────────────────────────────────────────────────────────
# 错词本
# ─────────────────────────────────────────────────────────────


def present_wrongbook_entry(entry: dict) -> dict:
    """错词本一行。

    一个单词可能出现在**多行** —— 因为它在不同技能上都错过
    （拼写写错、听音也没听出来）。这是故意的：
    合并成一行会让「错 3 次」变成各技能之和，掩盖真正的弱项。
    行内用 `skill` 区分，前端按技能分组展示即可。

    同一技能下的多个义项则已经合并（见 core/wrongbook.py 的聚合规则），
    所以「class 的『班级』和『课堂』都错了」只占一行，用 `sense_count` 体现。
    """
    return {
        "word_id": entry["word_id"],
        "form": entry["form"],
        "phonetic_uk": entry["phonetic_uk"],
        "phonetic_us": entry["phonetic_us"],
        "pos": entry["pos"],
        "meaning_cn": entry["meaning_cn"],
        "sense_count": entry["sense_count"],
        "unit_id": entry["unit_id"],
        "unit_code": entry["unit_code"],
        "unit_name": entry["unit_name"],
        "book": entry["book"],
        "theme": entry["theme"],
        "skill": skill_to_mode(entry["skill"]),
        "box": entry["box"],
        "wrong_count": entry["wrong_count"],
        # 错词本里的行一定是 active（查询已排除 mastered），
        # 所以四态只可能是 learning / reviewing
        "status": derive_status(entry["box"], "active"),
        "next_review_at": iso(entry["due_at"]),
        "is_due": entry["is_due"],
        "last_wrong_at": iso(entry["last_wrong_at"]),
        "audio": audio_flags(entry["word_id"]),
    }


def present_wrongbook_update(result: dict) -> dict:
    """手动操作的结果。`master` 之后 `next_review_at` 必须是 null。"""
    db_status = result["status"]
    return {
        "word_id": result["word_id"],
        "skill": skill_to_mode(result["skill"]),
        "status": (
            "mastered" if db_status == "mastered" else derive_status(result["box"], db_status)
        ),
        "box": result["box"],
        "next_review_at": iso(result["next_review_at"]),
        "updated_at": iso(result["updated_at"]),
        "affected_senses": result["affected_senses"],
    }

