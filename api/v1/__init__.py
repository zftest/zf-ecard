"""把 `/api/v1` 装到 Flask 应用上。

对外只有一个入口：`register_api_v1(app)`。

**所有钩子与错误处理都只在 `/api/v1` 范围内生效**，这是刻意的：
旧的知识卡页面、`/api/generate`、海报导出都跑在同一个 Flask 进程里，
一旦注册成全局钩子，旧页面的 404 会变成 JSON、旧接口的 HTML 错误页会消失，
属于「改着新功能、悄悄改坏旧功能」的典型。

实现方式：
    请求钩子  在 app 层注册，但用请求路径前缀守卫（因为 before_request 拿不到蓝图）
    错误处理  注册在蓝图上，天然只覆盖新接口，且不影响旧路由
"""
from __future__ import annotations

import logging
import time
import uuid

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from api.v1.blueprint import API_PREFIX, bp
from api.v1.errors import ApiError, MethodNotAllowed, NotFound, ValidationFailed

logger = logging.getLogger(__name__)

# 请求 ID 允许客户端自带的最大长度，防止有人塞一兆进去污染日志
MAX_REQUEST_ID_LEN = 64

# 蓝图错误处理是否已挂载（蓝图是模块级单例，只能挂一次）
_HANDLERS_INSTALLED = False


def _is_api_request() -> bool:
    return request.path.startswith(API_PREFIX)


def _request_id() -> str:
    return getattr(g, "request_id", "-")


def register_api_v1(app: Flask) -> None:
    """注册蓝图、请求钩子与错误处理。必须在 create_app 里调用一次。"""
    # 触发路由模块导入，否则装饰器不会执行、所有新接口都是 404
    from api.v1 import routes  # noqa: F401

    # 顺序很重要：Flask 3 在 register_blueprint 之后就"冻结"蓝图，
    # 之后再 @bp.errorhandler 会直接 AssertionError。必须先挂错误处理再注册。
    _install_error_handlers()
    app.register_blueprint(bp)
    _install_request_hooks(app)
    _install_routing_error_handlers(app)


# ─────────────────────────────────────────────────────────────
# 请求钩子：X-Request-Id + 访问日志
# ─────────────────────────────────────────────────────────────


def _install_request_hooks(app: Flask) -> None:
    @app.before_request
    def _assign_request_id() -> None:
        if not _is_api_request():
            return
        incoming = request.headers.get("X-Request-Id", "").strip()
        g.request_id = incoming[:MAX_REQUEST_ID_LEN] or uuid.uuid4().hex[:8]
        g.request_started = time.perf_counter()

    @app.after_request
    def _finalize(response):
        if not _is_api_request():
            return response

        request_id = _request_id()
        if request_id != "-":
            response.headers["X-Request-Id"] = request_id

        started = getattr(g, "request_started", None)
        duration_ms = round((time.perf_counter() - started) * 1000, 1) if started else None
        # 一条一行、键值明确，方便直接 grep 或喂给日志分析
        logger.info(
            "api method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


# ─────────────────────────────────────────────────────────────
# 路由阶段的 404 / 405
# ─────────────────────────────────────────────────────────────


def _install_routing_error_handlers(app: Flask) -> None:
    """兜住「根本没匹配到任何路由」的 404 和 405。

    为什么蓝图处理器不够：
        蓝图错误处理要求 Flask 已经知道这个请求属于哪个蓝图。
        但 `/api/v1/typo` 这种路径压根没匹配到任何 rule，路由阶段就失败了，
        蓝图无从谈起 —— 此时会走框架默认处理，返回 HTML 页面。
        结果就是：前端有时收到统一 JSON 错误，有时收到一坨 HTML，
        `response.json()` 直接抛 SyntaxError，真正的错误反被掩盖。

    非 /api/v1 的请求原样交回 Flask，旧页面的 404 表现一个字都不变。
    """

    @app.errorhandler(404)
    def _not_found(exc):
        if not _is_api_request():
            return exc
        return jsonify(NotFound("接口或资源不存在").to_dict(_request_id())), 404

    @app.errorhandler(405)
    def _method_not_allowed(exc):
        if not _is_api_request():
            return exc
        return (
            jsonify(MethodNotAllowed("请求方法不被支持").to_dict(_request_id())),
            405,
        )


# ─────────────────────────────────────────────────────────────
# 业务与框架异常：注册在蓝图上，旧路由完全不受影响
# ─────────────────────────────────────────────────────────────


def _install_error_handlers() -> None:
    # 蓝图是模块级单例：第二次 create_app（测试里很常见）再挂一次会抛
    # AssertionError，所以只挂一次。app 级请求钩子则每个 app 都要挂，不在此列。
    global _HANDLERS_INSTALLED
    if _HANDLERS_INSTALLED:
        return
    _HANDLERS_INSTALLED = True

    @bp.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        payload = exc.to_dict(_request_id())
        # 4xx 是客户端问题（warn），5xx 才是我们的问题（error）
        if exc.status >= 500:
            logger.error(
                "api_error code=%s path=%s request_id=%s message=%s",
                exc.code,
                request.path,
                _request_id(),
                exc.message,
            )
        else:
            logger.warning(
                "api_error code=%s path=%s request_id=%s message=%s",
                exc.code,
                request.path,
                _request_id(),
                exc.message,
            )
        return jsonify(payload), exc.status

    @bp.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        """把 404/405 这类框架级错误也包成统一结构。

        否则前端会遇到「有时是 JSON 错误、有时是 HTML 页面」的两种失败形态，
        解析器直接抛 SyntaxError，真正的错误信息反而被掩盖。
        """
        if exc.code == 404:
            wrapped: ApiError = NotFound("接口或资源不存在")
        elif exc.code == 405:
            wrapped = MethodNotAllowed("请求方法不被支持")
        elif exc.code == 400:
            wrapped = ValidationFailed("请求格式不合法")
        else:
            wrapped = ApiError(exc.description or "请求失败", status=exc.code or 500)
        return jsonify(wrapped.to_dict(_request_id())), wrapped.status

    @bp.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        """兜底：绝不把异常字符串返回给前端。"""
        logger.exception(
            "unhandled path=%s request_id=%s", request.path, _request_id()
        )
        return (
            jsonify(
                {
                    "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
                    "request_id": _request_id(),
                }
            ),
            500,
        )
