"""音频文件位置、格式探测与来源清单。

为什么放在 core 而不是 presenter 里：
    「有没有音频」既被接口层用来决定 `audio_available`，
    也被练习层用来决定要不要给前端发"音频未生成"的降级提示。
    如果放在 api 层，core 就得反过来 import api —— 依赖方向倒挂，
    以后想把 core 单独打包成命令行工具时立刻崩。

判定方式是**看文件在不在**，不是读一个全局开关，也不是查 manifest：
    manifest 是记账用的（来源与许可），可能没生成、可能落后于文件；
    而文件存在就该能播。把"能不能播"和"记没记账"分开，
    才不会出现「文件明明在，因为 manifest 没更新而播不出声」。

为什么不硬编码 mp3：
    音频来源可以换（edge-tts 出 mp3、Wikimedia 是 ogg、Windows SAPI 是 wav）。
    接口按实际文件的扩展名返回对应 MIME，换来源就不用改接口和前端。
    如果只认 mp3，某天换了来源，接口会静默 404，而文件就在磁盘上。
"""
from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
MANIFEST_PATH = os.path.join(AUDIO_DIR, "manifest.json")

# 按优先级探测：同一词同一口音有多个格式时，优先返回体积小、兼容性好的
AUDIO_EXTS: tuple[str, ...] = ("mp3", "m4a", "ogg", "wav")

MIME_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
}

ACCENTS: tuple[str, ...] = ("uk", "us")

# manifest 读取缓存。接口会被高频调用（每个词每口音一次），
# 每次读一遍 JSON 属于纯粹的浪费。用 (mtime, size) 判断是否失效，
# 这样构建工具写完新 manifest 后，下一个请求就能看到。
_manifest_cache: dict[str, object] = {"key": None, "data": {}}


def audio_dir(word_id: int) -> str:
    return os.path.join(AUDIO_DIR, str(word_id))


def find_audio(word_id: int, accent: str = "uk") -> tuple[str, str] | None:
    """返回 (文件路径, 扩展名)，没有则 None。"""
    directory = audio_dir(word_id)
    for ext in AUDIO_EXTS:
        path = os.path.join(directory, f"{accent}.{ext}")
        if os.path.exists(path):
            return path, ext
    return None


def audio_path(word_id: int, accent: str = "uk") -> str:
    """默认写入路径（构建工具用）。只看 mp3，不看已存在的其它格式。"""
    return os.path.join(audio_dir(word_id), f"{accent}.mp3")


def mime_for(ext: str) -> str:
    return MIME_TYPES.get(ext, "application/octet-stream")


def audio_flags(word_id: int) -> dict[str, bool]:
    """{uk: bool, us: bool}，是否已有对应口音的音频文件。"""
    return {accent: find_audio(word_id, accent) is not None for accent in ACCENTS}


def has_any_audio(word_id: int) -> bool:
    return any(audio_flags(word_id).values())


# ─────────────────────────────────────────────────────────────
# manifest：只用来记账（来源 / 许可 / 生成时间）
# ─────────────────────────────────────────────────────────────


def load_manifest() -> dict:
    """读 manifest。文件不存在或损坏时返回空结构，不抛异常。

    为什么吞掉损坏：
        发音接口的首要职责是"能播就播"。一个 manifest 的 JSON 写坏了
        不该让整个发音功能 500 —— 那是记账文件，不是运行必需。
    """
    try:
        stat = os.stat(MANIFEST_PATH)
    except OSError:
        return {"version": 1, "entries": {}}

    key = (stat.st_mtime_ns, stat.st_size)
    if _manifest_cache["key"] == key:
        return _manifest_cache["data"]  # type: ignore[return-value]

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("manifest 顶层必须是对象")
        data.setdefault("entries", {})
    except (OSError, ValueError):
        data = {"version": 1, "entries": {}}

    _manifest_cache["key"] = key
    _manifest_cache["data"] = data
    return data


def manifest_entry(word_id: int, accent: str = "uk") -> dict | None:
    """某个词某个口音的来源记录；没记录返回 None。"""
    entries = load_manifest().get("entries", {})
    return (entries.get(str(word_id)) or {}).get(accent)


def describe_source(word_id: int, accent: str = "uk") -> str:
    """`X-Audio-Source` 头的值。

    cache  —— 有文件但 manifest 里没记来源（老数据 / 手工放进去的）
    其它   —— manifest 里记的 provider 名（edge-tts / wikimedia / piper …）

    这个头的作用是排障：用户反馈"听着不像英音"时，
    不用翻磁盘就能知道这条音频是哪来的。
    """
    entry = manifest_entry(word_id, accent)
    if entry and entry.get("source"):
        return str(entry["source"])
    return "cache"


def record_manifest(
    word_id: int,
    accent: str,
    *,
    ext: str,
    source: str,
    license_text: str,
    size_bytes: int,
    generated_at: str,
) -> None:
    """写入一条来源记录（构建工具调用）。整份写回，不做增量合并写。"""
    data = load_manifest()
    entries = data.setdefault("entries", {})
    word_entry = entries.setdefault(str(word_id), {})
    word_entry[accent] = {
        "file": f"{word_id}/{accent}.{ext}",
        "ext": ext,
        "source": source,
        "license": license_text,
        "bytes": size_bytes,
        "generated_at": generated_at,
    }

    os.makedirs(AUDIO_DIR, exist_ok=True)
    tmp_path = MANIFEST_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    # 先写临时文件再替换：中途被打断也不会留下半截 JSON
    os.replace(tmp_path, MANIFEST_PATH)
    _manifest_cache["key"] = None  # 强制下次重读
