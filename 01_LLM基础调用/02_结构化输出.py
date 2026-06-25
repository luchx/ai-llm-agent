"""
================================================================
阶段 1-2：结构化输出 —— 让 AI 返回固定格式的 JSON
================================================================

【这个文件教会你什么】
  让大模型不要返回一段自由文本，而是返回固定格式的 JSON。
  这是 Agent 工程最关键的技术之一：让 AI 的输出"可被代码消费"。

  如果 AI 返回"我觉得这个回答涉及了房产降价的问题"，
  你的代码没法解析。但如果 AI 返回 {"is_exist": 1, "category": "房产降价"}，
  你的代码就能直接用了。

【对应 llm-agent】
  question_check_agent.py 里的 prompt 就是让 AI 返回固定的 JSON 格式：
  {"is_exist": 1/2, "confidence": "high/medium/low", "categories_detected": [...]}

【前端类比】
  就像你和后端约定接口返回格式：
  { code: 0, data: { ... }, message: 'ok' }
  这里你是和 AI 约定返回格式。

【运行方式】
  python 01_LLM基础调用/02_结构化输出.py
================================================================
"""

import json

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from config import API_KEY, BASE_URL, MODEL, get_client

client = get_client()


# ========== 核心技巧：在 prompt 里明确要求 JSON 格式 ==========
# 这是最简单也最常用的结构化输出方式。
# 关键在于 prompt 要写得非常明确，告诉 AI：
#   1. 你必须返回 JSON
#   2. JSON 里有哪些字段
#   3. 每个字段是什么类型、什么取值
#
# 对照 llm-agent 的 question_check_agent.py，它的 SYSTEM_PROMPT 就是这么写的。
SYSTEM_PROMPT = """你是一位专业的问卷分析专家。

你的任务：分析用户的问卷回答，判断是否涉及以下四类问题：
1. 房产车位降价（关键词：降价、便宜、价格、贬值）
2. 市政道路（关键词：道路、交通、堵车、修路）
3. 市政供暖（关键词：供暖、暖气、取暖、供热）
4. 周边配套（关键词：配套、学校、医院、商场）

【重要】你必须严格按以下 JSON 格式返回，不要返回任何其他内容：
{
    "is_exist": 1 或 2,           // 1=存在问题, 2=不存在问题
    "confidence": "high/medium/low",  // 你的判断置信度
    "categories_detected": ["类别1", "类别2"],  // 检测到的问题类别，没有则为空数组
    "reason": "一句话说明判断理由"
}"""


def analyze_answer(answer_text: str) -> dict:
    """
    分析问卷回答，返回结构化的 JSON 结果。

    参数：
        answer_text: 用户的问卷回答文本
    返回：
        dict: 包含 is_exist, confidence, categories_detected, reason 的字典

    对照 llm-agent：
        这就是 question_check_agent.py 里 process() 方法的核心逻辑
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下问卷回答：\n{answer_text}"},
        ],
        temperature=0.1,  # 判断题用低温度，保证结果稳定
    )

    raw_text = response.choices[0].message.content
    # AI 返回的可能带 markdown 代码块标记（```json ... ```），需要清理
    # 前端类比：就像你从后端拿到的可能是字符串，需要 JSON.parse
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        # 去掉 ```json 和 ```
        clean_text = clean_text.split("\n", 1)[1]  # 去掉第一行 ```json
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]  # 去掉最后的 ```
        clean_text = clean_text.strip()

    try:
        result = json.loads(clean_text)  # 把字符串解析成 dict
        return result
    except json.JSONDecodeError:
        # 如果 AI 返回的不是合法 JSON（偶尔会发生），给一个兜底结果
        # 对照 llm-agent：这就是 question_check_agent.py 里的"关键词降级"逻辑
        return {
            "is_exist": 0,
            "confidence": "low",
            "categories_detected": [],
            "reason": f"解析失败，原始返回：{raw_text[:100]}",
        }


# ========== 关键词降级方案 ==========
# 对照 llm-agent：question_check_agent.py 里有完整的关键词降级逻辑
# 当 LLM 不可用或返回异常时，用关键词匹配做兜底
# 前端类比：就像接口超时后你用本地缓存兜底
KEYWORDS = {
    "房产车位降价": ["降价", "便宜", "价格", "车位", "房产", "贬值"],
    "市政道路": ["道路", "交通", "路况", "堵车", "修路", "街道"],
    "市政供暖": ["供暖", "暖气", "取暖", "供热", "暖器", "温度"],
    "周边配套": ["配套", "设施", "学校", "医院", "商场", "公园", "超市"],
}


def analyze_by_keyword(answer_text: str) -> dict:
    """关键词降级方案：不用 LLM，直接用关键词匹配"""
    detected = []
    for category, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in answer_text:
                detected.append(category)
                break  # 一个类别命中一个关键词就够了

    return {
        "is_exist": 1 if detected else 2,
        "confidence": "medium" if detected else "high",
        "categories_detected": detected,
        "reason": "关键词匹配" + ("命中" if detected else "未命中"),
    }


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 1-2：结构化输出 —— 让 AI 返回 JSON")
    print("=" * 60)

    test_answers = [
        "因为别人买的比我便宜，我买的比较贵。",      # → 应该命中"房产车位降价"
        "小区门口经常堵车，修路修了好几个月。",       # → 应该命中"市政道路"
        "你们的服务态度很好，我很满意。",             # → 应该不命中任何类别
        "暖气不热，冬天在家还要穿棉袄。学校也远。",   # → 应该命中"市政供暖" + "周边配套"
    ]

    for ans in test_answers:
        print(f"\n📝 问卷回答：{ans}")

        # 用 LLM 分析
        result = analyze_answer(ans)
        print(f"🤖 LLM 分析：{json.dumps(result, ensure_ascii=False, indent=2)}")

        # 用关键词兜底验证
        kw_result = analyze_by_keyword(ans)
        print(f"🔑 关键词兜底：{kw_result['categories_detected']}")

    print("\n" + "=" * 60)
    print("✅ 看到没？AI 返回了标准的 JSON，你的代码可以直接用。")
    print("   这就是 Agent 工程的核心技巧：让 AI 的输出可被代码消费。")
    print("=" * 60)
