"""发音接口：把一个词的 mp3/ogg/wav 直接流给浏览器。

三个刻意的选择：

1. **接口只读本地文件，绝不在这里联网合成。**
   TTS 合成一次要几百毫秒到几秒，放进请求链路里意味着：
   第一次点发音要等，网络抖动时整个页面卡住，并发几个词就排队。
   所以合成放在离线工具（`tools/build_audio.py`）里批跑，
   接口只做「有文件就发，没文件就 404」—— 永远在毫秒级返回。

2. **按实际扩展名返回对应 MIME，不硬编码 `audio/mpeg`。**
   来源可能换（edge-tts 出 mp3、Wikimedia 是 ogg、Windows SAPI 是 wav）。
   硬编码 mp3 的话，某天换成 ogg 播放器会直接拒绝播放，
   而文件明明就在磁盘上，排查起来很费劲。

3. **没有音频返回 404，不是 200 + 空 body。**
   前端要靠状态码决定是否降级到设备语音。返回 200 空 body 的话，
   `<audio>` 会静默失败，用户点了没反应，也不知道是网络问题还是没音频。
"""
from __future__ import annotations

from flask import request, send_file

from api.v1.blueprint import bp
from api.v1.errors import AudioNotAvailable
from api.v1.params import AudioQuery, parse_query
from core.audio import describe_source, find_audio, mime_for

# 一年。音频内容永远不变（换了来源就换文件），可以安全地永久缓存
CACHE_SECONDS = 31536000


@bp.get("/audio/<int:word_id>")
def get_word_audio(word_id: int):
    """返回单词指定口音的音频流。

    `conditional=True` 打开 Range 支持：浏览器拖动播放进度条时
    只取需要的字节，而不是把整个文件重新下一遍。
    """
    params = parse_query(AudioQuery, request.args)
    found = find_audio(word_id, params.accent)
    if found is None:
        raise AudioNotAvailable(
            f"该词暂无{('英式' if params.accent == 'uk' else '美式')}发音，可改用设备语音"
        )

    path, ext = found
    response = send_file(
        path,
        mimetype=mime_for(ext),
        conditional=True,
        max_age=CACHE_SECONDS,
    )
    # 显式写 immutable：有了它，浏览器刷新页面时连条件请求都不发，
    # 二次播放是真正的零请求
    response.headers["Cache-Control"] = f"public, max-age={CACHE_SECONDS}, immutable"
    response.headers["X-Audio-Source"] = describe_source(word_id, params.accent)
    return response
