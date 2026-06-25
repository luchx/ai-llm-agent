"""
================================================================
阶段 1-3：多轮对话 —— 让 AI 记住上下文
================================================================

【这个文件教会你什么】
  单次调用只能"一问一答"。多轮对话是让 AI 记住之前说过什么，
  这是 AI 客服、聊天机器人的基础。

  app/agent/kf_chat_task/ 里的 AI 客服就用到了多轮对话和上下文管理。
  app/agent/kf_chat_task/core/context_manager.py 负责管理对话历史。

【核心原理】
  AI 本身没有记忆！它的"记忆"就是你每次发给它的 messages 列表。
  所谓多轮对话，就是你把历史消息全部带上再发一次。
  前端类比：就像你在前端维护一个 chatMessages 数组，每次发请求都带上完整历史。

【运行方式】
  python 01_LLM基础调用/03_多轮对话.py
================================================================
"""


import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from config import API_KEY, BASE_URL, MODEL, get_client

client = get_client()


class SimpleChatBot:
    """
    一个最简单的多轮对话机器人。

    核心设计：内部维护一个 messages 列表，每次对话都带上完整历史。
    前端类比：这就是一个聊天组件的 state.messages。
    """

    def __init__(self, system_prompt: str = "你是一个专业的客服助手。"):
        # messages 就是"记忆"——所有历史对话都在这里
        # 前端类比：const [messages, setMessages] = useState([...])
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]

    def chat(self, user_input: str) -> str:
        """
        发送一条消息，返回 AI 的回复。

        每次调用都会：
        1. 把用户消息加到历史里
        2. 把完整历史发给大模型
        3. 把 AI 的回复也加到历史里
        """
        # 第 1 步：把用户消息加到历史
        self.messages.append({"role": "user", "content": user_input})

        print(self.messages)

        # 第 2 步：把完整历史发给大模型（这就是"多轮"的秘密）
        response = client.chat.completions.create(
            model=MODEL,
            messages=self.messages,  # ← 带上所有历史消息！
            temperature=0.7,
        )

        # 第 3 步：把 AI 的回复也加到历史，这样下次对话 AI 能"记住"自己说过什么
        ai_reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": ai_reply})

        return ai_reply

    def get_history(self) -> list:
        """获取完整对话历史（除了 system prompt）"""
        return [m for m in self.messages if m["role"] != "system"]

    def clear(self):
        """清空对话历史（重新开始）"""
        system_msg = self.messages[0]  # 保留 system prompt
        self.messages = [system_msg]


if __name__ == "__main__":
    print("=" * 55)
    print("阶段 1-3：多轮对话 —— 让 AI 记住上下文")
    print("=" * 55)

    # 创建一个客服机器人
    bot = SimpleChatBot(
        system_prompt="你是明源云的专业客服助手，负责回答业主关于物业服务的问题。请用简洁友好的中文回答。"
    )

    # 模拟多轮对话
    conversations = [
        "你好，我想问一下物业费的问题",
        "我们小区物业费是多少钱一平？",
        "那停车费呢？",
        "最近有物业费的优惠活动吗？",  # 这个问题需要 AI 记住前面聊了"物业费"
    ]

    for msg in conversations:
        print(f"\n👤 用户：{msg}")
        reply = bot.chat(msg)
        print(f"🤖 客服：{reply}")

    # 展示对话历史
    print("\n" + "-" * 55)
    print("📋 对话历史（一共 {} 轮）：".format(len(bot.get_history()) // 2))
    for m in bot.get_history():
        role = "👤" if m["role"] == "user" else "🤖"
        print(f"  {role} {m['content'][:50]}...")

    print("\n" + "=" * 55)
    print("✅ 看到没？AI 记住了前面聊的内容。")
    print("   秘密就在于：每次把完整 messages 列表发给模型。")
    print("。")
    print("=" * 55)
