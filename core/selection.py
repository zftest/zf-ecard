"""抽题排序：纯函数，输入候选义项列表，输出排好序的列表。

为什么不写在路由里：
    三个顺序（random / sequential / weak_first）各有一条隐含规则，
    混在 HTTP 处理里就只能靠手工点页面验证。抽出来之后可以精确断言
    「薄弱优先是不是真的把盒子 1 排在了盒子 5 前面」。

两条实现细节：

1. **weak_first 用「先洗牌再稳定排序」，而不是给同盒子的项加随机权重。**
   稳定排序保证同盒子内保持洗牌后的顺序 —— 既是随机的，又真的按盒子分层。
   给盒子乘一个随机系数那种写法会让盒子 4 偶尔排到盒子 1 前面。

2. **没有进度行（新词）的盒子按 0 算。**
   新词最该练，如果按 None 排会被丢到最后，等于「越不会越不出现」。
"""
from __future__ import annotations

import random

ORDER_RANDOM = "random"
ORDER_SEQUENTIAL = "sequential"
ORDER_WEAK_FIRST = "weak_first"

# 新词（没有 skill_progress 行）的虚拟盒子：低于第 1 盒，最优先
NEW_WORD_BOX = 0


def _shuffled(candidates: list[dict], rng: random.Random) -> list[dict]:
    copied = list(candidates)
    rng.shuffle(copied)
    return copied


def order_candidates(
    candidates: list[dict],
    order: str = ORDER_RANDOM,
    rng: random.Random | None = None,
) -> list[dict]:
    """按策略排序候选义项。

    :param candidates: 每项至少含 `box`（int | None）与 `order_key`（可比较的元组）
    :param order: random / sequential / weak_first
    :param rng: 便于测试注入固定种子；默认新建
    """
    rng = rng or random.Random()
    rows = list(candidates)

    if order == ORDER_SEQUENTIAL:
        # 按教材顺序：册 -> 单元 -> 词 -> 义项。孩子更适应"从头往下背"
        return sorted(rows, key=lambda row: row["order_key"])

    shuffled = _shuffled(rows, rng)
    if order == ORDER_WEAK_FIRST:
        # 洗牌后再稳定排序：盒子升序，同盒子内保留洗牌顺序
        return sorted(
            shuffled,
            key=lambda row: NEW_WORD_BOX if row.get("box") is None else row["box"],
        )
    return shuffled


def pick(candidates: list[dict], size: int, order: str, rng: random.Random | None = None):
    """排序后取前 size 个。返回 (选中的题, 是否池子不足)。"""
    ordered = order_candidates(candidates, order, rng)
    chosen = ordered[: max(0, size)]
    return chosen, len(ordered) < size
