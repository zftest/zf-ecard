"""文本规范化测试。

这些用例的来源不是「想测什么写什么」，而是**实际会发生的输入错误**：
手机输入法的弯引号、中文输入法全角状态下的英文、孩子多打的空格、
复制的词条带词性前缀。每一条都对应一次「明明写对了却被判错」的投诉。
"""
import pytest

from core.normalize import (
    build_accepted_keys,
    is_answer_accepted,
    normalize_en,
    normalize_zh,
    split_variants,
    strip_pos_prefix,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("environment", "environment"),
        ("Environment", "environment"),
        ("  environment  ", "environment"),
        ("ｅｎｖｉｒｏｎｍｅｎｔ", "environment"),  # 全角字母
        ("ice - cream", "ice-cream"),  # 连字符两侧空格
        ("ice–cream", "ice-cream"),  # en dash
        ("ice—cream", "ice-cream"),  # em dash
        ("don’t", "don't"),  # 弯撇号
        ("don`t", "don't"),  # 反引号
        ("hello   world", "hello world"),  # 多空格折叠
        ("book.", "book"),  # 首尾标点
        ("(book)", "book"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_en(raw, expected):
    assert normalize_en(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("环境", "环境"),
        (" 环 境 ", "环境"),  # 中文答案里的空格无意义
        ("环境，", "环境"),  # 中文逗号
        ("环境。", "环境"),
        ("环境、自然", "环境自然"),
        ("（环境）", "环境"),
        ("环境 ", "环境"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_zh(raw, expected):
    assert normalize_zh(raw) == expected


def test_normalize_en_keeps_inner_apostrophe():
    """词内撇号不能被剥掉，否则 don't 会被判成 dont。"""
    assert normalize_en("Don't") == "don't"
    assert normalize_en("don't.") == "don't"


def test_strip_pos_prefix():
    assert strip_pos_prefix("n. 环境") == "环境"
    assert strip_pos_prefix("adj.整洁的") == "整洁的"
    assert strip_pos_prefix("v. 保持") == "保持"
    # 不是词性前缀的内容原样保留
    assert strip_pos_prefix("环境") == "环境"
    # 避免把单词本体的开头误当词性：nice 不能被当成 n 前缀
    assert strip_pos_prefix("nice") == "nice"


def test_split_variants():
    assert split_variants("祖父|外公|姥爷") == ["祖父", "外公", "姥爷"]
    assert split_variants("祖父/外公") == ["祖父", "外公"]
    assert split_variants("") == []
    assert split_variants(None) == []
    # 多余空格与空项要被丢掉，否则会生成一个 "" 的空答案
    assert split_variants(" 祖父 | | 外公 ") == ["祖父", "外公"]


def test_build_accepted_keys_primary_first():
    keys = build_accepted_keys("爷爷", ["祖父", "外公"])
    assert keys[0] == "爷爷"
    assert set(keys) == {"爷爷", "祖父", "外公"}


def test_build_accepted_keys_dedupes():
    """accepted 里重复标准释义时不该产生两个相同 key。"""
    keys = build_accepted_keys("爷爷", ["爷爷", "祖父"])
    assert keys == ["爷爷", "祖父"]


def test_is_answer_accepted_en():
    assert is_answer_accepted("Environment", "environment", lang="en")
    assert is_answer_accepted(" environment ", "environment", lang="en")
    assert not is_answer_accepted("enviroment", "environment", lang="en")
    assert not is_answer_accepted("", "environment", lang="en")
    assert not is_answer_accepted(None, "environment", lang="en")


def test_is_answer_accepted_zh_uses_accepted_list():
    """这是「中文同义写法人工维护」真正生效的地方。"""
    assert is_answer_accepted("爷爷", "爷爷", ["外公"], lang="zh")
    assert is_answer_accepted("外公", "爷爷", ["外公"], lang="zh")
    assert is_answer_accepted("外 公。", "爷爷", ["外公"], lang="zh")
    assert not is_answer_accepted("奶奶", "爷爷", ["外公"], lang="zh")


def test_is_answer_accepted_does_not_fuzzy_match():
    """不做模糊匹配是刻意的：编辑距离会把 very 判成 every，比判错更糟。"""
    assert not is_answer_accepted("enviroment", "environment", lang="en")
