"""
================================================================
阶段 5-1：LangGraph 基础 —— 用图来编排多步 AI 流程
================================================================

【这个文件教会你什么】
  当一个任务需要多步处理时（先分类 → 再检索 → 再回答），
  用 if-else 写会变成一团乱麻。LangGraph 让你用"图"来描述流程：
  每一步是一个"节点"(Node)，步骤之间的跳转是"边"(Edge)。

  app/graph/                            ← 基础图定义
  app/agent/identify_answer/workflow.py ← 真实的多步工作流
  app/agent/survey_analysis/           ← 更复杂的 LangGraph 编排

【前端类比】
  就像一个复杂的状态机：
  idle → loading → success/error
  或者一个 Redux 的 middleware chain：
  action → middleware1 → middleware2 → reducer

【运行方式】
  pip install langchain langgraph
  python 05_LangGraph编排/01_简单图.py
================================================================
"""

from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END


# ========== 第 1 步：定义"状态" ==========
# 状态是贯穿整个图的数据，每个节点都可以读取和修改它。
# 前端类比：就像 Redux 的 state，每个 reducer 都能读写。
class AgentState(TypedDict):
    """
    Agent 的全局状态。
    每个节点都能读取和修改这些字段。
    """
    user_input: str       # 用户输入
    category: str         # 分类结果
    response: str         # 最终回复
    steps: list           # 记录经过了哪些步骤（方便调试）


# ========== 第 2 步：定义"节点" ==========
# 节点就是一个函数，接收当前状态，返回修改后的状态。
# 前端类比：就像 Redux 的 reducer 函数
def classify_node(state: AgentState) -> dict:
    """分类节点：判断用户问题属于哪一类"""
    user_input = state["user_input"]

    # 简单的关键词分类（真实项目会用 LLM）
    if any(kw in user_input for kw in ["工单", "报修", "维修", "故障"]):
        category = "工单问题"
    elif any(kw in user_input for kw in ["物业费", "缴费", "账单"]):
        category = "费用问题"
    elif any(kw in user_input for kw in ["投诉", "噪音", "卫生"]):
        category = "投诉建议"
    else:
        category = "一般咨询"

    print(f"  📊 分类节点：'{user_input}' → {category}")

    return {
        "category": category,
        "steps": state.get("steps", []) + [f"分类→{category}"],
    }


def handle_workorder(state: AgentState) -> dict:
    """处理工单问题的节点"""
    print(f"  🔧 工单处理节点：处理 '{state['user_input']}'")
    return {
        "response": f"您好，关于您的工单问题「{state['user_input']}」，已为您创建维修工单，编号 WO-{hash(state['user_input']) % 10000:04d}，预计24小时内处理。",
        "steps": state.get("steps", []) + ["工单处理"],
    }


def handle_fee(state: AgentState) -> dict:
    """处理费用问题的节点"""
    print(f"  💰 费用处理节点：处理 '{state['user_input']}'")
    return {
        "response": f"您好，关于物业费问题「{state['user_input']}」，您的物业费缴纳状态正常，如需详细账单请联系物业前台。",
        "steps": state.get("steps", []) + ["费用处理"],
    }


def handle_complaint(state: AgentState) -> dict:
    """处理投诉的节点"""
    print(f"  📢 投诉处理节点：处理 '{state['user_input']}'")
    return {
        "response": f"您好，关于您的投诉「{state['user_input']}」，我们非常重视，已记录并转交相关部门，会在48小时内给您回复。",
        "steps": state.get("steps", []) + ["投诉处理"],
    }


def handle_general(state: AgentState) -> dict:
    """处理一般咨询的节点"""
    print(f"  💬 一般咨询节点：处理 '{state['user_input']}'")
    return {
        "response": f"您好，关于您的问题「{state['user_input']}」，如有具体需求请拨打物业服务热线 400-xxx-xxxx。",
        "steps": state.get("steps", []) + ["一般咨询"],
    }


# ========== 第 3 步：定义"路由"（条件边） ==========
# 路由函数根据当前状态决定下一步走哪个节点。
# 前端类比：就像一个 switch-case 或者路由守卫
def route_by_category(state: AgentState) -> Literal["handle_workorder", "handle_fee", "handle_complaint", "handle_general"]:
    """根据分类结果，决定下一步走哪个处理节点"""
    category = state["category"]
    if category == "工单问题":
        return "handle_workorder"
    elif category == "费用问题":
        return "handle_fee"
    elif category == "投诉建议":
        return "handle_complaint"
    else:
        return "handle_general"


# ========== 第 4 步：构建图 ==========
# 把节点和边组装成一个完整的流程图。
# 前端类比：就像配置一个路由表

# 创建图构建器
graph_builder = StateGraph(AgentState)

# 添加所有节点
graph_builder.add_node("classify", classify_node)          # 分类节点
graph_builder.add_node("handle_workorder", handle_workorder)  # 工单处理
graph_builder.add_node("handle_fee", handle_fee)            # 费用处理
graph_builder.add_node("handle_complaint", handle_complaint)  # 投诉处理
graph_builder.add_node("handle_general", handle_general)    # 一般咨询

# 添加边（定义流程）
graph_builder.add_edge(START, "classify")                   # 开始 → 分类
graph_builder.add_conditional_edges(                         # 分类 → 根据结果走不同分支
    "classify",                                              # 从分类节点出发
    route_by_category,                                       # 用路由函数决定去哪
)
graph_builder.add_edge("handle_workorder", END)             # 处理完 → 结束
graph_builder.add_edge("handle_fee", END)
graph_builder.add_edge("handle_complaint", END)
graph_builder.add_edge("handle_general", END)

# 编译图（生成可执行的 workflow）
workflow = graph_builder.compile()


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 5-1：LangGraph 基础 —— 用图编排多步流程")
    print("=" * 60)

    # 测试不同类型的用户输入
    test_inputs = [
        "我家的门锁坏了，需要报修",
        "这个月的物业费是多少？",
        "楼上太吵了，我要投诉",
        "你们物业几点下班？",
    ]

    for user_input in test_inputs:
        print(f"\n{'─'*60}")
        print(f"👤 用户：{user_input}")

        # 执行图
        result = workflow.invoke({
            "user_input": user_input,
            "category": "",
            "response": "",
            "steps": [],
        })

        print(f"🤖 回复：{result['response']}")
        print(f"📍 路径：{' → '.join(result['steps'])}")

    print(f"\n{'='*60}")
    print("✅ LangGraph 的核心就是：节点 + 边 + 状态")
    print("   节点 = 处理逻辑（函数）")
    print("   边 = 流转规则（条件路由）")
    print("   状态 = 贯穿全图的数据（每个节点都能读写）")
    print("")
