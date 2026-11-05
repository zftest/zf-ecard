"""判题核心：纯函数，不碰数据库、不碰 HTTP。

为什么单独一层且必须纯函数：
    判题写错了**不会报错**，只会静默判错 —— 孩子写对了系统说错。
    家长的第一反应是"孩子记错了"，不是"软件有 bug"，
    所以这类错误能一直藏到统计全乱、错词本全是熟词才被发现。
    纯函数才能用几十条用例把边界钉死。

三个刻意的规则（与 docs/prd-junior-vocabulary-dictation-v0.2.md 一致）：

1. **只做无损归一，不做模糊匹配。**
   大小写、全角、弯引号、多空格、首尾标点都折叠；
   但「经历」和「经验」这种语义判断绝不靠编辑距离猜 ——
   它必须走 `word_senses.accepted` 人工维护，因为只有家长能拍板。

2. **`near_miss` 只提示，不放水。**
   距离为 1 且长度 ≥ 6 时提示「很接近，再检查一下」，但 `correct` 仍是 false。
   一旦"差一个字母也算对"，默写的意义就没了。

3. **diff 的 `pos` 是渲染顺序索引，不是原字符串下标。**
   前端按数组顺序逐格画即可，不需要自己算插入点。
   漏写的字符用 expected 的字符 + `missing` 表示（画成占位方块），
   多写的字符用用户输入的字符 + `extra` 表示（画成红色删除线）。
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from core.normalize import normalize_en, normalize_zh

# diff 单元格状态
OK = "ok"
MISSING = "missing"
EXTRA = "extra"
WRONG = "wrong"

# 近失（near miss）判定门槛：距离必须正好 1，且标准答案够长
# 短词（如 it / an）差一个字母就是另一个词，给"很接近"反而误导
NEAR_MISS_MAX_DISTANCE = 1
NEAR_MISS_MIN_LENGTH = 6

# 中文答案不做 near_miss：汉字距离没有意义
ZH_LANG = "zh"
EN_LANG = "en"


@dataclass(frozen=True)
class GradeResult:
    """一次判题的完整结果，字段与 `GradeResult` 契约一一对应。"""

    correct: bool
    near_miss: bool
    distance: int
    expected: str
    normalized_input: str
    diff: list[dict] = field(default_factory=list)
    feedback: str = ""
    hint_used: bool = False
    first_try_correct: bool = False


def levenshtein(left: str, right: str) -> int:
    """编辑距离（插入/删除/替换各计 1）。

    用滚动数组，空间 O(min(m, n))：判题会在一道题里被调用多次，
    没必要为几十个字符的字符串分配二维表。
    """
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    if len(left) < len(right):
        left, right = right, left

    previous = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        current = [i]
        for j, rch in enumerate(right, start=1):
            cost = 0 if lch == rch else 1
            current.append(
                min(
                    previous[j] + 1,        # 删除
                    current[j - 1] + 1,     # 插入
                    previous[j - 1] + cost,  # 替换
                )
            )
        previous = current
    return previous[-1]


def build_diff(user_input: str, expected: str) -> list[dict]:
    """逐字符差异，供前端画"漏写占位块 / 多写删除线"。

    :param user_input: 已规范化的作答
    :param expected: 已规范化的标准答案
    :return: `[{pos, char, status, input?}]`，按渲染顺序排列

    对齐用 LCS（`difflib.SequenceMatcher`），不是逐位比较：
    逐位比较时 "enviroment" vs "environment" 会从第 6 位起全部标成"写错"，
    孩子看到满屏红叉，实际只漏了一个字母，反而更打击人。
    """
    cells: list[dict] = []
    matcher = difflib.SequenceMatcher(None, expected, user_input, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                cells.append(
                    {"pos": len(cells), "char": expected[i1 + offset], "status": OK}
                )
        elif tag == "delete":
            # 只在标准答案里有 -> 用户漏写
            for offset in range(i2 - i1):
                cells.append(
                    {"pos": len(cells), "char": expected[i1 + offset], "status": MISSING}
                )
        elif tag == "insert":
            # 只在用户输入里有 -> 多写
            for offset in range(j2 - j1):
                cells.append(
                    {"pos": len(cells), "char": user_input[j1 + offset], "status": EXTRA}
                )
        else:  # replace：先按位标"写错"，余下的再分漏写 / 多写
            shared = min(i2 - i1, j2 - j1)
            for offset in range(shared):
                cells.append(
                    {
                        "pos": len(cells),
                        "char": expected[i1 + offset],
                        "status": WRONG,
                        "input": user_input[j1 + offset],
                    }
                )
            for offset in range(shared, i2 - i1):
                cells.append(
                    {"pos": len(cells), "char": expected[i1 + offset], "status": MISSING}
                )
            for offset in range(shared, j2 - j1):
                cells.append(
                    {"pos": len(cells), "char": user_input[j1 + offset], "status": EXTRA}
                )
    return cells


def _brief(items: list[str]) -> str:
    """把字符列表拼成「n」「n、t」这种短串，最多列 3 个。"""
    unique: list[str] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    shown = "、".join(unique[:3])
    if len(unique) > 3:
        shown += " 等"
    return shown


def summarize(diff: list[dict], correct: bool, hint_used: bool) -> str:
    """把 diff 折成一句人话，前端直接显示，不再自己拼文案。"""
    if correct:
        return "答对了（用了提示，不计入首答正确率）" if hint_used else "答对了"

    missing = [cell["char"] for cell in diff if cell["status"] == MISSING]
    extra = [cell["char"] for cell in diff if cell["status"] == EXTRA]
    wrong = [cell for cell in diff if cell["status"] == WRONG]

    parts: list[str] = []
    if missing:
        parts.append(f"少写了 {len(missing)} 个字母（{_brief(missing)}）")
    if extra:
        parts.append(f"多写了 {len(extra)} 个字母（{_brief(extra)}）")
    if wrong:
        first = wrong[0]
        parts.append(
            f"第 {first['pos'] + 1} 个字母应该是 {first['char']}，你写的是 {first.get('input', '')}"
        )

    if not parts:  # pragma: no cover - 理论上不可能：判错必有差异
        return "答案不对，再检查一下"
    return "；".join(parts[:2])


def _is_near_miss(distance: int, expected: str, lang: str) -> bool:
    if lang != EN_LANG:
        return False
    return distance <= NEAR_MISS_MAX_DISTANCE and len(expected) >= NEAR_MISS_MIN_LENGTH


def grade(
    answer: str | None,
    expected: str,
    *,
    lang: str = EN_LANG,
    accepted: list[str] | None = None,
    hint_used: bool = False,
) -> GradeResult:
    """判一道题。

    :param answer: 用户原始输入（**不要预先处理**，归一化只在这里做一次）
    :param expected: 标准答案（英文是词形，中文是释义）
    :param lang: "en" 走英文归一化，"zh" 走中文归一化
    :param accepted: 人工维护的等价写法（中文同义词 / 拼写变体）
    :param hint_used: 是否用过提示。它**不影响对错**，只影响 `first_try_correct`
    """
    normalize = normalize_en if lang == EN_LANG else normalize_zh
    normalized_input = normalize(answer)
    normalized_expected = normalize(expected)

    candidates = [normalized_expected]
    for item in accepted or []:
        key = normalize(item)
        if key and key not in candidates:
            candidates.append(key)

    # 空作答一定判错：不能让 "" 和空答案"相等"
    correct = bool(normalized_input) and normalized_input in candidates

    if correct:
        diff = [
            {"pos": index, "char": char, "status": OK}
            for index, char in enumerate(normalized_expected)
        ]
        distance = 0
    else:
        diff = build_diff(normalized_input, normalized_expected)
        distance = levenshtein(normalized_input, normalized_expected)

    return GradeResult(
        correct=correct,
        near_miss=_is_near_miss(distance, normalized_expected, lang),
        distance=distance,
        expected=expected,
        normalized_input=normalized_input,
        diff=diff,
        feedback=summarize(diff, correct, hint_used),
        hint_used=hint_used,
        first_try_correct=correct and not hint_used,
    )


def make_hint(spelling: str) -> str:
    """首字母 + 下划线占位，例如 environment -> e__________。

    只给首字母：给太多就等于抄答案，给 0 个则等于没有提示。
    """
    text = (spelling or "").strip()
    if not text:
        return ""
    return text[0] + "_" * (len(text) - 1)
