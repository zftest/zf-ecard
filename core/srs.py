"""五盒间隔重复调度（Leitner 变体）。

为什么不用 FSRS / Anki 那套记忆模型：
    单人使用、每天题量几十个、需要「家长能一眼看懂今天为什么该练这个词」。
    五盒规则的每个数字都能在界面上解释清楚，这是它唯一但决定性的优势。
    引入 FSRS 的代价是三个权重矩阵 + 一个依赖库，收益在小样本下无法验证。

盒子含义：
    1  刚学会 / 刚答错，需要当天再练
    2  隔 1 天
    3  隔 2 天
    4  隔 5 天
    5  隔 10 天（连续答对 3 次即可判定「已掌握」，退出错词本）

三条调度规则（全部是纯函数，可单测）：
    答错         → 降回第 1 盒，10 分钟后重练
    用提示答对   → 盒子不动，明天再练（答对了但不算掌握）
    独立答对     → 升一盒，按新盒子的间隔安排
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

MIN_BOX = 1
MAX_BOX = 5

# 盒子 → 答对后再隔几天出现
BOX_INTERVAL_DAYS: dict[int, int] = {1: 0, 2: 1, 3: 2, 4: 5, 5: 10}

# 答错后多久重练（分钟）。不设 0 是为了避免同一次会话里死循环出同一题
WRONG_RETRY_MINUTES = 10
# 用提示答对后的重练间隔（天）
HINT_RETRY_DAYS = 1
# 判定「已掌握」的条件
MASTER_BOX = MAX_BOX
MASTER_MIN_CORRECT = 3


@dataclass(frozen=True)
class ScheduleResult:
    """一次调度决策的结果。"""

    box_level: int
    due_at: dt.datetime
    reason: str  # 给界面直接显示的中文原因，例如「答错，降回第 1 盒」

    @property
    def is_mastered(self) -> bool:
        return self.box_level >= MASTER_BOX


def _coerce_box(box_level: int | None) -> int:
    if box_level is None:
        return MIN_BOX
    return max(MIN_BOX, min(MAX_BOX, int(box_level)))


def _ensure_aware(now: dt.datetime | None) -> dt.datetime:
    """统一成带时区的 UTC 时间。

    传进来的 naive 时间按 UTC 解释（不是本地时间），全库只有一种时区，
    否则「下次复习时间」会莫名其妙差几个小时。
    """
    if now is None:
        return dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(dt.timezone.utc)


def next_interval_days(box_level: int | None) -> int:
    """第 N 盒的复习间隔（天）。"""
    return BOX_INTERVAL_DAYS.get(_coerce_box(box_level), 0)


def schedule(
    box_level: int | None,
    is_correct: bool,
    hint_used: bool = False,
    now: dt.datetime | None = None,
) -> ScheduleResult:
    """算出答题后的新盒子与下次复习时间。"""
    current = _coerce_box(box_level)
    moment = _ensure_aware(now)

    if not is_correct:
        return ScheduleResult(
            box_level=MIN_BOX,
            due_at=moment + dt.timedelta(minutes=WRONG_RETRY_MINUTES),
            reason=f"答错，降回第 {MIN_BOX} 盒，{WRONG_RETRY_MINUTES} 分钟后再练",
        )

    if hint_used:
        return ScheduleResult(
            box_level=current,
            due_at=moment + dt.timedelta(days=HINT_RETRY_DAYS),
            reason=f"用提示答对，停留第 {current} 盒，明天再练一次",
        )

    new_box = min(current + 1, MAX_BOX)
    days = next_interval_days(new_box)
    if new_box >= MASTER_BOX:
        reason = f"独立答对，升到第 {new_box} 盒（已到掌握线），{days} 天后复习"
    else:
        reason = f"独立答对，升到第 {new_box} 盒，{days} 天后复习"
    return ScheduleResult(
        box_level=new_box,
        due_at=moment + dt.timedelta(days=days),
        reason=reason,
    )


def is_mastered(box_level: int | None, correct_count: int) -> bool:
    """是否已达「掌握」：到第 5 盒且独立答对次数够。"""
    return _coerce_box(box_level) >= MASTER_BOX and correct_count >= MASTER_MIN_CORRECT


def due_state(due_at: dt.datetime | None, now: dt.datetime | None = None) -> str:
    """返回 due_at 相对当前时间的状态，供错词本分组显示。

    overdue    已过期（欠着没练）
    today      今天到期
    future     还没到
    """
    if due_at is None:
        return "overdue"
    moment = _ensure_aware(now)
    due = _ensure_aware(due_at)
    if due <= moment:
        return "overdue"
    if due.date() == moment.date():
        return "today"
    return "future"


def days_until_due(due_at: dt.datetime | None, now: dt.datetime | None = None) -> int:
    """距离到期还有几天（向上取整；已到期返回 0）。

    用于界面上的「下次复习：3 天后」。
    """
    if due_at is None:
        return 0
    delta = _ensure_aware(due_at) - _ensure_aware(now)
    if delta.total_seconds() <= 0:
        return 0
    return math.ceil(delta.total_seconds() / 86400)
