"""
================================================================
阶段 1-1：最小 LLM 调用 —— 发一句话给大模型，拿回回复
================================================================

【这个文件教会你什么】
  Agent 的最底层就是：发一段文字(prompt)给大模型，它返回一段文字。
  其他所有花哨的东西——Agent、工具调用、编排——全是在这一行调用上面包的壳。

  app/llm/myopenai_client.py  ← 里面就是封装了这个 OpenAI 客户端
  app/agent/question_check_agent.py  ← process() 方法里的 LLM 调用

【前端类比】
  这就像你第一次用 axios 调通一个接口：
  const res = await axios.post(url, data)
  这里就是：
  response = client.chat.completions.create(model=..., messages=...)

【运行方式】
  1. pip install openai
  2. 打开 config.py，把 API_KEY / BASE_URL 换成真实的
  3. python 01_LLM基础调用/01_最小调用.py
================================================================
"""

# ========== 第 1 步：导入库 ==========
# openai 是调用大模型的标准库，几乎所有大模型都兼容 OpenAI 的接口格式
# 前端类比：就像你用 axios 调后端接口


# ========== 第 2 步：从统一配置文件读取 ==========
# API Key 只需要在 config.py 里填一次，所有文件共用
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import API_KEY, BASE_URL, MODEL, get_client

client = get_client()


# ========== 第 4 步：发请求，拿结果 ==========
# 这是整个 Agent 世界里最核心的一行代码。
# messages 是一个列表，每条消息有 role（角色）和 content（内容）：
#   - system：给 AI 的"人设设定"，告诉它"你是谁、你要干嘛"
#   - user：用户的输入
#
# 前端类比：就像你调后端接口：
#   const res = await http.post('/chat', {
#     system: '你是客服助手',
#     user: '你好'
#   })
def ask_llm(question: str) -> str:
    """
    发一句话给大模型，返回它的回复。

    参数：
        question: 你想问的问题
    返回：
        大模型的回答文本
    """
    # chat.completions.create 就是"发请求"的核心方法
    response = client.chat.completions.create(
        model=MODEL,                              # 用哪个模型
        messages=[                                # 对话内容
            {
                "role": "system",                  # 系统提示词 = 给 AI 的人设
                "content": "你是一个专业的客服助手，请用简洁的中文回答用户问题。"
            },
            {
                "role": "user",                    # 用户消息 = 用户实际说的话
                "content": question
            }
        ],
        temperature=0.7,  # 温度：0=最稳定（每次回答几乎一样），1=最有创意（每次回答可能不同）
                          # 前端类比：就像一个"随机种子"的开关
    )

    # response 的结构：
    # response.choices[0].message.content  ← 这就是 AI 的回答文本
    # 前端类比：就像 res.data.choices[0].message.content
    answer = response.choices[0].message.content
    return answer


# ========== 第 5 步：跑起来 ==========
if __name__ == "__main__":
    print("=" * 50)
    print("阶段 1-1：最小 LLM 调用")
    print("=" * 50)

    # 准备几个测试问题
    questions = [
        "什么是 AI Agent？",
        "帮我写一段 Python 代码，计算斐波那契数列第 10 项",
        "用一句话解释什么是异步队列",
    ]

    for q in questions:
        print(f"\n📝 问：{q}")
        answer = ask_llm(q)
        print(f"🤖 答：{answer}")

    print("\n" + "=" * 50)
    print("✅ 恭喜！你刚刚完成了 AI Agent 的最底层操作。")
    print("   所有 Agent 的本质，就是在这一行调用上面加各种包装。")
    print("=" * 50)
