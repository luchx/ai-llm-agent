"""
================================================================
阶段 3-1：Function Calling —— 让 AI 自己决定调用函数
================================================================

【这个文件教会你什么】
  这是 Agent 和普通聊天机器人最核心的区别：
  普通聊天机器人只会"说"，Agent 能"做事"。

  Function Calling 的流程：
  1. 你告诉 AI "你有哪些工具可以用"（工具说明书）
  2. AI 自己判断"这个问题需不需要用工具"
  3. 如果需要，AI 返回它想调哪个函数、传什么参数
  4. 你真的去执行这个函数
  5. 把函数结果再喂回 AI，让它组织成自然语言回复

【对应 llm-agent】
  Agent 的核心能力之一。kf_chat_task 里的 AI 客服就是用 Function Calling
  来调用查工单、查业主信息等工具的。

【前端类比】
  就像你写一个智能助手：
  用户说"帮我查一下订单 123" → 前端解析意图 → 调后端接口 → 展示结果
  这里是 AI 替你做了"解析意图"这一步。

【运行方式】
  python 03_工具调用/01_FunctionCalling.py
================================================================
"""

import json

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from config import API_KEY, BASE_URL, MODEL, get_client

client = get_client()


# ========== 第 1 步：定义工具（就是一个普通的 Python 函数）==========
# 这个函数假装去数据库查工单状态。
# 真实项目里，这里面会是真正的数据库查询。
# 对照 llm-agent：各种 Agent 里调用的后端服务函数
def query_order_status(order_id: str) -> dict:
    """根据工单号查询处理状态"""
    # 假数据，模拟数据库查询结果
    fake_db = {
        "12345": {"status": "处理中", "handler": "张工", "created": "2025-01-15", "eta": "今天下午"},
        "67890": {"status": "已完成", "handler": "李工", "created": "2025-01-10", "eta": "已交付"},
        "11111": {"status": "待分配", "handler": "未分配", "created": "2025-01-20", "eta": "待定"},
    }
    return fake_db.get(order_id, {"status": "查无此工单", "handler": "无", "created": "无", "eta": "无"})


def get_weather(city: str) -> dict:
    """查询城市天气（模拟）"""
    fake_weather = {
        "北京": {"temp": "5°C", "weather": "晴", "wind": "北风3级"},
        "上海": {"temp": "8°C", "weather": "多云", "wind": "东风2级"},
        "深圳": {"temp": "18°C", "weather": "阴", "wind": "南风1级"},
    }
    return fake_weather.get(city, {"temp": "未知", "weather": "未知", "wind": "未知"})


# ========== 第 2 步：写"工具说明书" ==========
# 这是告诉 AI "你有哪些工具"的关键。
# 每个工具需要写清楚：
#   - name: 函数名（必须和实际函数名一致）
#   - description: 这个工具是干嘛的（AI 靠这个判断要不要用）
#   - parameters: 参数定义（AI 靠这个知道该传什么）
#
# 前端类比：就像你写 API 文档，告诉前端"有哪些接口、传什么参数"。
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_order_status",
            "description": "根据工单号查询工单的处理状态、处理人和预计完成时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "工单号，例如 12345",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如 北京",
                    }
                },
                "required": ["city"],
            },
        },
    },
]


# ========== 第 3 步：工具执行器 ==========
# 这是一个"工具名 → 函数"的映射。
# AI 返回工具名后，你在这里找到对应的函数去执行。
# 前端类比：就像一个路由映射 { '/api/order': handler, '/api/weather': handler }
TOOL_MAP = {
    "query_order_status": query_order_status,
    "get_weather": get_weather,
}


# ========== 第 4 步：完整的 Agent 流程 ==========
def ask_agent(user_question: str) -> str:
    """
    完整的 Function Calling 流程：

    1. 把用户问题 + 工具说明书发给 AI
    2. AI 判断需不需要用工具
    3. 如果需要 → 执行工具 → 把结果喂回 AI → AI 组织回复
    4. 如果不需要 → AI 直接回复

    前端类比：这就是一个完整的"意图识别 → 调接口 → 渲染"流程。
    """
    # 构建消息列表
    messages = [
        {"role": "system", "content": "你是一个智能客服助手，可以帮用户查询工单状态和天气。请用简洁的中文回答。"},
        {"role": "user", "content": user_question},
    ]

    # 第 1 次调用 AI：发问题 + 工具说明书
    # AI 会返回两种情况之一：
    #   A. tool_calls 不为空 → AI 决定要用工具
    #   B. tool_calls 为空 → AI 觉得不用工具，直接回答
    print(f"  📤 发送给 AI（附带 {len(tools)} 个工具说明书）...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,  # ← 关键：告诉 AI 它有工具可用
        temperature=0.1,
    )
    msg = response.choices[0].message

    # ========== 情况 A：AI 决定用工具 ==========
    if msg.tool_calls:
        # AI 可能同时调用多个工具，这里逐个处理
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name          # AI 想调哪个函数
            fn_args = json.loads(tool_call.function.arguments)  # AI 自己填的参数！
            print(f"  🔧 AI 决定调用工具：{fn_name}({fn_args})")

            # 真正执行这个函数
            if fn_name in TOOL_MAP:
                result = TOOL_MAP[fn_name](**fn_args)
            else:
                result = {"error": f"未知工具: {fn_name}"}

            print(f"  📦 工具返回：{result}")

            # 把工具结果加到消息列表里，再喂回 AI
            # 这样 AI 就能基于真实数据来组织回复
            messages.append(msg)  # AI 的回复（包含 tool_calls）
            messages.append({
                "role": "tool",                   # 角色是 "tool"，表示这是工具返回的结果
                "tool_call_id": tool_call.id,     # 关联到哪个 tool_call
                "content": json.dumps(result, ensure_ascii=False),
            })

        # 第 2 次调用 AI：把工具结果喂回去，让 AI 组织成自然语言
        print(f"  📤 把工具结果喂回 AI，让它组织回复...")
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
        )
        return final_response.choices[0].message.content

    # ========== 情况 B：AI 觉得不需要用工具 ==========
    else:
        print(f"  💬 AI 决定直接回答（不使用工具）")
        return msg.content


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 3-1：Function Calling —— 让 AI 自己决定调用函数")
    print("=" * 60)

    # 测试 1：需要调用 query_order_status
    print(f"\n{'─'*60}")
    print("测试 1：查工单（需要工具）")
    print(f"👤 用户：帮我查下工单 12345 现在什么情况？")
    answer = ask_agent("帮我查下工单 12345 现在什么情况？")
    print(f"🤖 AI：{answer}")

    # 测试 2：不需要工具
    print(f"\n{'─'*60}")
    print("测试 2：普通问题（不需要工具）")
    print(f"👤 用户：你好，你是谁？")
    answer = ask_agent("你好，你是谁？")
    print(f"🤖 AI：{answer}")

    # 测试 3：查天气
    print(f"\n{'─'*60}")
    print("测试 3：查天气（另一个工具）")
    print(f"👤 用户：今天北京天气怎么样？")
    answer = ask_agent("今天北京天气怎么样？")
    print(f"🤖 AI：{answer}")

    print(f"\n{'='*60}")
    print("✅ 看到没？AI 自己判断了什么时候该用工具、用哪个工具。")
    print("   这就是 Agent 的灵魂：不只是说，而是能动手做事。")
    print("   核心就是 5 步：工具说明书 → AI 判断 → 执行函数 → 结果喂回 → 组织回复")
