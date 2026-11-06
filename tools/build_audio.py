"""批量生成单词发音（mp3），写入 data/audio 与 manifest。

为什么是离线工具，不做进接口：
    TTS 合成一次几百毫秒到几秒。放进请求链路里意味着第一个词要等、
    网络抖动整页卡住、并发几个词就排队。而这个操作**只做一次**，
    之后永远是读本地文件。所以合成在这里批跑，接口只负责发文件。

为什么用 edge-tts：
    - 环境实测：`piper-tts` 依赖 onnxruntime，在 Python 3.14 上没有可用包，
      装不上；edge-tts 依赖纯 Python，能装，输出就是 mp3。
    - 音质接近真人朗读，英式/美式都有对应音色。
    - 代价：**它是微软 Edge 的在线朗读服务**，需要联网，且只适合个人学习用途，
      不要用于任何商业场景。manifest 里会写明来源与用途，方便日后追溯。

幂等：已有文件的词默认跳过。想重生成加 `--overwrite`。
单个词失败不影响整批，最后汇总失败清单。

用法：

    # 先看计划，不生成（推荐第一步）
    python tools/build_audio.py --dry-run

    # 生成前 20 个词的英式+美式发音
    python tools/build_audio.py --limit 20

    # 只生成英音，全部重新合成
    python tools/build_audio.py --accent uk --overwrite

    # 换个音色
    python tools/build_audio.py --voice-uk en-GB-RyanNeural

依赖（未安装时脚本会给出提示，不会崩）：

    pip install edge-tts
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select  # noqa: E402

from core import audio as audio_module  # noqa: E402
from core.db import Database  # noqa: E402
from core.models import Word  # noqa: E402

# 默认音色。都是 neural 音色，朗读单词清晰度足够。
DEFAULT_VOICES = {
    "uk": "en-GB-SoniaNeural",
    "us": "en-US-AriaNeural",
}

PROVIDER = "edge-tts"
LICENSE_TEXT = (
    "Microsoft Edge TTS 在线服务生成；仅供个人学习使用，不得商用"
)


def collect_targets(db, accents: list[str], overwrite: bool, limit: int | None) -> list[dict]:
    """算出这一轮要生成哪些 (词, 口音)。"""
    with db.session() as session:
        words = session.scalars(select(Word).order_by(Word.id)).all()
        rows = [(word.id, word.spelling) for word in words]

    targets: list[dict] = []
    for word_id, spelling in rows:
        for accent in accents:
            if not overwrite and audio_module.find_audio(word_id, accent):
                continue
            targets.append({"word_id": word_id, "spelling": spelling, "accent": accent})

    if limit is not None:
        # 按词截断而不是按条截断：--limit 20 应该是 20 个词，不是 20 个文件
        allowed: list[int] = []
        for target in targets:
            if target["word_id"] not in allowed:
                if len(allowed) >= limit:
                    break
                allowed.append(target["word_id"])
        targets = [target for target in targets if target["word_id"] in allowed]

    return targets


async def _synthesize_all(targets: list[dict], args) -> tuple[int, int, list[str]]:
    """并发合成。返回 (成功数, 跳过数, 失败描述列表)。"""
    import edge_tts  # 延迟导入：没装依赖时只有真正要跑才会报错

    semaphore = asyncio.Semaphore(max(1, args.concurrency))
    stamp = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    failures: list[str] = []
    done = 0

    async def one(target: dict) -> None:
        nonlocal done
        word_id = target["word_id"]
        accent = target["accent"]
        voice = args.voice_uk if accent == "uk" else args.voice_us
        directory = os.path.join(audio_module.AUDIO_DIR, str(word_id))
        os.makedirs(directory, exist_ok=True)
        final_path = os.path.join(directory, f"{accent}.mp3")
        # 先写临时文件再替换：中途失败不会留下一个能被播出来的半截 mp3
        tmp_path = final_path + ".part"

        async with semaphore:
            try:
                await edge_tts.Communicate(
                    target["spelling"], voice, rate=args.rate
                ).save(tmp_path)
                if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                    raise RuntimeError("合成结果为空")
                os.replace(tmp_path, final_path)
                audio_module.record_manifest(
                    word_id,
                    accent,
                    ext="mp3",
                    source=PROVIDER,
                    license_text=LICENSE_TEXT,
                    size_bytes=os.path.getsize(final_path),
                    generated_at=stamp,
                )
                done += 1
                if not args.quiet:
                    print(f"  ok  {target['spelling']:<20} {accent}")
            except Exception as exc:  # noqa: BLE001 - 单条失败不该中断整批
                failures.append(f"{target['spelling']} ({accent}): {type(exc).__name__} {exc}")
                if os.path.exists(tmp_path):
                    # 清理自己刚写的半成品（只删本次生成的 .part，不碰任何已有文件）
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

    await asyncio.gather(*(one(target) for target in targets))
    return done, 0, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="批量生成单词发音")
    parser.add_argument("--db", default=None, help="数据库文件路径，默认 data/app.db")
    parser.add_argument(
        "--accent", default="uk,us", help="要生成的口音，英文逗号分隔，默认 uk,us"
    )
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 个词")
    parser.add_argument("--overwrite", action="store_true", help="已有文件也重新生成")
    parser.add_argument("--dry-run", action="store_true", help="只列计划，不生成")
    parser.add_argument("--concurrency", type=int, default=4, help="并发数，默认 4")
    parser.add_argument("--rate", default="+0%", help="语速调整，如 -20%%")
    parser.add_argument("--voice-uk", default=DEFAULT_VOICES["uk"], help="英式音色")
    parser.add_argument("--voice-us", default=DEFAULT_VOICES["us"], help="美式音色")
    parser.add_argument("--quiet", action="store_true", help="只打印汇总")
    args = parser.parse_args(argv)

    accents = [item.strip() for item in args.accent.split(",") if item.strip()]
    unknown = [item for item in accents if item not in audio_module.ACCENTS]
    if unknown:
        print(f"未知口音：{', '.join(unknown)}（只支持 uk / us）")
        return 2

    database = Database(args.db)
    print(f"数据库：{database.path}")
    print(f"音频目录：{audio_module.AUDIO_DIR}")
    print(f"口音：{', '.join(accents)}\n")

    targets = collect_targets(database, accents, args.overwrite, args.limit)
    total_words = len({target["word_id"] for target in targets})

    if not targets:
        print("没有需要生成的音频（全部已存在）。想重新生成请加 --overwrite")
        database.dispose()
        return 0

    print(f"计划生成：{total_words} 个词 / {len(targets)} 个文件")

    if args.dry_run:
        preview = targets[:10]
        for target in preview:
            print(f"  · {target['spelling']:<20} {target['accent']}")
        if len(targets) > len(preview):
            print(f"  … 另有 {len(targets) - len(preview)} 个文件")
        print("\n空跑结束，未生成任何文件（去掉 --dry-run 才会真正生成）")
        database.dispose()
        return 0

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("\n缺少依赖 edge-tts。请先执行：")
        print("    .venv\\Scripts\\python.exe -m pip install edge-tts")
        database.dispose()
        return 2

    os.makedirs(audio_module.AUDIO_DIR, exist_ok=True)
    done, skipped, failures = asyncio.run(_synthesize_all(targets, args))

    database.dispose()

    print(f"\n完成：成功 {done} 个，失败 {len(failures)} 个")
    if failures:
        print("失败明细（可单独重跑，已成功的会自动跳过）：")
        for item in failures:
            print(f"  ! {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
