"""新功能内核层。

与旧 Flask/Jinja 代码完全隔离：这里不 import flask，也不 import services.*。
好处是核心逻辑（判题、调度、规范化）可以脱离 Web 层单测，
这也是 B4 敢先写测试再写实现的前提。
"""
