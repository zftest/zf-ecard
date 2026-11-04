"""旧功能契约测试 —— 7 条兼容红线。

为什么要有这个文件：
本项目的改造策略是「旧 Flask/Jinja 功能一行不动，新增功能走 /api/v1 + Vue SPA」。
但"没改坏"这件事不能靠人眼保证。改造过程中最容易出的事故是：
  · 把旧路由搬进 Blueprint → endpoint 名变成 legacy.show_poster
    → url_for("show_poster") 在**运行期**才解析 → 用户提交表单时才 500
  · 顺手统一端口，只改了一处 → PNG 导出访问错误端口 → 必然失败
  · 顺手把异常消息改成 str(e) → 泄露服务器路径

这些事故都不会在启动时报错。所以把它们固化成断言。
任何一次改造后，本文件必须保持全绿。
"""
import os
import re

from flask import url_for

from conftest import VALID_FORM


# ══════════════════════════════════════════════════════════════
# 红线 1：旧页面路由全部可用
# ══════════════════════════════════════════════════════════════

def test_index_page_available(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["Content-Type"]


def test_loading_page_available(client):
    assert client.get("/loading").status_code == 200


def test_poster_page_available(client, poster_id):
    resp = client.get(f"/poster/{poster_id}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["Content-Type"]


def test_poster_demo_page_available(client, poster_id):
    resp = client.get(f"/poster-demo/{poster_id}")
    assert resp.status_code == 200


def test_poster_page_404_when_cache_missing(client):
    """缓存不存在时仍是原来的纯文本 404，不是 JSON。"""
    resp = client.get("/poster/doesnotexist")
    assert resp.status_code == 404
    assert "海报已过期" in resp.get_data(as_text=True)


# ══════════════════════════════════════════════════════════════
# 红线 2：POST /api/generate 返回结构不变
# ══════════════════════════════════════════════════════════════

def test_api_generate_response_shape(client, fake_ai):
    resp = client.post("/api/generate", json=VALID_FORM)
    assert resp.status_code == 200

    data = resp.get_json()
    # 只允许有 poster_id 一个键，且为 12 位小写 hex
    assert set(data.keys()) == {"poster_id"}
    assert re.fullmatch(r"[0-9a-f]{12}", data["poster_id"])


def test_api_generate_passes_all_fields(client, fake_ai):
    client.post("/api/generate", json=VALID_FORM)
    assert fake_ai["args"] == {**VALID_FORM, "stage": "小学"}


def test_api_generate_default_stage_is_primary_school(client, fake_ai):
    client.post("/api/generate", json=VALID_FORM)
    assert fake_ai["args"]["stage"] == "小学"


def test_api_generate_accepts_custom_stage(client, fake_ai):
    client.post("/api/generate", json={**VALID_FORM, "stage": "初中"})
    assert fake_ai["args"]["stage"] == "初中"


def test_api_generate_rejects_incomplete_form(client):
    resp = client.post("/api/generate", json={"grade": "三年级"})
    assert resp.status_code == 400
    assert set(resp.get_json().keys()) == {"error"}


def test_api_generate_trims_whitespace(client, fake_ai):
    """新增的输入清洗不应改变正常输入的语义。"""
    client.post("/api/generate", json={**VALID_FORM, "grade": "  三年级  "})
    assert fake_ai["args"]["grade"] == "三年级"


# ══════════════════════════════════════════════════════════════
# 红线 3：异常不得把堆栈/路径/密钥回传前端
# ══════════════════════════════════════════════════════════════

def test_api_generate_does_not_leak_exception(client, monkeypatch):
    import app as app_module

    def boom(*args, **kwargs):
        raise RuntimeError("sk-should-not-leak /d/内部/路径/Object at 0x1")

    monkeypatch.setattr(app_module, "generate_knowledge_card", boom)

    resp = client.post("/api/generate", json=VALID_FORM)
    assert resp.status_code == 500

    body = resp.get_data(as_text=True)
    assert "sk-should-not-leak" not in body
    assert "内部/路径" not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
    # 仍是 {"error": "..."} 结构
    assert set(resp.get_json().keys()) == {"error"}


def test_export_does_not_leak_exception(client, poster_id, monkeypatch):
    import app as app_module

    def boom(*args, **kwargs):
        raise RuntimeError("sk-should-not-leak 内部路径")

    monkeypatch.setattr(app_module, "export_poster_to_png", boom)

    resp = client.get(f"/api/export/{poster_id}")
    assert resp.status_code == 500
    body = resp.get_data(as_text=True)
    assert "sk-should-not-leak" not in body
    assert "内部路径" not in body


# ══════════════════════════════════════════════════════════════
# 红线 4：POST /generate 仍 302 到 /poster/<id>
# ══════════════════════════════════════════════════════════════

def test_form_generate_redirects_to_poster(client, fake_ai):
    resp = client.post("/generate", data=VALID_FORM)
    assert resp.status_code == 302

    location = resp.headers["Location"]
    assert re.search(r"/poster/[0-9a-f]{12}$", location)

    # 跟随跳转后能正常渲染海报页
    assert client.get(location).status_code == 200


def test_form_generate_rejects_incomplete(client):
    resp = client.post("/generate", data={"grade": "三年级"})
    assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════
# 红线 5：GET /api/export/<id> 仍返回 PNG 附件
# ══════════════════════════════════════════════════════════════

def test_export_returns_png_attachment(client, poster_id, fake_exporter):
    resp = client.get(f"/api/export/{poster_id}")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "image/png"
    assert "attachment" in resp.headers["Content-Disposition"]


def test_export_404_when_cache_missing(client, fake_exporter):
    resp = client.get("/api/export/doesnotexist")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "海报数据不存在，请重新生成"


def test_export_url_uses_configured_base_url(client, poster_id, fake_exporter):
    """端口统一的核心验证：导出目标地址必须取自配置，而不是硬编码 5000。"""
    client.get(f"/api/export/{poster_id}")
    base_url = client.application.config["POSTER_BASE_URL"]
    assert fake_exporter["poster_url"] == f"{base_url}/poster/{poster_id}?export=1"
    assert fake_exporter["output_filename"] == f"poster_{poster_id}.png"


# ══════════════════════════════════════════════════════════════
# 红线 6：缓存目录与文件名规则不变
# ══════════════════════════════════════════════════════════════

def test_cache_file_naming_unchanged(client, poster_id):
    cache_dir = client.application.config["CACHE_DIR"]
    path = os.path.join(cache_dir, f"{poster_id}.json")
    assert os.path.exists(path)


def test_cache_json_is_readable_utf8(client, app, poster_id):
    import json

    cache_dir = app.config["CACHE_DIR"]
    with open(os.path.join(cache_dir, f"{poster_id}.json"), encoding="utf-8") as f:
        data = json.load(f)
    assert "meta" in data and "cards" in data


def test_default_cache_dir_is_output_cache():
    """默认缓存目录必须仍是 output/cache，不能因为改造而漂移。"""
    import app as app_module

    assert app_module.DEFAULT_CACHE_DIR.endswith(os.path.join("output", "cache"))


# ══════════════════════════════════════════════════════════════
# 红线 7：endpoint 名不变 —— 这是「不搬 Blueprint」的守护测试
# ══════════════════════════════════════════════════════════════

def test_endpoint_names_unchanged(app):
    """七个 endpoint 必须仍可被 url_for 按原名解析。

    若有人把旧路由搬进 Blueprint，endpoint 会变成 "legacy.show_poster"，
    这个测试会立刻失败 —— 而不是等到用户提交表单时才 500。
    """
    with app.test_request_context():
        assert url_for("index") == "/"
        assert url_for("loading") == "/loading"
        assert url_for("show_poster", poster_id="abc123") == "/poster/abc123"
        assert url_for("show_poster_demo", poster_id="abc123") == "/poster-demo/abc123"
        assert url_for("api_generate") == "/api/generate"
        assert url_for("generate_poster_form") == "/generate"
        assert url_for("api_export", poster_id="abc123") == "/api/export/abc123"


def test_route_count_is_seven(app):
    """旧路由数量固定为 7。新增功能必须走 /api/v1，不得往这里塞。

    /api/v1 的路由被显式排除，否则每加一个新接口这条断言就会红一次，
    最后一定会被人改成「== 14」「== 21」而失去意义。
    这里要守的是**旧接口不增不减**，不是"全站路由总数"。
    """
    legacy = [
        rule
        for rule in app.url_map.iter_rules()
        if not rule.rule.startswith("/static")
        and not rule.rule.startswith("/api/v1")
    ]
    assert len(legacy) == 7, [r.rule for r in legacy]


def test_api_v1_routes_are_namespaced(app):
    """新接口一律挂在 /api/v1 下，不许占用旧路由的命名空间。"""
    api_rules = [
        rule.rule for rule in app.url_map.iter_rules() if "/api/" in rule.rule
    ]
    new_api = [rule for rule in api_rules if rule.startswith("/api/v1")]
    legacy_api = [rule for rule in api_rules if not rule.startswith("/api/v1")]
    assert new_api, "应至少有一个 /api/v1 接口"
    # 旧 JSON 接口只有这两个，逐个写出来而不是数数量，谁多加了会立刻暴露
    assert sorted(legacy_api) == ["/api/export/<poster_id>", "/api/generate"]


# ══════════════════════════════════════════════════════════════
# 附加：核心 HTML 格式化函数行为不变
# ══════════════════════════════════════════════════════════════

def test_format_card_content_warning_block():
    import app as app_module

    html = app_module.format_card_content("【注意】复数要加 s")
    assert "warning-block" in html
    assert "复数要加 s" in html


def test_format_card_content_example_block():
    import app as app_module

    html = app_module.format_card_content("【典型例题】1+1=?\n答：2")
    assert "example-block" in html
    assert "example-ans" in html


def test_format_card_content_empty():
    import app as app_module

    assert app_module.format_card_content("") == ""
    assert app_module.format_card_content(None) == ""


# ══════════════════════════════════════════════════════════════
# 附加：密钥文件必须被忽略
# ══════════════════════════════════════════════════════════════

def test_config_py_is_gitignored():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".gitignore"), encoding="utf-8") as f:
        content = f.read()
    assert re.search(r"^config\.py\s*$", content, re.M), "config.py 必须留在 .gitignore 中"


def test_config_example_has_no_real_key():
    """示例配置里只能是占位符。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "config.example.py"), encoding="utf-8") as f:
        content = f.read()
    assert "sk-your-api-key-here" in content
    assert not re.search(r"sk-[0-9a-f]{20,}", content), "示例配置中出现了疑似真实密钥"
