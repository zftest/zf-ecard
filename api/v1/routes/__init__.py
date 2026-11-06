"""路由模块集合。

这样集中 import 的意义：Flask 的蓝图路由是靠「装饰器执行时注册」的，
模块不被 import 就等于路由不存在。分散在各处手动 import 迟早会漏一个，
表现是接口 404，而代码看着完全正常。
"""
from api.v1.routes import (  # noqa: F401
    audio,
    catalog,
    health,
    learners,
    practice,
    words,
    wrongbook,
)
