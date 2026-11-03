"""
poster-generator 主程序
Flask 路由 + 核心调度逻辑

缓存方案：改用文件缓存（output/cache/），解决内存缓存重启丢失问题

2025-05-14: 新增 format_card_content() 函数
           将 AI 返回的纯文本 card.content 智能转换为结构化 HTML
           支持：段落标题、数字列表、短横线列表、例题块、解析块、警示块
"""
import os
import re
import json
import uuid

from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect
from services.deepseek_client import generate_knowledge_card
from services.poster_exporter import export_poster_to_png
from config import SECRET_KEY, DEBUG

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 文件缓存目录：把每次生成的 JSON 数据存到磁盘
CACHE_DIR = os.path.join(os.path.dirname(__file__), "output", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def cache_save(poster_id, data):
    """把海报数据存到文件"""
    path = os.path.join(CACHE_DIR, f"{poster_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cache_load(poster_id):
    """从文件读取海报数据，不存在返回 None"""
    path = os.path.join(CACHE_DIR, f"{poster_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────
# 2025-05-14: 新增文本格式化函数
# 把 AI 返回的纯文本 card.content 转换为结构化 HTML
# ─────────────────────────────────────────────────────────────

def format_card_content(text):
    """
    将 AI 生成的纯文本 card.content 转为结构化 HTML。

    识别规则（按优先级）：
    - 【典型例题】/【例题】  → 绿色例题块（.example-block）
    - 【解析】             → 例题块内解析行
    - 【错因分析】/【注意】  → 橙色警示块（.warning-block）
    - 【正确解析】         → 例题块内正确答案行（.example-ans）
    - 答案：/答：          → 例题块内答案行
    - 段标题（以"："结尾的短行）→ <p><strong>…</strong></p>
    - 数字列表 1. / ①②③   → <ol><li>
    - 短横线列表 - xxx     → <ul><li>
    - 普通行               → <p>
    """
    if not text:
        return ""

    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # ── 智能分段：如果整段没有换行，按语义拆分 ────────────────────
    # AI 有时把所有内容挤在一行，需要智能插入换行
    # 策略：按句号/分号/问号/感叹号 + 后面跟数字/【/段标题特征 拆分
    if '\n' not in text or text.count('\n') < 3:
        # 先保护 【xxx】标签内的内容不被拆分
        placeholders = []
        def protect_brackets(m):
            placeholders.append(m.group(0))
            return f"\x00{len(placeholders)-1}\x00"
        text = re.sub(r'【[^】]+】', protect_brackets, text)

        # 按语义拆分：句号/分号/问号/感叹号 后跟 数字/【/字母/中文序号
        text = re.sub(r'([。；？！])(\s*)(?=\d+[\.、]|【|[①-⑩]|[一二三四五六七八九十]+、|\w+\s*[:：])', r'\1\n', text)

        # 恢复 【xxx】
        def restore_brackets(m):
            idx = int(m.group(1))
            return placeholders[idx] if idx < len(placeholders) else m.group(0)
        text = re.sub(r'\x00(\d+)\x00', restore_brackets, text)

    lines = text.split('\n')

    html_parts = []

    # 状态标记
    in_ol = False          # 是否在有序列表中
    in_ul = False          # 是否在无序列表中
    in_example = False     # 是否在例题块中
    example_has_ans = False  # 例题块是否已输出答案

    def close_ol():
        nonlocal in_ol
        if in_ol:
            html_parts.append('</ol>')
            in_ol = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            html_parts.append('</ul>')
            in_ul = False

    def close_lists():
        close_ol()
        close_ul()

    def close_example():
        nonlocal in_example, example_has_ans
        if in_example:
            html_parts.append('</div>')
            in_example = False
            example_has_ans = False

    # 【标签】提取辅助
    LABEL_PATTERN = re.compile(r'【(.+?)】')

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            # 空行：关闭列表（但不关闭例题块，例题块可能跨多行）
            close_lists()
            continue

        # ── 1. 识别 【典型例题】 / 【例题】 ──────────────────────
        if re.search(r'【典型例题】|【例题】', line):
            close_lists()
            close_example()
            # 去掉标签，保留正文
            content = re.sub(r'【典型例题】|【例题】', '', line).strip()
            html_parts.append(
                f'<div class="example-block">'
                f'<div class="example-q">📝 {content}</div>'
            )
            in_example = True
            example_has_ans = False
            continue

        # ── 2. 识别 【解析】（在例题块内） ─────────────────────────
        if re.search(r'【解析】', line) and in_example:
            content = re.sub(r'【解析】', '', line).strip()
            html_parts.append(f'<div style="color:#555;margin-top:6px">{content}</div>')
            continue

        # ── 3. 识别 【正确解析】 ──────────────────────────────────
        if re.search(r'【正确解析】|【正确答案】', line):
            close_lists()
            content = re.sub(r'【正确解析】|【正确答案】', '', line).strip()
            if in_example:
                html_parts.append(f'<div class="example-ans">✅ {content}</div>')
                close_example()
            else:
                html_parts.append(f'<p class="example-ans">✅ <strong>{content}</strong></p>')
            continue

        # ── 4. 识别 答案：/ 答：（在例题块内结束例题） ───────────────
        if re.match(r'^(答案[:：]|答[:：])', line):
            content = re.sub(r'^(答案[:：]|答[:：])\s*', '', line).strip()
            if in_example:
                html_parts.append(f'<div class="example-ans">✅ {content}</div>')
                close_example()
            else:
                close_lists()
                html_parts.append(f'<p>✅ <strong>答：</strong>{content}</p>')
            continue

        # ── 5. 识别 【错因分析】 / 【注意】 / 【易错】 ──────────────
        if re.search(r'【错因分析】|【注意】|【易错】|【易错点】', line):
            close_lists()
            close_example()
            content = re.sub(r'【错因分析】|【注意】|【易错】|【易错点】', '', line).strip()
            html_parts.append(f'<div class="warning-block">⚠️ {content}</div>')
            continue

        # ── 6. 识别 【培优拓展】 / 【口诀】 / 【技巧】 ──────────────
        if re.search(r'【培优拓展】|【口诀】|【解题技巧】|【技巧】', line):
            close_lists()
            close_example()
            content = re.sub(r'【培优拓展】|【口诀】|【解题技巧】|【技巧】', '', line).strip()
            html_parts.append(f'<div class="tip-block">💡 {content}</div>')
            continue

        # ── 7. 识别 ① ② ③ 等开头的有序列表 ──────────────────────
        if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', line):
            close_ul()
            close_example()
            if not in_ol:
                html_parts.append('<ol>')
                in_ol = True
            content = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', line).strip()
            html_parts.append(f'<li>{content}</li>')
            continue

        # ── 8. 识别数字列表 1. 2. 3. ────────────────────────────
        if re.match(r'^\d+[\.、]\s', line):
            close_ul()
            close_example()
            if not in_ol:
                html_parts.append('<ol>')
                in_ol = True
            content = re.sub(r'^\d+[\.、]\s*', '', line).strip()
            html_parts.append(f'<li>{content}</li>')
            continue

        # ── 9. 识别短横线列表 - xxx ──────────────────────────────
        if re.match(r'^[-·•]\s', line):
            close_ol()
            close_example()
            if not in_ul:
                html_parts.append('<ul>')
                in_ul = True
            content = re.sub(r'^[-·•]\s*', '', line).strip()
            html_parts.append(f'<li>{content}</li>')
            continue

        # ── 10. 段标题：短行 + 以"："结尾 ─────────────────────────
        if re.match(r'^[^①-⑩\d].{0,20}[:：]$', line):
            close_lists()
            close_example()
            title = line.rstrip('：:')
            html_parts.append(f'<p><strong>{title}：</strong></p>')
            continue

        # ── 11. 段标题：含"："且前部分较短（段落首行）────────────────
        if '：' in line and not in_ol and not in_ul:
            parts = line.split('：', 1)
            prefix, rest = parts[0], parts[1]
            # 前缀短（≤15字）且不是数字开头，视为段标题
            if len(prefix) <= 15 and not re.match(r'^\d', prefix) and rest.strip():
                close_lists()
                close_example()
                html_parts.append(f'<p><strong>{prefix}：</strong>{rest}</p>')
                continue

        # ── 12. 其余：普通文本行 ─────────────────────────────────
        close_lists()
        if in_example:
            # 例题块内的普通行
            html_parts.append(f'<div style="color:#555;margin-top:4px">{line}</div>')
        else:
            html_parts.append(f'<p>{line}</p>')

    # 收尾：关闭所有未关闭的块
    close_lists()
    close_example()

    return '\n'.join(html_parts)


def prepare_card_data(card_data):
    """
    2025-05-14: 对 card_data 中每张卡片的 content 进行 HTML 格式化
    返回处理后的 card_data（不修改原始缓存）
    """
    import copy
    data = copy.deepcopy(card_data)
    if 'cards' in data and isinstance(data['cards'], list):
        for card in data['cards']:
            if 'content' in card and isinstance(card['content'], str):
                card['content'] = format_card_content(card['content'])
    return data


# ─────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """首页：输入表单"""
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    AJAX 接口：接收表单参数 → 调用 DeepSeek → 返回 poster_id
    前端拿到 poster_id 后跳转到 /poster/<poster_id>
    """
    data = request.get_json(force=True)
    grade     = data.get("grade", "")
    subject   = data.get("subject", "")
    book      = data.get("book", "")
    publisher = data.get("publisher", "")
    unit_name = data.get("unit_name", "")
    stage     = data.get("stage", "小学")

    if not all([grade, subject, book, publisher, unit_name]):
        return jsonify({"error": "请填写完整信息"}), 400

    try:
        card_data = generate_knowledge_card(grade, subject, book, publisher, unit_name, stage=stage)
    except Exception as e:
        print(f"[Generate] DeepSeek 调用失败：{e}")
        return jsonify({"error": f"AI 生成失败：{str(e)}"}), 500

    # 生成唯一 ID，存入文件缓存（重启 Flask 也不会丢失）
    poster_id = uuid.uuid4().hex[:12]
    cache_save(poster_id, card_data)

    print(f"[Generate] 海报已生成，ID={poster_id}")
    return jsonify({"poster_id": poster_id})


@app.route("/generate", methods=["POST"])
def generate_poster_form():
    """
    表单提交接口：接收表单参数 → 调用 DeepSeek → 直接重定向到海报页
    用于 <form target="_blank"> 在新标签页打开海报
    """
    grade     = request.form.get("grade", "")
    subject   = request.form.get("subject", "")
    book      = request.form.get("book", "")
    publisher = request.form.get("publisher", "")
    unit_name = request.form.get("unit_name", "")
    stage     = request.form.get("stage", "小学")

    if not all([grade, subject, book, publisher, unit_name]):
        return "请填写完整信息", 400

    try:
        card_data = generate_knowledge_card(grade, subject, book, publisher, unit_name, stage=stage)
    except Exception as e:
        print(f"[Generate] DeepSeek 调用失败：{e}")
        return f"AI 生成失败：{str(e)}", 500

    poster_id = uuid.uuid4().hex[:12]
    cache_save(poster_id, card_data)

    print(f"[Generate] 海报已生成，ID={poster_id}")
    return redirect(url_for("show_poster", poster_id=poster_id))


@app.route("/poster/<poster_id>")
def show_poster(poster_id):
    """海报预览页：渲染动态 HTML 海报"""
    card_data = cache_load(poster_id)
    if not card_data:
        return "海报已过期，请重新生成", 404

    # 2025-05-14: 对 card.content 进行 HTML 格式化，确保内容层级清晰
    card_data = prepare_card_data(card_data)

    # 检查是否使用新版布局
    use_demo = request.args.get("demo", "0") == "1"
    template = "poster-demo.html" if use_demo else "poster.html"
    return render_template(template, data=card_data, poster_id=poster_id)


@app.route("/poster-demo/<poster_id>")
def show_poster_demo(poster_id):
    """海报预览页（新版左右分栏布局）"""
    card_data = cache_load(poster_id)
    if not card_data:
        return "海报已过期，请重新生成", 404

    # 2025-05-14: 对 card.content 进行 HTML 格式化
    card_data = prepare_card_data(card_data)

    return render_template("poster-demo.html", data=card_data, poster_id=poster_id)


@app.route("/api/export/<poster_id>")
def api_export(poster_id):
    """
    导出 PNG：Playwright 直接访问 Flask HTTP URL 截图
    - Playwright 访问 127.0.0.1（服务器本地），保证 CSS/字体完整渲染
    - 数据从文件缓存读取，不依赖内存
    """
    card_data = cache_load(poster_id)
    if not card_data:
        return jsonify({"error": "海报数据不存在，请重新生成"}), 404

    # Playwright 在服务器本地访问（127.0.0.1），与客户端访问IP无关
    poster_url = f"http://127.0.0.1:5000/poster/{poster_id}?export=1"

    try:
        png_path = export_poster_to_png(poster_url, f"poster_{poster_id}.png")
    except Exception as e:
        print(f"[Export] 截图失败：{e}")
        return jsonify({"error": f"截图失败：{str(e)}"}), 500

    return send_file(
        png_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"知识卡_{poster_id}.png"
    )


@app.route("/loading")
def loading():
    """生成中等待页（可选）"""
    return render_template("loading.html")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
