"""把前端构建产物挂到 `/app/` 下。

为什么是 `/app/` 而不是根路径：
`/` 已经被旧的 Jinja 首页占用（那是不能动的东西，28 项契约测试在盯着它）。
新前端必须和旧功能共存，只能挪到子路径下。

三个容易踩的点，这里都处理了：

1. **base 必须对得上**。`vite.config.js` 里 `base: '/app/'`，
   产物里引用的是 `/app/assets/xxx.js`。两边不一致的表现是"页面全白、
   控制台无报错"，因为浏览器在 404 一个不存在的 JS 文件。

2. **history 模式要回落**。用户直接刷新 `/app/words` 时，服务端没有这个文件，
   必须返回 index.html 让前端路由接管。但如果**任何**不存在的路径都回 index.html，
   缺失的 `.js` 会返回一段 HTML，浏览器报 `Unexpected token '<'`——
   这个报错和真正的原因（文件没打包进去）完全不像，能查半天。
   所以带资源后缀的请求找不到就老实 404。

3. **dist 不存在时不能白屏**。新机器 clone 下来还没 `npm run build`，
   这时访问 /app/ 如果只给一个 404，会让人以为路由配错了。
   这里直接返回一段说明，写清楚要跑什么命令。
"""
from __future__ import annotations

import os

from flask import Response, abort, current_app, redirect, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIST = os.path.join(BASE_DIR, "frontend", "dist")

# 这些后缀的请求一定是在要静态资源。
# 找不到就是真 404 —— 回落成 index.html 会把问题伪装成"语法错误"。
ASSET_EXTS = frozenset(
    {
        ".js",
        ".mjs",
        ".css",
        ".map",
        ".json",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
    }
)

# 产物带 hash，内容变了文件名就变，可以永久缓存；
# index.html 不能缓存，否则发版后用户拿到的还是旧的资源引用。
ASSET_CACHE = "public, max-age=31536000, immutable"
INDEX_CACHE = "no-cache, must-revalidate"

NOT_BUILT_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>前端尚未构建</title>
<style>
  body { margin:0; min-height:100vh; display:grid; place-items:center;
         background:#f4f1e9; color:#20241f;
         font-family:"Microsoft YaHei","PingFang SC",sans-serif; line-height:1.7; }
  .card { max-width:560px; padding:32px; background:#fcfaf4;
          border:1px solid #d7d4c9; border-radius:22px; }
  h1 { margin:0 0 12px; font-size:22px; }
  p { margin:0 0 16px; color:#676c63; font-size:14px; }
  pre { margin:0; padding:14px 16px; background:#eee9dd; border-radius:12px;
        font-family:Consolas,monospace; font-size:13px; overflow-x:auto; }
</style>
</head>
<body>
  <div class="card">
    <h1>前端还没有构建</h1>
    <p>这个地址提供的是 Vue 前端的构建产物，而 <code>frontend/dist/</code> 目前不存在。
       先构建一次，再刷新本页。</p>
    <pre>cd frontend
npm install
npm run build</pre>
    <p style="margin-top:16px">开发时也可以用 <code>npm run dev</code>，
       访问 http://127.0.0.1:5173 ，那里有热更新，不用每次构建。</p>
  </div>
</body>
</html>
"""


def _dist_dir(app=None) -> str:
    """允许测试或部署通过配置覆盖产物目录。

    显式接受 app 参数：注册阶段（create_app 里）还没有请求上下文，
    这时拿不到 current_app，直接访问会抛 "Working outside of application context"。
    """
    config = (app or current_app).config
    return config.get("SPA_DIST") or DEFAULT_DIST


def _looks_like_traversal(path: str) -> bool:
    """路径里有没有想往上跳的段。

    `send_from_directory` 内部用 `safe_join` 已经挡住了真正的穿越，
    这里再加一道不是因为不信任它，而是因为**行为要明确**：
    没有这道检查，`/app/../app.py` 会命中兜底规则返回 index.html（200），
    看上去"正常"，实际上是拿一个畸形请求换了一段 HTML。
    直接 404 才能让扫描器和日志一眼看出有人在试。
    """
    normalized = path.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    return any(part == ".." for part in normalized.split("/"))


def _serve(path: str) -> Response:
    dist = _dist_dir()

    if not os.path.isfile(os.path.join(dist, "index.html")):
        return Response(NOT_BUILT_PAGE, mimetype="text/html")

    if path and _looks_like_traversal(path):
        abort(404)

    if path:
        # send_from_directory 内部用 safe_join，已经挡住了 ../ 穿越，
        # 不需要自己再拼 normpath 检查一遍（多写一遍反而容易写漏）
        if os.path.isfile(os.path.join(dist, path)):
            response = send_from_directory(dist, path, max_age=31536000)
            response.headers["Cache-Control"] = ASSET_CACHE
            return response

        # 要资源却没有 -> 真 404，不回落
        if os.path.splitext(path)[1].lower() in ASSET_EXTS:
            abort(404)

    # 其余情况一律交给前端路由（/app/words、/app/wrongbook 等）
    response = send_from_directory(dist, "index.html")
    response.headers["Cache-Control"] = INDEX_CACHE
    return response


def register_spa(app) -> None:
    """挂载 SPA。必须在所有蓝图注册完之后调用。"""

    @app.get("/app")
    def spa_redirect():
        # 不带尾斜杠的话，相对路径资源会解析到 /assets/ 而不是 /app/assets/
        return redirect("/app/", code=308)

    @app.get("/app/")
    @app.get("/app/<path:filename>")
    def spa(filename: str = ""):
        return _serve(filename)

    app.logger.info("SPA 挂载于 /app/（产物目录：%s）", _dist_dir(app))
