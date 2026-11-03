"""
DeepSeek API 调用封装
支持三科分学科提示词路由
支持 小学/初中/高中 学段自适应（{stage}/{exam} 占位符）
"""
import json
import re
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

# 学科与提示词文件映射
PROMPT_FILES = {
    "数学": "prompts/math.txt",
    "英语": "prompts/english.txt",
    "语文": "prompts/chinese.txt"
}

# 学科与卡片标题映射（数学第6卡按学段变名）
SUBJECT_CARDS = {
    "数学": [
        "核心概念定义",
        "核心知识点汇总",
        "单元重点梳理",
        "单元难点突破",
        "知识结构树",
        "生活应用与奥数培优"
    ],
    "英语": [
        "核心词汇汇总",
        "重点短语搭配",
        "核心句型交际",
        "单元语法精讲",
        "单元知识结构树",
        "情景运用与培优拓展"
    ],
    "语文": [
        "单元生字词积累",
        "重点词句与佳句赏析",
        "段落精读与细节解析",
        "篇章结构与中心思想",
        "单元知识结构树",
        "读写应用与培优拓展"
    ]
}

# 学段 → 考试/考纲关键词（注入 {exam} 占位符）
STAGE_EXAM = {
    "小学": "期末统考与小升初",
    "初中": "期中期末与中考",
    "高中": "期中期末与高考",
}


def get_subject_cards(subject, stage=None):
    """获取某学科固定卡片标题；数学按学段切换第6卡名称"""
    titles = list(SUBJECT_CARDS.get(subject, SUBJECT_CARDS["数学"]))
    if subject == "数学":
        if stage == "初中":
            titles[5] = "生活应用与中考培优"
        elif stage == "高中":
            titles[5] = "生活应用与高考培优"
    return titles


# 学科与颜色主题映射
SUBJECT_THEMES = {
    "数学": {
        "primary": "#7C3AED",
        "primary_light": "#A78BFA",
        "primary_dark": "#5B21B6",
        "icon": "🔢"
    },
    "英语": {
        "primary": "#2563EB",
        "primary_light": "#60A5FA",
        "primary_dark": "#1D4ED8",
        "icon": "🔤"
    },
    "语文": {
        "primary": "#059669",
        "primary_light": "#34D399",
        "primary_dark": "#047857",
        "icon": "📖"
    }
}


def get_deepseek_client():
    """创建 DeepSeek 客户端"""
    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )


def load_prompt_template(subject):
    """
    根据学科加载对应的提示词模板

    Args:
        subject: 学科名称（数学/英语/语文）
    Returns:
        str: 提示词模板内容
    """
    prompt_file = PROMPT_FILES.get(subject)
    if not prompt_file:
        raise ValueError(f"未知学科: {subject}，支持的学科: {list(PROMPT_FILES.keys())}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


def replace_placeholders(template, grade, subject, book, publisher, unit_name,
                         stage="小学", exam="期末统考与小升初"):
    """
    替换提示词模板中的占位符
    使用 str.replace() 避免 .format() 对双大括号 {{}} 的解析问题

    Args:
        template: 提示词模板字符串
        grade: 年级
        subject: 学科
        book: 册别
        publisher: 出版社
        unit_name: 单元名称
        stage: 学段（小学/初中/高中）
        exam: 考试/考纲关键词（由 stage 推导）
    Returns:
        str: 替换后的提示词
    """
    result = template
    result = result.replace("{stage}", str(stage))
    result = result.replace("{exam}", str(exam))
    result = result.replace("{grade}", str(grade))
    result = result.replace("{subject}", str(subject))
    result = result.replace("{book}", str(book))
    result = result.replace("{publisher}", str(publisher))
    result = result.replace("{unit}", str(unit_name))
    return result


def parse_json_content(content):
    """
    解析 DeepSeek 返回的 JSON 内容
    兼容有无 ```json 包裹的情况

    Args:
        content: DeepSeek 返回的原始内容
    Returns:
        list: 知识卡片列表
    """
    content = content.strip()

    # 处理 markdown 代码块包裹
    if content.startswith("```"):
        # 去掉 ```json 或 ``` 等标记
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                return json.loads(part)

    # 直接是 JSON 数组
    if content.startswith("["):
        return json.loads(content)

    raise ValueError(f"无法解析 JSON 内容: {content[:100]}...")


def generate_knowledge_card(grade, subject, book, publisher, unit_name, stage="小学"):
    """
    调用 DeepSeek 生成知识卡片 JSON 数据

    Args:
        grade: 年级
        subject: 学科（数学/英语/语文）
        book: 册别
        publisher: 出版社
        unit_name: 单元名
        stage: 学段（小学/初中/高中）

    Returns:
        dict: 解析后的完整 JSON 数据
    """
    client = get_deepseek_client()
    prompt_template = load_prompt_template(subject)

    # 由学段推导考试/考纲关键词
    exam = STAGE_EXAM.get(stage, STAGE_EXAM["小学"])

    # 替换模板中的占位符（使用 replace 避免双大括号问题）
    user_prompt = replace_placeholders(
        prompt_template,
        grade=grade,
        subject=subject,
        book=book,
        publisher=publisher,
        unit_name=unit_name,
        stage=stage,
        exam=exam
    )

    print(f"[DeepSeek] 开始生成：{stage}{grade}{book}·{subject}·{unit_name}")
    print(f"[DeepSeek] 使用提示词：{PROMPT_FILES.get(subject)}")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "你是一名专业的教育内容生成助手，擅长将教材知识结构化输出。请严格按照JSON格式输出，不要有任何多余内容。"
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3
        # 注意：提示词已明确要求"仅输出纯JSON数组"，故不使用
        # response_format=json_object，避免与数组输出冲突导致 500。
    )

    raw_content = response.choices[0].message.content
    print(f"[DeepSeek] 生成完成，原始响应长度：{len(raw_content)} 字符")

    # 解析卡片数据
    try:
        cards = parse_json_content(raw_content)
    except json.JSONDecodeError as e:
        print(f"[DeepSeek] JSON解析失败: {e}")
        print(f"[DeepSeek] 原始内容: {raw_content[:500]}")
        raise

    # 构建完整的返回数据结构
    result = {
        "meta": {
            "grade": grade,
            "subject": subject,
            "book": book,
            "publisher": publisher,
            "unit_name": unit_name,
            "stage": stage,
            "poster_title": f"{grade}{book}·{subject}·{unit_name}",
            "theme": SUBJECT_THEMES.get(subject, SUBJECT_THEMES["数学"]),
            "card_titles": get_subject_cards(subject, stage)
        },
        "cards": cards
    }

    print(f"[DeepSeek] 解析成功，共 {len(cards)} 张知识卡片")
    return result


def get_subject_info(subject, stage="小学"):
    """
    获取学科相关信息（卡片标题、颜色主题等）

    Args:
        subject: 学科名称
        stage: 学段（数学第6卡标题按学段变化）
    Returns:
        dict: 学科信息
    """
    return {
        "cards": get_subject_cards(subject, stage),
        "theme": SUBJECT_THEMES.get(subject, SUBJECT_THEMES["数学"])
    }
