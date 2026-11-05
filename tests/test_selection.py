"""抽题排序单测（T4-3）。

抽题错了不会报错，只会"每次都是同一批词"或者"最该练的词永远排在最后"——
后者尤其隐蔽：界面看起来正常，孩子练了两周还是那几个词在循环。
"""
from __future__ import annotations

import random

from core.selection import order_candidates, pick


def _cand(word_id: int, box: int | None, order_key: tuple | None = None) -> dict:
    return {
        "word_id": word_id,
        "box": box,
        "order_key": order_key or (1, word_id, word_id, 1),
    }


def test_sequential_follows_textbook_order():
    rows = [
        _cand(3, None, (1, 3, 3, 1)),
        _cand(1, None, (1, 1, 1, 1)),
        _cand(2, None, (1, 2, 2, 1)),
    ]
    ordered = order_candidates(rows, "sequential")
    assert [row["word_id"] for row in ordered] == [1, 2, 3]


def test_random_keeps_every_candidate():
    rows = [_cand(index, None) for index in range(30)]
    ordered = order_candidates(rows, "random", random.Random(7))
    assert sorted(row["word_id"] for row in ordered) == list(range(30))


def test_random_is_stable_for_the_same_seed():
    """给种子必须可复现，否则这条规则没法测。"""
    rows = [_cand(index, None) for index in range(10)]
    first = order_candidates(rows, "random", random.Random(42))
    second = order_candidates(rows, "random", random.Random(42))
    assert [row["word_id"] for row in first] == [row["word_id"] for row in second]


def test_weak_first_puts_new_words_before_learned_ones():
    """新词没有进度行，按 0 算，必须排在最前面 —— 越不会越该出现。"""
    rows = [_cand(1, 5), _cand(2, None), _cand(3, 3)]
    ordered = order_candidates(rows, "weak_first", random.Random(1))
    assert [row["word_id"] for row in ordered] == [2, 3, 1]


def test_weak_first_is_monotonic_by_box():
    rows = [_cand(index, index % 5 + 1) for index in range(20)]
    ordered = order_candidates(rows, "weak_first", random.Random(3))
    boxes = [row["box"] for row in ordered]
    assert boxes == sorted(boxes)


def test_pick_reports_insufficient_pool():
    rows = [_cand(index, None) for index in range(6)]
    chosen, insufficient = pick(rows, 20, "random", random.Random(1))
    assert len(chosen) == 6
    assert insufficient is True


def test_pick_caps_at_requested_size():
    rows = [_cand(index, None) for index in range(30)]
    chosen, insufficient = pick(rows, 10, "random", random.Random(1))
    assert len(chosen) == 10
    assert insufficient is False


def test_pick_never_returns_duplicates():
    rows = [_cand(index, None) for index in range(30)]
    chosen, _ = pick(rows, 30, "random", random.Random(5))
    assert len({row["word_id"] for row in chosen}) == 30
