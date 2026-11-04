"""五盒调度测试。

调度一旦算错，症状是「孩子的复习计划悄悄变形」——不会报错，也不会有红灯，
只是某些词越来越久不出现、另一些词天天重复。所以这里的每条规则都要钉死。
"""
import datetime as dt

import pytest

from core.srs import (
    BOX_INTERVAL_DAYS,
    MASTER_BOX,
    WRONG_RETRY_MINUTES,
    days_until_due,
    due_state,
    is_mastered,
    next_interval_days,
    schedule,
)

NOW = dt.datetime(2026, 11, 4, 9, 0, 0, tzinfo=dt.timezone.utc)


def test_wrong_answer_resets_to_box_one():
    result = schedule(box_level=4, is_correct=False, now=NOW)
    assert result.box_level == 1
    assert result.due_at == NOW + dt.timedelta(minutes=WRONG_RETRY_MINUTES)
    assert result.reason  # 必须给出可展示的中文原因


def test_correct_answer_promotes_one_box():
    result = schedule(box_level=1, is_correct=True, now=NOW)
    assert result.box_level == 2
    assert result.due_at == NOW + dt.timedelta(days=BOX_INTERVAL_DAYS[2])


@pytest.mark.parametrize("box", [1, 2, 3, 4])
def test_each_promotion_uses_new_box_interval(box):
    result = schedule(box_level=box, is_correct=True, now=NOW)
    assert result.box_level == box + 1
    assert (result.due_at - NOW).days == BOX_INTERVAL_DAYS[box + 1]


def test_box_is_capped_at_max():
    """第 5 盒答对仍然是第 5 盒，不能涨到第 6 盒（否则间隔表会 KeyError）。"""
    result = schedule(box_level=MASTER_BOX, is_correct=True, now=NOW)
    assert result.box_level == MASTER_BOX
    assert (result.due_at - NOW).days == BOX_INTERVAL_DAYS[MASTER_BOX]


def test_hint_keeps_box_but_pushes_to_tomorrow():
    """用提示答对不算掌握：盒子不动，但明天必须再验一次。"""
    result = schedule(box_level=3, is_correct=True, hint_used=True, now=NOW)
    assert result.box_level == 3
    assert result.due_at == NOW + dt.timedelta(days=1)


def test_hint_on_box_one_does_not_advance():
    result = schedule(box_level=1, is_correct=True, hint_used=True, now=NOW)
    assert result.box_level == 1
    assert result.due_at == NOW + dt.timedelta(days=1)


def test_wrong_beats_hint():
    """既用提示又答错，按答错处理。"""
    result = schedule(box_level=4, is_correct=False, hint_used=True, now=NOW)
    assert result.box_level == 1


def test_none_box_treated_as_one():
    assert schedule(box_level=None, is_correct=True, now=NOW).box_level == 2


def test_box_out_of_range_is_clamped():
    assert schedule(box_level=99, is_correct=True, now=NOW).box_level == MASTER_BOX
    assert schedule(box_level=0, is_correct=True, now=NOW).box_level == 2


def test_naive_datetime_is_treated_as_utc():
    """传入 naive 时间按 UTC 解释，避免误当本地时间导致差 8 小时。"""
    naive = dt.datetime(2026, 11, 4, 9, 0, 0)
    aware = dt.datetime(2026, 11, 4, 9, 0, 0, tzinfo=dt.timezone.utc)
    assert schedule(1, True, now=naive).due_at == schedule(1, True, now=aware).due_at


def test_schedule_result_marks_mastered():
    assert schedule(MASTER_BOX, True, now=NOW).is_mastered is True
    assert schedule(1, False, now=NOW).is_mastered is False


def test_is_mastered_needs_both_box_and_count():
    assert is_mastered(MASTER_BOX, 3) is True
    assert is_mastered(MASTER_BOX, 2) is False
    assert is_mastered(4, 10) is False


def test_next_interval_days():
    assert next_interval_days(1) == 0
    assert next_interval_days(2) == 1
    assert next_interval_days(10) == BOX_INTERVAL_DAYS[5]  # 越界按第 5 盒


def test_due_state():
    assert due_state(NOW - dt.timedelta(minutes=1), NOW) == "overdue"
    assert due_state(NOW + dt.timedelta(hours=1), NOW) == "today"
    assert due_state(NOW + dt.timedelta(days=3), NOW) == "future"
    assert due_state(None, NOW) == "overdue"


def test_days_until_due_rounds_up():
    assert days_until_due(NOW - dt.timedelta(days=1), NOW) == 0
    assert days_until_due(NOW + dt.timedelta(hours=2), NOW) == 1
    assert days_until_due(NOW + dt.timedelta(days=2), NOW) == 2
    assert days_until_due(NOW + dt.timedelta(days=2, hours=1), NOW) == 3
    assert days_until_due(None, NOW) == 0
