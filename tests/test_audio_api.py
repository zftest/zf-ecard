"""发音接口与音频探测测试（T6-1 / T6-3 / T6-4）。

守的六条：
1. 没有音频文件 → 404 + `AUDIO_NOT_AVAILABLE`，不是 200 空 body。
   前端要靠这个状态码决定「切设备语音」，200 会让 `<audio>` 静默失败。
2. 有文件 → 200，MIME 按**实际扩展名**给（mp3/ogg/wav 都要对），
   不能一律写死 `audio/mpeg`。
3. 缓存头必须是 `immutable`：二次播放零请求。
4. `X-Audio-Source` 用于排障，manifest 记了来源就报来源，没记就报 cache。
5. Range 请求要返回 206，否则拖动进度条得把整个文件重下。
6. manifest 损坏不能影响播放 —— 记账文件不该让功能 500。
"""
from __future__ import annotations

import json

import pytest

from core import audio as audio_module


@pytest.fixture()
def audio_root(tmp_path, monkeypatch):
    """把音频目录指到临时目录，避免读写真实的 data/audio。

    目录名特意与 conftest 里 api_app 用的 `audio` 区分开：
    同一个测试内 `tmp_path` 是同一个对象，两处用同名子目录会撞。
    """
    root = tmp_path / "audio-fixture"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(audio_module, "AUDIO_DIR", str(root))
    monkeypatch.setattr(audio_module, "MANIFEST_PATH", str(root / "manifest.json"))
    audio_module._manifest_cache["key"] = None
    return root


def _write(root, word_id: int, accent: str = "uk", ext: str = "mp3") -> bytes:
    directory = root / str(word_id)
    directory.mkdir(parents=True, exist_ok=True)
    payload = b"ID3\x03\x00fake-audio-bytes-for-test" + b"\x00" * 64
    (directory / f"{accent}.{ext}").write_bytes(payload)
    return payload


def _word_id(api) -> int:
    return api.get("/api/v1/words").get_json()["items"][0]["word_id"]


# ─────────────────────────────────────────────────────────────
# 探测逻辑
# ─────────────────────────────────────────────────────────────


def test_no_file_means_unavailable(audio_root):
    assert audio_module.find_audio(999) is None
    assert audio_module.has_any_audio(999) is False
    assert audio_module.audio_flags(999) == {"uk": False, "us": False}


def test_detect_mp3_and_ogg(audio_root):
    _write(audio_root, 1, "uk", "mp3")
    _write(audio_root, 1, "us", "ogg")

    assert audio_module.find_audio(1, "uk") == (
        str(audio_root / "1" / "uk.mp3"),
        "mp3",
    )
    assert audio_module.audio_flags(1) == {"uk": True, "us": True}


def test_mp3_wins_when_multiple_formats_exist(audio_root):
    """同一口音同时有 mp3 和 wav 时，优先 mp3（体积小、兼容性好）。"""
    _write(audio_root, 2, "uk", "wav")
    _write(audio_root, 2, "uk", "mp3")

    found = audio_module.find_audio(2, "uk")
    assert found is not None and found[1] == "mp3"


def test_manifest_survives_corrupt_json(audio_root):
    """manifest 写坏了，仍要能判断音频可用、能返回来源兜底值。"""
    _write(audio_root, 3, "uk", "mp3")
    (audio_root / "manifest.json").write_text("{ 这不是 json", encoding="utf-8")
    audio_module._manifest_cache["key"] = None

    assert audio_module.load_manifest()["entries"] == {}
    assert audio_module.find_audio(3, "uk") is not None
    assert audio_module.describe_source(3, "uk") == "cache"


def test_describe_source_reads_manifest(audio_root):
    _write(audio_root, 4, "uk", "mp3")
    audio_module.record_manifest(
        4, "uk", ext="mp3", source="edge-tts",
        license_text="Microsoft Edge TTS, 个人学习用途", size_bytes=100,
        generated_at="2026-11-06T12:00:00+08:00",
    )

    assert audio_module.describe_source(4, "uk") == "edge-tts"
    assert audio_module.describe_source(4, "us") == "cache", "没记录的口音要兜底"

    saved = json.loads((audio_root / "manifest.json").read_text(encoding="utf-8"))
    assert saved["entries"]["4"]["uk"]["license"].startswith("Microsoft")


# ─────────────────────────────────────────────────────────────
# 接口
# ─────────────────────────────────────────────────────────────


def test_audio_404_when_missing(api, audio_root):
    word_id = _word_id(api)

    resp = api.get(f"/api/v1/audio/{word_id}")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"]["code"] == "AUDIO_NOT_AVAILABLE"
    assert "设备语音" in body["error"]["message"], "404 文案要告诉前端可以降级"


def test_audio_returns_mp3_with_cache_headers(api, audio_root):
    word_id = _word_id(api)
    payload = _write(audio_root, word_id, "uk", "mp3")

    resp = api.get(f"/api/v1/audio/{word_id}")
    assert resp.status_code == 200
    assert resp.mimetype == "audio/mpeg"
    assert resp.data == payload
    assert "immutable" in resp.headers["Cache-Control"]
    assert "max-age=31536000" in resp.headers["Cache-Control"]
    assert resp.headers["X-Audio-Source"] == "cache"


def test_audio_returns_correct_mime_for_ogg(api, audio_root):
    """换成 ogg 也要能播 —— 不能因为写死 audio/mpeg 而静默失败。"""
    word_id = _word_id(api)
    _write(audio_root, word_id, "uk", "ogg")

    resp = api.get(f"/api/v1/audio/{word_id}")
    assert resp.status_code == 200
    assert resp.mimetype == "audio/ogg"


def test_accents_are_independent(api, audio_root):
    """只有英音时，请求美音必须 404，不能拿英音顶替。"""
    word_id = _word_id(api)
    _write(audio_root, word_id, "uk", "mp3")

    assert api.get(f"/api/v1/audio/{word_id}?accent=uk").status_code == 200
    resp = api.get(f"/api/v1/audio/{word_id}?accent=us")
    assert resp.status_code == 404
    assert "美式" in resp.get_json()["error"]["message"]


def test_invalid_accent_returns_400(api, audio_root):
    word_id = _word_id(api)

    resp = api.get(f"/api/v1/audio/{word_id}?accent=au")
    assert resp.status_code == 400
    detail = resp.get_json()["error"]["details"][0]
    assert detail["field"] == "accent"


def test_audio_supports_range_requests(api, audio_root):
    """拖动进度条只取需要的字节，否则每次拖都要重下整个文件。"""
    word_id = _word_id(api)
    _write(audio_root, word_id, "uk", "mp3")

    resp = api.get(f"/api/v1/audio/{word_id}", headers={"Range": "bytes=0-9"})
    assert resp.status_code == 206
    assert len(resp.data) == 10
    assert resp.headers["Content-Range"].startswith("bytes 0-9/")


def test_audio_word_does_not_need_to_exist(api, audio_root):
    """不存在的 word_id 也返 404 AUDIO_NOT_AVAILABLE。

    对前端来说「词不存在」和「词没音频」的处理方式完全一样（切设备语音），
    分成两个状态码只会让前端多写一个没有用的分支。
    """
    resp = api.get("/api/v1/audio/999999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "AUDIO_NOT_AVAILABLE"
