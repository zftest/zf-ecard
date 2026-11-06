"""枚举字典、题型与技能的换算、掌握状态推导。

这里集中解决一个容易埋雷的口径问题：

    API 对外说「题型」      zh_to_en / audio_to_en / en_to_zh / phonetic_to_en
    数据库存的是「技能」    spelling / listening_spelling / meaning_recall / phonetic_spelling

两者不等价。题型是「这一次怎么练」，技能是「练的是哪一种能力」。
将来同一个技能可能有好几个题型入口（spelling 既能由汉译英练，也能由看图写词练），
所以进度表必须按技能记；而前端下拉框是让用户选题型。
换算只发生在这一层，其他任何地方都不该硬编码这两套字符串。
"""
from __future__ import annotations

from typing import Literal

# 题型（API 层词汇，也等于 practice_sessions.mode / practice_items.mode）
Mode = Literal["zh_to_en", "audio_to_en", "en_to_zh", "phonetic_to_en"]
MODES: tuple[str, ...] = ("zh_to_en", "audio_to_en", "en_to_zh", "phonetic_to_en")

# 技能（数据库 skill_progress.skill 词汇）
Skill = Literal["spelling", "listening_spelling", "meaning_recall", "phonetic_spelling"]

MODE_TO_SKILL: dict[str, str] = {
    "zh_to_en": "spelling",
    "audio_to_en": "listening_spelling",
    "en_to_zh": "meaning_recall",
    "phonetic_to_en": "phonetic_spelling",
}
SKILL_TO_MODE: dict[str, str] = {skill: mode for mode, skill in MODE_TO_SKILL.items()}

# 对外暴露的掌握状态（由 box_level + db status 推导，库里不存这个值）
ApiStatus = Literal["new", "learning", "reviewing", "mastered"]
STATUSES: tuple[str, ...] = ("new", "learning", "reviewing", "mastered")

SortKey = Literal["unit", "alpha", "wrong_first", "recent"]
SORTS: tuple[str, ...] = ("unit", "alpha", "wrong_first", "recent")

POS_VALUES: tuple[str, ...] = (
    "n.",
    "v.",
    "adj.",
    "adv.",
    "prep.",
    "conj.",
    "pron.",
    "num.",
    "phr.",
)

RANGE_TYPES: tuple[str, ...] = ("unit", "theme", "wrongbook", "all")
ORDERS: tuple[str, ...] = ("random", "sequential", "weak_first")

# 错词本排序口径。默认 due：错词本的第一诉求是「现在该练哪些」
WRONGBOOK_SORTS: tuple[str, ...] = ("due", "wrong_count", "recent")

# 错词本手动操作
ACTION_MASTER = "master"
ACTION_RESET = "reset"
WRONGBOOK_ACTIONS: tuple[str, ...] = (ACTION_MASTER, ACTION_RESET)

# 盒子 4 及以上算「复习中」，5 且标记 mastered 算毕业
REVIEWING_BOX = 4
MASTER_BOX = 5


def mode_to_skill(mode: str) -> str:
    """题型 -> 技能。未知值抛 ValueError，让调用方在入口拦掉。"""
    try:
        return MODE_TO_SKILL[mode]
    except KeyError:
        raise ValueError(f"未知题型：{mode}") from None


def skill_to_mode(skill: str) -> str:
    """技能 -> 题型。

    未知技能**原样返回**而不是抛错：历史数据里如果混进了别的技能名，
    读接口不该因此 500 —— 少一个字段的正确性，比整个列表打不开要好。
    """
    return SKILL_TO_MODE.get(skill, skill)


def derive_status(box_level: int | None, db_status: str | None) -> str:
    """把 (盒级, 库内状态) 折算成对外的四态。

    注意 `new`（未学）不在这里判断 —— 那是「没有进度行」，
    必须在查询层用 LEFT JOIN / EXISTS 判，不能靠 box_level 猜。
    """
    if db_status == "mastered":
        return "mastered"
    if box_level is None:
        return "new"
    if box_level >= REVIEWING_BOX:
        return "reviewing"
    return "learning"


def explain_mode(mode: str) -> str:
    """题型的中文名，日志与错误提示里用。"""
    return {
        "zh_to_en": "汉译英",
        "audio_to_en": "听音写词",
        "en_to_zh": "英译汉",
        "phonetic_to_en": "音标写词",
    }.get(mode, mode)


def explain_skill(skill: str) -> str:
    return {
        "spelling": "拼写",
        "listening_spelling": "听音拼写",
        "meaning_recall": "词义回忆",
        "phonetic_spelling": "音标拼写",
    }.get(skill, skill)
