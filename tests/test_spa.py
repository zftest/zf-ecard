"""SPA 静态托管的契约测试。

为什么这些细节值得单独测：
静态文件服务出问题的表现几乎都是"页面全白"或"控制台一个看不懂的语法错误"，
而不是一个明确的 500。等真出问题再来查，光"到底是路由没配、还是产物没构建、
还是 MIME 类型不对"就要花很久。所以把每种情况都钉死。
"""
from __future__ import annotations

import os

import pytest

from app import create_app


@pytest.fixture()
def dist_dir(tmp_path):
    """造一个假的构建产物目录：index.html + assets/app.js。"""
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(
        '<!DOCTYPE html><html><body><div id="app"></div>'
        '<script type="module" src="/app/assets/app.js"></script></body></html>',
        encoding="utf-8",
    )
    (root / "assets" / "app.js").write_text("console.log('spa')\n", encoding="utf-8")
    return root


@pytest.fixture()
def spa_app(dist_dir):
    return create_app({"SPA_DIST": str(dist_dir), "TESTING": True})


@pytest.fixture()
def spa_client(spa_app):
    return spa_app.test_client()


def test_entry_returns_index_html(spa_client):
    response = spa_client.get("/app/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b'id="app"' in response.data
    # index.html 不能缓存：否则发版后用户拿到的还是旧 html，引用着已删除的 hash 资源
    assert "no-cache" in response.headers["Cache-Control"]


def test_hashed_asset_is_cacheable(spa_client):
    response = spa_client.get("/app/assets/app.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type
    # 产物文件名带 hash，内容变了文件名就变，可以永久缓存
    assert "immutable" in response.headers["Cache-Control"]
    assert "max-age=31536000" in response.headers["Cache-Control"]


def test_client_route_falls_back_to_index(spa_client):
    """history 模式：刷新 /app/words 时必须返回 index.html，让前端路由接管。"""
    for path in ("/app/words", "/app/wrongbook", "/app/practice"):
        response = spa_client.get(path)
        assert response.status_code == 200, path
        assert b'id="app"' in response.data, path


def test_missing_asset_is_404_not_index(spa_client):
    """缺失的 .js 必须真 404。

    如果回落成 index.html，浏览器会拿到一段 HTML 当 JS 执行，
    报 `Uncaught SyntaxError: Unexpected token '<'` ——
    这个报错和真正的原因（文件没打包进去）完全不像。
    """
    response = spa_client.get("/app/assets/not-exist.js")
    assert response.status_code == 404
    assert b'id="app"' not in response.data


@pytest.mark.parametrize(
    "path",
    [
        "/app/assets/x.css",
        "/app/assets/x.map",
        "/app/assets/x.woff2",
        "/app/assets/x.png",
    ],
)
def test_missing_static_assets_are_404(spa_client, path):
    assert spa_client.get(path).status_code == 404


def test_no_trailing_slash_redirects(spa_client):
    """`/app` 要跳到 `/app/`。

    不跳的话，相对路径资源会解析到 `/assets/` 而不是 `/app/assets/`，
    整个页面样式脚本全 404。
    """
    response = spa_client.get("/app")
    assert response.status_code in (301, 308)
    assert response.headers["Location"].endswith("/app/")


def test_index_when_dist_missing(tmp_path):
    """产物不存在时给说明页，不是 404。

    新机器 clone 下来还没 npm run build，这时用户看到 404 会以为路由配错了。
    """
    application = create_app(
        {"SPA_DIST": str(tmp_path / "no-such-dist"), "TESTING": True}
    )
    client = application.test_client()

    response = client.get("/app/")
    assert response.status_code == 200
    assert "前端还没有构建" in response.get_data(as_text=True)
    # 必须写清楚要跑什么命令，否则用户只能来问人
    assert "npm run build" in response.get_data(as_text=True)


def test_path_traversal_is_blocked(spa_client):
    """不能靠 ../ 读到 dist 之外的文件。

    显式要求 404 而不是"只要没泄露源码就行"：
    若只是回落到 index.html（200），扫描器与日志里看不出有人在试穿越，
    而这类请求 100% 是恶意或脚本出错，没有一个是正常用户发出来的。
    """
    for path in ("/app/../app.py", "/app/assets/../../app.py", "/app/%2e%2e/app.py"):
        response = spa_client.get(path)
        assert response.status_code == 404, path
        assert b"Flask(" not in response.data, path


def test_legacy_and_api_routes_still_work(spa_app):
    """SPA 的兜底规则不能吃掉旧路由与 /api/v1。"""
    client = spa_app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/health").status_code in (200, 503)


def test_spa_dist_is_configurable(spa_app, dist_dir):
    """产物目录走配置，测试才能不碰真实的 frontend/dist。"""
    assert spa_app.config["SPA_DIST"] == str(dist_dir)
    assert os.path.isfile(os.path.join(spa_app.config["SPA_DIST"], "index.html"))
