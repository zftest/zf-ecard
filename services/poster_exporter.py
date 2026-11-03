"""
使用 Playwright 将海报页面截图导出为 PNG

修复说明：
  - 不再使用 file:/// 本地路径（会导致 CSS/字体全部丢失）
  - 改为直接访问 Flask 的 HTTP URL，保证样式完整渲染
  - 截图前隐藏底部操作栏（下载/重新生成按钮）
  - 使用 clip 精准截取海报区域，避免截到底部工具栏
"""
import os
from playwright.sync_api import sync_playwright
from config import POSTER_OUTPUT_DIR, POSTER_WIDTH


def export_poster_to_png(poster_url, output_filename=None):
    """
    通过 HTTP URL 访问海报页面并截图

    参数：
        poster_url: Flask 海报页面的完整 HTTP URL
                    例如 http://127.0.0.1:5000/poster/abc123?export=1
        output_filename: 输出文件名（不含路径）

    返回：
        str: 生成的 PNG 文件绝对路径
    """
    if output_filename is None:
        import time
        output_filename = f"poster_{int(time.time())}.png"

    os.makedirs(POSTER_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.abspath(os.path.join(POSTER_OUTPUT_DIR, output_filename))

    print(f"[Exporter] 开始截图 URL：{poster_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--font-render-hinting=none"]
        )

        page = browser.new_page(
            viewport={"width": POSTER_WIDTH, "height": 900},
            device_scale_factor=2    # 2倍分辨率，图片更清晰
        )

        # 直接访问 Flask HTTP 页面（带 export=1 隐藏按钮）
        page.goto(poster_url, wait_until="networkidle", timeout=60000)

        # 等待字体和动画完全渲染
        page.wait_for_timeout(2000)

        # 注入 JS：隐藏底部操作栏 + 确保 overflow 可见
        page.evaluate("""
            () => {
                const toolbar = document.querySelector('.poster-toolbar');
                if (toolbar) toolbar.style.display = 'none';
                const wrapper = document.querySelector('.poster-wrapper');
                if (wrapper) {
                    wrapper.style.overflow = 'visible';
                    wrapper.style.paddingBottom = '40px';
                }
            }
        """)

        page.wait_for_timeout(500)

        # 获取海报区域真实高度，精准截图
        poster_box = page.evaluate("""
            () => {
                const el = document.querySelector('.poster-wrapper');
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
            }
        """)

        if poster_box and poster_box["height"] > 100:
            page.screenshot(
                path=output_path,
                type="png",
                clip={
                    "x": max(0, poster_box["x"] - 10),
                    "y": max(0, poster_box["y"] - 10),
                    "width": poster_box["width"] + 20,
                    "height": poster_box["height"] + 20
                }
            )
            print(f"[Exporter] 精准截图完成，区域高度={poster_box['height']}px")
        else:
            # 降级：全页截图
            page.screenshot(path=output_path, full_page=True, type="png")
            print("[Exporter] 降级为全页截图")

        browser.close()

    print(f"[Exporter] 截图保存至：{output_path}")
    return output_path
