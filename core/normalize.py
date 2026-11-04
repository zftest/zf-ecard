"""文本规范化：判题前的统一清洗。

判题必须建立在「规范化之后」的字符串上，否则下面这些都会被判错，
而家长只会得出「这软件判错了」的结论：

    "Environment "   vs  "environment"     首尾空格 + 大小写
    "don’t"          vs  "don't"           弯引号（手机输入法默认输出弯引号）
    "ｅｎｖ"          vs  "env"             全角字母（中文输入法下极易发生）
    "ice – cream"    vs  "ice-cream"       四种以上的连字符变体
    "环境，"          vs  "环境"            中文标点

这里只做「无损归一」——把同一个答案的不同写法折叠成一种，
**不做**模糊匹配（不做编辑距离、不做同义词推断）。
同义词属于业务规则，放在 word_senses.accepted 里由人工维护，
因为「经历」和「经验」到底算不算同一个答案，只有家长能判断。
"""
from __future__ import annotations

import re
import unicodedata

# 各种撇号：' ’ ‘ ʼ ′ ` ´
_APOSTROPHES = "\u2018\u2019\u02bc\u2032\u0060\u00b4"
# 各种连字符：‐ ‑ ‒ – — −
_HYPHENS = "\u2010\u2011\u2012\u2013\u2014\u2212"
# 判题时忽略的标点（中英文都抹掉）
_ZH_PUNCT = "，。、；：！？…—～·「」『』（）【】《》〈〉“”‘’"
_ASCII_PUNCT = ".,;:!?()[]{}<>\"'`"

_WHITESPACE_RE = re.compile(r"\s+")
_HYPHEN_SPACE_RE = re.compile(r"\s*-\s*")
_VARIANT_SPLIT_RE = re.compile(r"[|｜/／]")
# 义项前缀：n. / v. / adj. / vt. ...
_POS_PREFIX_RE = re.compile(
    r"^\s*(?:n|v|vt|vi|adj|adv|prep|conj|pron|num|art|interj|aux|modal)\s*\.\s*",
    re.IGNORECASE,
)


def _to_half_width(text: str) -> str:
    """全角转半角（NFKC）。

    NFKC 同时会把「，」转成「,」、「１」转成「1」，这正是我们要的：
    中文输入法在全角状态下敲出的英文，应该和半角英文等价。
    """
    return unicodedata.normalize("NFKC", text)


def normalize_en(raw: str | None) -> str:
    """规范化英文答案（用于「汉译英 / 听音写词 / 音标写词」）。"""
    if raw is None:
        return ""
    text = _to_half_width(str(raw))

    # 撇号、连字符统一
    text = text.translate(str.maketrans({ch: "'" for ch in _APOSTROPHES}))
    text = text.translate(str.maketrans({ch: "-" for ch in _HYPHENS}))
    text = _HYPHEN_SPACE_RE.sub("-", text)

    # 折叠空白、去首尾空白、统一小写
    text = _WHITESPACE_RE.sub(" ", text).strip().lower()

    # 去掉首尾的英文标点，但不动词内的撇号与连字符
    text = text.strip(_ASCII_PUNCT + " ")
    return text


def normalize_zh(raw: str | None) -> str:
    """规范化中文答案（用于「英译汉」）。"""
    if raw is None:
        return ""
    text = _to_half_width(str(raw))

    # 中文答案里的空格一律无意义："环 境" == "环境"
    text = _WHITESPACE_RE.sub("", text)

    # 中英文标点全部抹掉："环境，自然" == "环境自然"
    text = text.translate(str.maketrans("", "", _ZH_PUNCT + _ASCII_PUNCT))

    return text.lower()


def strip_pos_prefix(raw: str | None) -> str:
    """去掉释义前的词性标记："n. 环境" -> "环境"。"""
    if not raw:
        return ""
    return _POS_PREFIX_RE.sub("", str(raw)).strip()


def split_variants(raw: str | None) -> list[str]:
    """按 | 或 / 切分多写法字段。

    例："自然环境|生态环境" -> ["自然环境", "生态环境"]
    用于 CSV 里的 accepted 列。
    """
    if not raw:
        return []
    return [part.strip() for part in _VARIANT_SPLIT_RE.split(str(raw)) if part.strip()]


def build_accepted_keys(meaning_zh: str | None, accepted: list[str] | None) -> list[str]:
    """把「标准释义 + 人工维护的同义写法」编译成可比较的 key 列表。

    返回的第一个元素永远是标准释义的 key，便于调用方把「首选项」和
    「同义项」区分开（提示功能只给首选项）。
    """
    keys: list[str] = []
    primary = normalize_zh(strip_pos_prefix(meaning_zh))
    if primary:
        keys.append(primary)
    for item in accepted or []:
        key = normalize_zh(strip_pos_prefix(item))
        if key and key not in keys:
            keys.append(key)
    return keys


def is_answer_accepted(
    user_answer: str | None,
    expected: str,
    accepted: list[str] | None = None,
    lang: str = "en",
) -> bool:
    """判断作答是否算对。

    :param lang: "en" 用英文规范化，"zh" 用中文规范化
    """
    normalize = normalize_en if lang == "en" else normalize_zh
    got = normalize(user_answer)
    if not got:
        return False
    candidates = [expected, *(accepted or [])]
    return any(got == normalize(item) for item in candidates if item)
