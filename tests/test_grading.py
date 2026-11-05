"""判题规则单测（T4-1 / T4-2）。

这一组测试的价值不在"覆盖率高"，而在于：
判题写错**不会抛异常**，只会静默判错。孩子写对了系统说错，
家长的第一反应是"孩子记错了"，不是"软件有 bug"。

所以这里刻意把每一类"看起来一样、其实写法不同"的输入都固定下来：
大小写、全角、弯引号、连字符变体、多空格、首尾标点、漏字母、多字母、错字母。
"""
from __future__ import annotations

import pytest

from core.grading import (
    EXTRA,
    MISSING,
    OK,
    WRONG,
    build_diff,
    grade,
    levenshtein,
    make_hint,
    summarize,
)


def _statuses(cells: list[dict]) -> list[str]:
    return [cell["status"] for cell in cells]


# ─────────────────────────────────────────────────────────────
# 规范化后应当判对
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "answer",
    [
        "environment",
        "Environment",
        " ENVIRONMENT ",
        "environmenT",
        "ｅｎｖｉｒｏｎｍｅｎｔ",  # 全角（中文输入法下极易发生）
    ],
)
def test_case_space_and_fullwidth_are_correct(answer):
    assert grade(answer, "environment").correct is True


@pytest.mark.parametrize("answer", ["don't", "don’t", "DON’T", "donʼt"])
def test_apostrophe_variants_are_correct(answer):
    """手机输入法默认输出弯引号，不折叠的话每次都要判错。"""
    assert grade(answer, "don't").correct is True


@pytest.mark.parametrize("answer", ["ice-cream", "ice – cream", "ice—cream"])
def test_hyphen_variants_are_correct(answer):
    assert grade(answer, "ice-cream").correct is True


def test_light_ice_cream_with_space_is_not_hyphenated():
    """"ice cream" 与 "ice-cream" 是两个词形，不能互相折叠。

    这条是反向用例：只折叠连字符的变体，不折叠空格。
    """
    assert grade("ice cream", "ice-cream").correct is False


def test_trailing_punctuation_is_ignored():
    assert grade("apple.", "apple").correct is True


def test_internal_multi_space_collapses():
    assert grade("hello    world", "hello world").correct is True


# ─────────────────────────────────────────────────────────────
# 中文答案
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("answer", ["环境", "环境。", "环 境", "环境，"])
def test_chinese_punctuation_and_space_are_ignored(answer):
    assert grade(answer, "环境", lang="zh").correct is True


def test_chinese_accepted_synonym_counts_as_correct():
    """同义写法只走 accepted 配置，不做语义推断。

    「自然环境」算对是因为家长维护过，「环境好」不算对也不是 bug。
    """
    result = grade("自然环境", "环境", lang="zh", accepted=["自然环境", "生态环境"])
    assert result.correct is True


def test_chinese_unlisted_synonym_is_wrong():
    """没维护过的同义写法必须判错 —— 这是刻意的，不是能力不足。

    「经历」和「经验」到底算不算同一个答案，只有家长能拍板；
    靠编辑距离猜会把整本词库的判题口径交给运气。
    """
    assert grade("经验", "经历", lang="zh").correct is False


def test_chinese_answer_never_near_miss():
    result = grade("环镜", "环境", lang="zh")
    assert result.correct is False
    assert result.near_miss is False, "汉字的编辑距离没有意义，不许给近失"


# ─────────────────────────────────────────────────────────────
# 错误类型与逐字符 diff
# ─────────────────────────────────────────────────────────────


def test_missing_letter_marks_one_cell():
    result = grade("enviroment", "environment")
    assert result.correct is False
    assert result.distance == 1
    missing = [cell for cell in result.diff if cell["status"] == MISSING]
    assert [cell["char"] for cell in missing] == ["n"]


def test_extra_letter_is_marked_extra():
    result = grade("envirronment", "environment")
    assert result.correct is False
    extras = [cell for cell in result.diff if cell["status"] == EXTRA]
    assert [cell["char"] for cell in extras] == ["r"]


def test_wrong_letter_records_input():
    result = grade("enviroament", "environment")
    assert result.correct is False
    wrong = [cell for cell in result.diff if cell["status"] == WRONG]
    assert wrong and wrong[0]["char"] == "n" and wrong[0]["input"] == "a"


def test_diff_positions_are_contiguous():
    """pos 是渲染顺序索引，前端按数组顺序画即可，不用自己算插入点。"""
    cells = build_diff("enviroment", "environment")
    assert [cell["pos"] for cell in cells] == list(range(len(cells)))


def test_correct_answer_diff_is_all_ok():
    result = grade("environment", "environment")
    assert result.distance == 0
    assert set(_statuses(result.diff)) == {OK}


def test_empty_answer_is_wrong_not_crash():
    result = grade("", "environment")
    assert result.correct is False
    assert result.distance == len("environment")
    assert result.feedback, "空作答也要给一句人话，不能返回空字符串"


def test_none_answer_is_wrong():
    assert grade(None, "environment").correct is False


# ─────────────────────────────────────────────────────────────
# near_miss：只提示，不放水
# ─────────────────────────────────────────────────────────────


def test_near_miss_true_when_distance_one_and_long_enough():
    assert grade("enviroment", "environment").near_miss is True


def test_near_miss_false_for_short_word():
    """cat / cut 差一个字母就是另一个词，提示"很接近"是误导。"""
    assert grade("cut", "cat").near_miss is False


def test_near_miss_false_when_distance_two():
    assert grade("enviromentt", "environment").near_miss is False


def test_near_miss_does_not_make_it_correct():
    result = grade("enviroment", "environment")
    assert result.near_miss is True and result.correct is False


# ─────────────────────────────────────────────────────────────
# 提示与首答
# ─────────────────────────────────────────────────────────────


def test_hint_used_keeps_correct_but_kills_first_try():
    result = grade("environment", "environment", hint_used=True)
    assert result.correct is True
    assert result.first_try_correct is False
    assert "提示" in result.feedback


def test_without_hint_first_try_is_true():
    assert grade("environment", "environment").first_try_correct is True


def test_wrong_answer_is_never_first_try_correct():
    assert grade("enviroment", "environment").first_try_correct is False


def test_make_hint_keeps_first_letter_and_length():
    assert make_hint("environment") == "e" + "_" * 10
    assert make_hint("") == ""


def test_summarize_mentions_missing_letter():
    assert "少写" in summarize(build_diff("enviroment", "environment"), False, False)


# ─────────────────────────────────────────────────────────────
# 编辑距离本身
# ─────────────────────────────────────────────────────────────


def test_levenshtein_is_symmetric_and_sane():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("sitting", "kitten") == 3
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3
    assert levenshtein("same", "same") == 0
