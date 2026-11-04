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
import os

from core.models import SkillProgress, Word
from core.queries import LOCAL_TZ
from core.vocabulary import derive_status, skill_to_mode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
# 音频扩展名：MVP 统一 mp3（见 docs/word-source-and-pronunciation-plan.md）
AUDIO_EXT = "mp3"


def iso(value: dt.datetime | None) -> str | None:
    """UTC -> 本地时区的 ISO 8601 字符串（带偏移量）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(LOCAL_TZ).isoformat(timespec="seconds")


def _audio_flags(word_id: int) -> dict[str, bool]:
    """音频是否已就绪。

    直接看文件在不在，而不是写一个全局开关 ——
    这样 B5 把音频灌进 data/audio 之后，接口会自动开始返回 true，
    不需要再回来改一行"记得把 false 改成 true"的代码。
    """
    base = os.path.join(AUDIO_DIR, str(word_id))
    return {
        accent: os.path.exists(os.path.join(base, f"{accent}.{AUDIO_EXT}"))
        for accent in ("uk", "us")
    }


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
        "audio": _audio_flags(word.id),
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
        "audio": _audio_flags(word.id),
        "progress_by_skill": by_skill,
    }
