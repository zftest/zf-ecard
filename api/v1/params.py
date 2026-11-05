"""请求参数校验。

为什么用 pydantic 而不是手写 if：
    手写校验的典型结局是「这个接口校验了 page_size，那个接口忘了」，
    越界值一路走到 SQL 里变成 `LIMIT -1`（SQLite 里等价于不限条数），
    接口看起来正常，实际把整张表返回给前端。

统一在这里做三件事：
    1. 空字符串当"没传"处理（`?q=` 与 `?q` 不该有两种行为）
    2. 枚举值不合法时给出中文提示，而不是 pydantic 的英文原文
    3. 所有错误一次性收集成 details 数组返回，不是遇到第一个就停
"""
from __future__ import annotations

from typing import Any, Mapping, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from api.v1.errors import ValidationFailed
from core.vocabulary import MODES, ORDERS, RANGE_TYPES, SORTS, STATUSES


def _humanize(error: dict[str, Any]) -> dict[str, str]:
    """把 pydantic 的英文报错翻成能直接显示给用户的中文。"""
    field = ".".join(str(part) for part in error["loc"]) or "(请求)"
    kind = error["type"]
    ctx = error.get("ctx") or {}

    if kind == "literal_error":
        allowed = ctx.get("expected", "")
        return {"field": field, "message": f"取值必须是 {allowed} 之一"}
    if kind in {"greater_than_equal", "greater_than"}:
        return {"field": field, "message": f"必须大于等于 {ctx.get('ge', ctx.get('gt'))}"}
    if kind in {"less_than_equal", "less_than"}:
        return {"field": field, "message": f"必须小于等于 {ctx.get('le', ctx.get('lt'))}"}
    if kind == "int_parsing":
        return {"field": field, "message": "必须是整数"}
    if kind == "string_too_long":
        return {"field": field, "message": f"长度不能超过 {ctx.get('max_length')} 个字符"}
    if kind == "missing":
        return {"field": field, "message": "该参数必填"}
    if kind == "value_error":
        # pydantic 会把自定义 ValueError 包成 "Value error, xxx"，去掉这段前缀
        message = str(error.get("msg", "")).removeprefix("Value error, ")
        return {"field": field, "message": message or "参数不合法"}
    return {"field": field, "message": error.get("msg", "参数不合法")}


def parse_query(model_cls: type[BaseModel], args: Mapping[str, str]):
    """把查询字符串解析成校验过的模型；失败抛 ValidationFailed。"""
    raw = {key: value for key, value in args.items() if value != ""}
    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        raise ValidationFailed(details=[_humanize(err) for err in exc.errors()]) from None


def parse_body(model_cls: type[BaseModel], payload: Any):
    """把 JSON 请求体解析成校验过的模型。

    单独一个入口的原因：`request.get_json()` 在 body 不是合法 JSON 时
    会抛 400 的框架异常，在 body 为空时返回 None。
    两种情况的报错形态不一样，前端要写两个分支才能判断"我到底哪里错了"。
    这里统一成 `VALIDATION_ERROR` + 明确文案。
    """
    if payload is None:
        raise ValidationFailed(
            message="请求体必须是 JSON 对象",
            details=[{"field": "(请求体)", "message": "缺少 JSON body 或 Content-Type 不是 application/json"}],
        )
    if not isinstance(payload, dict):
        raise ValidationFailed(
            message="请求体必须是 JSON 对象",
            details=[{"field": "(请求体)", "message": "顶层必须是对象 {}, 不是数组或字符串"}],
        )
    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise ValidationFailed(details=[_humanize(err) for err in exc.errors()]) from None



class _Base(BaseModel):
    # 多余参数直接忽略：前端加个缓存击穿参数 `_t=...` 不该换来一个 400
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class PaginationQuery(_Base):
    page: int = Field(1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，1-100")


class UnitsQuery(_Base):
    learner_id: str = "default"
    book: str | None = Field(None, max_length=64, description="册次，如「七年级上册」")


class ThemesQuery(_Base):
    learner_id: str = "default"


class WordListQuery(PaginationQuery):
    learner_id: str = "default"
    q: str | None = Field(None, max_length=50, description="同时匹配词形与中文释义")
    unit: int | None = Field(None, ge=1, description="单元 ID（整数）")
    theme: str | None = Field(None, max_length=32)
    pos: list[str] | None = Field(None, description="词性，英文逗号分隔，如 n.,v.")
    status: list[str] | None = Field(
        None, description="掌握状态，英文逗号分隔，如 learning,reviewing"
    )
    skill: Literal[*MODES] = "zh_to_en"
    sort: Literal[*SORTS] = "unit"

    @field_validator("pos", "status", mode="before")
    @classmethod
    def _split_commas(cls, value):
        """`n.,v.` -> ['n.', 'v.']；空串在 parse_query 里已经被丢掉。"""
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",") if part.strip()]
            return parts or None
        return value

    @field_validator("status", mode="after")
    @classmethod
    def _check_status(cls, value):
        if value is None:
            return value
        unknown = [item for item in value if item not in STATUSES]
        if unknown:
            raise ValueError(f"未知状态：{', '.join(unknown)}")
        return value


class WordDetailQuery(_Base):
    learner_id: str = "default"


class LearnerQuery(_Base):
    pass


class StatsQuery(_Base):
    """趋势天数只允许 7 / 14 / 30。

    这里用 int + 白名单而不是 Literal[7, 14, 30]：
    查询串永远是字符串，pydantic 对 Literal 做的是"字面量相等"比较，
    "7" != 7 会直接判非法 —— 用户传 days=7 却收到 400，很难理解。
    """

    days: int = Field(7, description="趋势天数，只能取 7 / 14 / 30")

    @field_validator("days", mode="after")
    @classmethod
    def _check_days(cls, value: int) -> int:
        if value not in (7, 14, 30):
            raise ValueError("只允许 7、14 或 30")
        return value


# ─────────────────────────────────────────────────────────────
# 请求体（POST）
# ─────────────────────────────────────────────────────────────


class CreateSessionBody(_Base):
    """创建练习会话。

    `range` 是 Python 内置函数名，但在 pydantic 模型里作为字段名没问题，
    JSON 里的 key 就叫 `range`（契约文档这么写，前端不用迁就 Python）。
    """

    learner_id: str = Field("default", max_length=32)
    range: Literal[*RANGE_TYPES]
    range_value: str | None = Field(None, max_length=64)
    mode: Literal[*MODES]
    size: int = Field(20, ge=5, le=50, description="题量，5-50")
    order: Literal[*ORDERS] = "random"
    hint_enabled: bool = True


class SubmitAnswerBody(_Base):
    """提交一道题的作答。

    `answer` 允许空串：孩子直接点"不会"也是合法作答，
    判错即可，不该返 400 —— 那会让前端弹"请求失败"，把业务结果当成故障。
    """

    item_id: int = Field(..., ge=1)
    answer: str = Field("", max_length=100)
    hint_used: bool = False
    replay_count: int = Field(0, ge=0, le=20)
    elapsed_ms: int = Field(0, ge=0, le=600000)


class SessionQuery(_Base):
    """查询会话。`include_answers` 只在结果页开，作答中不要开。"""

    include_answers: bool = False

