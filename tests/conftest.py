"""pytest 公共 fixture。

设计要点：
1. 使用 create_app() 创建**独立实例**，缓存目录注入到 tmp_path，
   绝不污染真实的 output/cache。
2. DeepSeek 与 Playwright 全部打桩 —— 测试不依赖网络，也不启动浏览器。
"""
import os
import sys

import pytest

# 保证能 `import app`（项目根目录加入 sys.path）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app as app_module  # noqa: E402
from services.deepseek_client import get_subject_cards, get_subject_info  # noqa: E402


# 一张结构完整的最小知识卡。
# meta 直接复用服务里的主题/卡片标题定义，避免测试数据与真实返回结构漂移
# （poster.html 会读 data.meta.theme.primary，字段缺一个模板就报 UndefinedError）
def _build_sample_card(grade="三年级", subject="英语", book="上册",
                       publisher="人教版", unit_name="Unit 1", stage="小学"):
    info = get_subject_info(subject, stage)
    return {
        "meta": {
            "grade": grade,
            "subject": subject,
            "book": book,
            "publisher": publisher,
            "unit_name": unit_name,
            "stage": stage,
            "poster_title": f"{grade}{book}·{subject}·{unit_name}",
            "theme": info["theme"],
            "card_titles": get_subject_cards(subject, stage),
        },
        "cards": [
            {
                "title": info["cards"][0] if info["cards"] else "核心词汇",
                "content": "1. apple\n2. banana\n\n【注意】复数要加 s",
                "active": True,
                "class": "card-primary",
            }
        ],
    }


SAMPLE_CARD = _build_sample_card()

VALID_FORM = {
    "grade": "三年级",
    "subject": "英语",
    "book": "上册",
    "publisher": "人教版",
    "unit_name": "Unit 1",
}


@pytest.fixture()
def app(tmp_path):
    """独立应用实例，缓存目录指向临时目录。"""
    return app_module.create_app(
        {
            "TESTING": True,
            "CACHE_DIR": str(tmp_path / "cache"),
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def fake_ai(monkeypatch):
    """把 DeepSeek 调用替换为固定返回，并记录实际收到的参数。"""
    state = {}

    def _fake(grade, subject, book, publisher, unit_name, stage="小学"):
        state["args"] = {
            "grade": grade,
            "subject": subject,
            "book": book,
            "publisher": publisher,
            "unit_name": unit_name,
            "stage": stage,
        }
        # 用实际入参构造 meta，保证 poster 页拿到的信息与请求一致
        return _build_sample_card(**state["args"])

    monkeypatch.setattr(app_module, "generate_knowledge_card", _fake)
    return state


@pytest.fixture()
def fake_exporter(monkeypatch, tmp_path):
    """把 Playwright 截图替换为写一个假 PNG，避免测试依赖浏览器。"""
    state = {}

    def _fake(poster_url, output_filename=None):
        state["poster_url"] = poster_url
        state["output_filename"] = output_filename
        path = tmp_path / (output_filename or "poster.png")
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake-png-for-test")
        return str(path)

    monkeypatch.setattr(app_module, "export_poster_to_png", _fake)
    return state


@pytest.fixture()
def poster_id(client, fake_ai):
    """生成一张海报并返回它的 poster_id，供海报页/导出接口复用。"""
    resp = client.post("/api/generate", json=VALID_FORM)
    assert resp.status_code == 200
    return resp.get_json()["poster_id"]


# ─────────────────────────────────────────────────────────────
# 数据层 fixture
# ─────────────────────────────────────────────────────────────


@pytest.fixture()
def db(tmp_path):
    """每个测试一个全新的临时 SQLite，跑完即弃。

    这里用 create_all 而不是 alembic：单元测试要快，且不该依赖迁移文件。
    「迁移脚本与模型是否一致」由 tests/test_migrations.py 单独把关，
    两者分工明确，不会因为走了 create_all 就漏掉迁移的一致性。
    """
    from core.db import Database

    database = Database(str(tmp_path / "test.db"))
    database.create_all()
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture()
def seeded_db(db):
    """导入 data/seed 下的样例词库，供练习/统计相关测试使用。"""
    from tools.load_seed import (
        DEFAULT_UNITS_CSV,
        DEFAULT_WORDS_CSV,
        load_units,
        load_words,
        read_csv,
    )

    with db.session() as session:
        unit_index, _ = load_units(session, read_csv(DEFAULT_UNITS_CSV))
        load_words(session, read_csv(DEFAULT_WORDS_CSV), unit_index, "上册")
    return db
