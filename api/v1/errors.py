"""API 错误体系。

一条纪律：**HTTP 状态码表达结果，body 表达原因。**
不用 `{"code": 0, "msg": "ok"}` 那套 —— 那样在浏览器 Network 面板里
所有请求都是 200，出问题根本看不出是哪一步失败的。

另一条纪律：**500 绝不把 Python 异常字符串返回给前端。**
只返回固定文案 + request_id，堆栈进日志。旧接口 `f"AI 生成失败：{str(e)}"`
就是反面例子（会把内部路径、SQL、密钥片段漏给浏览器）。
"""
from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """所有业务错误的基类。子类只需要定 code / status / message。"""

    code: str = "INTERNAL_ERROR"
    status: int = 500
    message: str = "服务器内部错误"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, str]] | None = None,
        code: str | None = None,
        status: int | None = None,
    ) -> None:
        self.message = message or type(self).message
        self.details = details
        self.code = code or type(self).code
        self.status = status or type(self).status
        super().__init__(self.message)

    def to_dict(self, request_id: str) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        # details 只在参数校验失败时出现，避免客户端要判断"这个字段存不存在"
        if self.details:
            error["details"] = self.details
        return {"error": error, "request_id": request_id}


class ValidationFailed(ApiError):
    code = "VALIDATION_ERROR"
    status = 400
    message = "请求参数校验失败"


class NotFound(ApiError):
    code = "NOT_FOUND"
    status = 404
    message = "资源不存在"


class MethodNotAllowed(ApiError):
    code = "METHOD_NOT_ALLOWED"
    status = 405
    message = "请求方法不被支持"


class Conflict(ApiError):
    code = "CONFLICT"
    status = 409
    message = "当前状态不允许该操作"


class PayloadTooLarge(ApiError):
    code = "FILE_TOO_LARGE"
    status = 413
    message = "文件超过大小上限"


class Unprocessable(ApiError):
    code = "IMPORT_PARSE_FAILED"
    status = 422
    message = "无法解析该文件"


class ServiceUnavailable(ApiError):
    code = "INTERNAL_ERROR"
    status = 503
    message = "服务暂不可用"


# 业务专用错误（与 docs/api-v1-reference.md 第 12 节错误码总表一一对应）
class SessionFinished(Conflict):
    code = "SESSION_FINISHED"
    message = "该练习已结束"


class SessionExpired(Conflict):
    code = "SESSION_EXPIRED"
    message = "该练习已超过 2 小时，请重新开始"


class EmptyPool(Conflict):
    code = "EMPTY_POOL"
    message = "该范围内没有可练习的词"


class AudioNotAvailable(ApiError):
    code = "AUDIO_NOT_AVAILABLE"
    status = 404
    message = "该词暂无音频"


def bad_request(field: str, message: str) -> ValidationFailed:
    """单字段校验失败的快捷构造。"""
    return ValidationFailed(details=[{"field": field, "message": message}])
