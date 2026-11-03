# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-your-api-key-here"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Flask 配置
SECRET_KEY = "poster-generator-secret-key-change-in-production"
DEBUG = True

# ─────────────────────────────────────────────────────────────
# 服务端口（唯一入口）
# 改这里即可，页面访问端口与 PNG 导出使用的内部地址会同步变化。
# 历史上这两个值分别硬编码在 app.py 的两处（海报 URL 与 app.run），
# 只改一处会导致 PNG 导出访问到错误端口而失败，因此统一收口到此处。
# ─────────────────────────────────────────────────────────────
import os

PORT = int(os.getenv("PORT", "5000"))

# PNG 导出时 Playwright 访问的内部地址。
# 默认与 PORT 保持一致；将来走 Nginx / HTTPS 反向代理时，
# 可单独设为对外域名，例如 "https://ecard.example.com"
POSTER_BASE_URL = os.getenv("POSTER_BASE_URL", f"http://127.0.0.1:{PORT}")

# 海报导出配置
POSTER_OUTPUT_DIR = "output"
POSTER_WIDTH = 1200   # 海报宽度 px
POSTER_PADDING = 40   # 内边距 px
