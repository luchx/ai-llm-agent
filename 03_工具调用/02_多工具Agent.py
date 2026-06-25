"""
================================================================
阶段 3-2：多工具 Agent —— 复杂场景的工具编排
================================================================

【这个文件教会你什么】
  当 Agent 有很多工具时，如何管理它们？如何处理多个工具的调用结果？
  这个模式对应 llm-agent 里 kf_chat_task（AI 客服）的设计思路。

【对应 llm-agent】
  app/agent/kf_chat_task/ 里的 AI 客服有十几个子 Agent/工具：
  查工单、查业主信息、查知识库、查房产信息……
  AI 根据用户的问题自己决定调用哪个（或哪几个）。

【运行方式】
  python 03_工具调用/02_多工具Agent.py
================================================================
"""

import json

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from config import API_KEY, BASE_URL, MODEL, get_client

client = get_client()


# ========== 工具集：模拟一个客服系统的所有工具 ==========

def query_workorder(workorder_id: str) -> dict:
    """查询工单详情"""
    return {
        "id": workorder_id,
        "type": "报修",
        "status": "处理中",
        "handler": "张师傅",
        "description": "3号楼2单元电梯故障",
        "created_at": "2025-01-20 10:30",
    }

def query_property(owner_name: str) -> dict:
    """查询业主房产信息"""
    fake_data = {
        "张三": {"house": "3号楼2单元1801", "area": "89.5㎡", "type": "两室一厅", "check_in": "2023-06"},
        "李四": {"house": "5号楼1单元302", "area": "120㎡", "type": "三室两厅", "check_in": "2022-12"},
    }
    return fake_data.get(owner_name, {"error": "未找到业主信息"})

def query_fee(owner_name: str) -> dict:
    """查询物业费缴纳情况"""
    fake_data = {
        "张三": {"total": 3600, "paid": 3600, "status": "已缴清", "next_due": "2025-07-01"},
        "李四": {"total": 4800, "paid": 2400, "status": "欠费", "next_due": "2025-01-01"},
    }
    return fake_data.get(owner_name, {"error": "未找到缴费记录"})

def submit_complaint(category: str, content: str, contact: str) -> dict:
    """提交投诉工单"""
    return {
        "complaint_id": "CP-20250120-001",
        "category": category,
        "content": content,
        "contact": contact,
        "status": "已受理",
        "message": "我们会在24小时内联系您处理",
    }


# ========== 工具说明书 ==========
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_workorder",
            "description": "查询工单详情，包括工单类型、处理状态、处理人等",
            "parameters": {
                "type": "object",
                "properties": {
                    "workorder_id": {"type": "string", "description": "工单编号"}
                },
                "required": ["workorder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_property",
            "description": "查询业主的房产信息，包括房号、面积、户型等",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner_name": {"type": "string", "description": "业主姓名"}
                },
                "required": ["owner_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_fee",
            "description": "查询业主的物业费缴纳情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner_name": {"type": "string", "description": "业主姓名"}
                },
                "required": ["owner_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_complaint",
            "description": "帮用户提交一条投诉工单",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "投诉类别，如：噪音、卫生、安全"},
                    "content": {"type": "string", "description": "投诉内容"},
                    "contact": {"type": "string", "description": "联系方式"},
                },
                "required": ["category", "content", "contact"],
            },
        },
    },
]

TOOL_MAP = {
    "query_workorder": query_workorder,
    "query_property": query_property,
    "query_fee": query_fee,
    "submit_complaint": submit_complaint,
}


def ask_agent(user_question: str) -> str:
    """
    多工具 Agent 的完整流程。
    支持 AI 同时调用多个工具（parallel tool calls）。
    """
    messages = [
        {
            "role": "system",
            "content": (
                "你是明源云的专业物业客服助手。你可以帮用户查询工单、房产信息、物业费，"
                "也可以帮用户提交投诉。请用简洁友好的中文回答。"
                "如果用户提了多个问题，可以同时调用多个工具。"
            ),
        },
        {"role": "user", "content": user_question},
    ]

    # 第 1 次调用：让 AI 判断需要用哪些工具
    response = client.chat.completions.create(
        model=MODEL, messages=messages, tools=tools, temperature=0.1
    )
    msg = response.choices[0].message

    if msg.tool_calls:
        print(f"  🔧 AI 决定调用 {len(msg.tool_calls)} 个工具：")
        messages.append(msg)

        # 逐个执行工具并收集结果
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            print(f"     → {fn_name}({fn_args})")

            result = TOOL_MAP.get(fn_name, lambda **k: {"error": "未知工具"})(**fn_args)
            print(f"     ← 返回：{json.dumps(result, ensure_ascii=False)}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        # 第 2 次调用：让 AI 基于所有工具结果组织回复
        final = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.7)
        return final.choices[0].message.content
    else:
        return msg.content


if __name__ == "__main__":
    print("=" * 60)
    print("阶段 3-2：多工具 Agent —— 复杂场景")
    print("=" * 60)

    # 测试 1：单工具调用
    print(f"\n{'─'*60}")
    print("测试 1：查工单")
    print(f"👤 用户：帮我查下工单 WO-20250120 的情况")
    print(f"🤖 AI：{ask_agent('帮我查下工单 WO-20250120 的情况')}")

    # 测试 2：多工具同时调用（AI 可能一次调多个工具）
    print(f"\n{'─'*60}")
    print("测试 2：多问题（AI 可能同时调多个工具）")
    print(f"👤 用户：帮我查下张三的房产信息和物业费缴纳情况")
    print(f"🤖 AI：{ask_agent('帮我查下张三的房产信息和物业费缴纳情况')}")

    # 测试 3：提交投诉
    print(f"\n{'─'*60}")
    print("测试 3：提交投诉")
    print(f"👤 用户：我要投诉，楼上太吵了，每天晚上12点还在装修，我的电话是13800138000")
    print(f"🤖 AI：{ask_agent('我要投诉，楼上太吵了，每天晚上12点还在装修，我的电话是13800138000')}")

    print(f"\n{'='*60}")
    print("✅ 多工具 Agent 的关键点：")
    print("   1. AI 可以同时调用多个工具（parallel tool calls）")
    print("   2. 每个工具的结果都要通过 tool role 喂回 AI")
    print("   3. 最后 AI 综合所有结果，组织成自然语言回复")
    print("   对照 llm-agent/kf_chat_task/，AI 客服就是这个模式的生产级实现。")
