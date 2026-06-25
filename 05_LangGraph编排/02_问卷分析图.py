"""
================================================================
阶段 5-2：问卷分析图 —— 用 LangGraph 实现真实业务流程
================================================================

【这个文件教会你什么】
  用 LangGraph 实现一个真实的问卷分析流程：
  预处理 → LLM 分类 → 关键词验证 → 汇总输出

  这个模式对应 llm-agent 里最复杂的 Agent 设计思路。

【对应 llm-agent】
  app/agent/identify_answer/workflow.py  ← 问卷回答识别的 LangGraph 工作流
  app/agent/survey_analysis/            ← 满意度分析的 LangGraph 工作流

【运行方式】
  pip install langchain langgraph
  python 05_LangGraph编排/02_问卷分析图.py
================================================================
"""

import json
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


# ========== 状态定义 ==========
class SurveyState(TypedDict):
    question: str              # 问卷问题
    answer: str                # 用户回答
    cleaned_answer: str        # 清洗后的回答
    llm_result: dict           # LLM 分析结果
    keyword_result: dict       # 关键词分析结果
    final_result: dict         # 最终合并结果
    method_used: str           # 使用的方法（llm / keyword / hybrid）
    steps: list                # 执行路径记录


# ========== 关键词规则 ==========
KEYWORD_RULES = {
    "房产车位降价": ["降价", "便宜", "价格", "车位", "房产", "贬值", "亏"],
    "市政道路": ["道路", "交通", "路况", "堵车", "修路", "街道"],
    "市政供暖": ["供暖", "暖气", "取暖", "供热", "暖器"],
    "周边配套": ["配套", "设施", "学校", "医院", "商场", "公园", "超市"],
}


# ========== 节点实现 ==========

def preprocess_node(state: SurveyState) -> dict:
    """预处理：清洗文本"""
    answer = state["answer"].strip()
    # 去掉多余空白、特殊字符等
    cleaned = answer.replace("\n", " ").replace("\r", "")
    print(f"  🧹 预处理：'{answer[:30]}...' → 清洗完成")
    return {
        "cleaned_answer": cleaned,
        "steps": ["预处理"],
    }


def keyword_check_node(state: SurveyState) -> dict:
    """关键词检查：不依赖 LLM，纯规则匹配"""
    answer = state["cleaned_answer"]
    detected = []
    for category, keywords in KEYWORD_RULES.items():
        for kw in keywords:
            if kw in answer:
                detected.append(category)
                break

    result = {
        "is_exist": 1 if detected else 2,
        "categories": detected,
        "confidence": "high" if len(detected) >= 2 else ("medium" if detected else "high"),
    }
    print(f"  🔑 关键词检查：命中 {detected or '无'}")
    return {
        "keyword_result": result,
        "steps": state.get("steps", []) + [f"关键词→{detected or '无'}"],
    }


def merge_results_node(state: SurveyState) -> dict:
    """合并 LLM 和关键词的结果，取更可靠的"""
    kw = state.get("keyword_result", {})
    llm = state.get("llm_result", {})

    # 策略：如果关键词和 LLM 都检测到了，置信度最高
    # 如果只有一个检测到，用那个但降低置信度
    kw_categories = set(kw.get("categories", []))
    llm_categories = set(llm.get("categories", []))

    if kw_categories and llm_categories:
        # 两者都检测到 → 取并集，高置信度
        merged = list(kw_categories | llm_categories)
        confidence = "high"
        method = "hybrid"
    elif kw_categories:
        merged = list(kw_categories)
        confidence = "medium"
        method = "keyword"
    elif llm_categories:
        merged = list(llm_categories)
        confidence = "medium"
        method = "llm"
    else:
        merged = []
        confidence = "high"
        method = "keyword"

    final = {
        "is_exist": 1 if merged else 2,
        "categories_detected": merged,
        "confidence": confidence,
    }
    print(f"  📊 合并结果：categories={merged}, confidence={confidence}, method={method}")

    return {
        "final_result": final,
        "method_used": method,
        "steps": state.get("steps", []) + [f"合并→{method}"],
    }


def decide_next(state: SurveyState) -> Literal["merge_results", "llm_check"]:
    """
    决策节点：关键词检查后，是否需要进一步用 LLM 分析。

    策略：
    - 关键词已命中 → 直接合并（省 LLM 调用成本）
    - 关键词未命中 → 用 LLM 再检查一遍（可能有关键词覆盖不到的表达）

    对照 llm-agent：这就是"LLM 检测 + 关键词降级"策略的图化版本。
    """
    kw = state.get("keyword_result", {})
    if kw.get("categories"):
        print(f"  🔀 决策：关键词已命中，跳过 LLM（省钱！）")
        return "merge_results"
    else:
        print(f"  🔀 决策：关键词未命中，调用 LLM 进一步分析")
        return "llm_check"


def llm_check_node(state: SurveyState) -> dict:
    """
    LLM 检查节点。
    真实项目这里会调大模型 API，这里用更详细的关键词模拟。
    对照 llm-agent：question_check_agent.py 的 _llm_check 方法
    """
    answer = state["cleaned_answer"]

    # 模拟 LLM 的语义理解能力（比关键词更强）
    # 真实项目：client.chat.completions.create(...)
    semantic_indicators = {
        "房产车位降价": ["别人便宜", "买贵了", "不值", "掉价", "亏本"],
        "市政道路": ["出行不便", "路不好", "堵"],
        "市政供暖": ["冷", "不热", "穿棉袄"],
        "周边配套": ["不方便", "太远", "没有"],
    }

    detected = []
    for category, indicators in semantic_indicators.items():
        for indicator in indicators:
            if indicator in answer:
                detected.append(category)
                break

    result = {
        "is_exist": 1 if detected else 2,
        "categories": detected,
    }
    print(f"  🤖 LLM 分析：检测到 {detected or '无'}")

    return {
        "llm_result": result,
        "steps": state.get("steps", []) + [f"LLM→{detected or '无'}"],
    }


# ========== 构建图 ==========
graph_builder = StateGraph(SurveyState)

graph_builder.add_node("preprocess", preprocess_node)
graph_builder.add_node("keyword_check", keyword_check_node)
graph_builder.add_node("llm_check", llm_check_node)
graph_builder.add_node("merge_results", merge_results_node)

graph_builder.add_edge(START, "preprocess")
graph_builder.add_edge("preprocess", "keyword_check")
graph_builder.add_conditional_edges("keyword_check", decide_next)
graph_builder.add_edge("llm_check", "merge_results")
graph_builder.add_edge("merge_results", END)

workflow = graph_builder.compile()


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 5-2：问卷分析图 —— 真实业务的 LangGraph 编排")
    print("=" * 60)

    test_cases = [
        ("您对小区的整体满意度如何？", "因为别人买的比我便宜，我买的比较贵"),
        ("您对小区有什么不满意？", "你们的服务态度很好，我很满意"),
        ("您对小区有什么建议？", "暖气不热，冬天在家还要穿棉袄"),
        ("您对小区有什么看法？", "配套不行，学校太远了，医院也没有"),
    ]

    for question, answer in test_cases:
        print(f"\n{'─'*60}")
        print(f"📝 问题：{question}")
        print(f"💬 回答：{answer}")

        result = workflow.invoke({
            "question": question,
            "answer": answer,
            "cleaned_answer": "",
            "llm_result": {},
            "keyword_result": {},
            "final_result": {},
            "method_used": "",
            "steps": [],
        })

        print(f"📊 结果：{json.dumps(result['final_result'], ensure_ascii=False)}")
        print(f"📍 路径：{' → '.join(result['steps'])}")
        print(f"🔧 方法：{result['method_used']}")

    print(f"\n{'='*60}")
    print("✅ 关键设计点：")
    print("   1. 条件路由：关键词命中就跳过 LLM（省成本）")
    print("   2. 多策略合并：关键词 + LLM 结果取并集（更准确）")
    print("   3. 每步都记录路径（方便调试和监控）")
    print("   对照 llm-agent/identify_answer/workflow.py，一模一样的设计思路")
