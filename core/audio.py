"""音频文件位置与就绪状态。

为什么放在 core 而不是 presenter 里：
    「有没有音频」既被接口层用来决定 `audio_available`，
    也被练习层用来决定要不要给前端发"音频未生成"的降级提示。
    如果放在 api 层，core 就得反过来 import api —— 依赖方向倒挂，
    以后想把 core 单独打包成命令行工具时立刻崩。

判定方式是**看文件在不在**，不是读一个全局开关：
    B6 把 mp3 灌进 data/audio 之后，接口与降级提示会自动跟着变，
    不需要回来改一行"记得把 false 改成 true"的代码。
"""
from __future__ import annotations

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")

# MVP 统一 mp3（见 docs/word-source-and-pronunciation-plan.md）
AUDIO_EXT = "mp3"
ACCENTS: tuple[str, ...] = ("uk", "us")


def audio_path(word_id: int, accent: str = "uk") -> str:
    return os.path.join(AUDIO_DIR, str(word_id), f"{accent}.{AUDIO_EXT}")


def audio_flags(word_id: int) -> dict[str, bool]:
    """{uk: bool, us: bool}，是否已有对应口音的音频文件。"""
    return {accent: os.path.exists(audio_path(word_id, accent)) for accent in ACCENTS}


def has_any_audio(word_id: int) -> bool:
    return any(audio_flags(word_id).values())
