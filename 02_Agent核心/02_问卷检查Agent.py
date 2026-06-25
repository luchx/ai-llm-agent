"""
================================================================
阶段 2-2：问卷检查 Agent —— 你的第一个完整 Agent
================================================================

【这个文件教会你什么】
  继承 BaseAgent，实现一个真正的 Agent：输入问卷回答 → 调 LLM 判断 → 返回结构化结果。
  这就是真实项目里最核心的业务逻辑。

  app/agent/question_check_agent.py  ← 几乎一模一样的逻辑
  可以打开那个文件对照着看，你会发现自己写的和团队写的结构完全一致。

【前端类比】
  就像你写一个 React 组件：
  - Props 接口 = get_required_fields()（这个组件需要什么数据）
  - render() = process()（这个组件怎么处理数据、怎么渲染结果）
  - displayName = get_description()（这个组件是干嘛的）

【运行方式】
  python 02_Agent核心/02_问卷检查Agent.py
================================================================
"""

import json
import time
from typing import Dict, Any, List

# 从 01_BaseAgent.py 导入基类和结果结构
# 前端类比：就像 import { BaseComponent } from './BaseComponent'
from importlib import import_module
import sys
import os

# 把上级目录加入路径，这样能 import 同阶段的其他文件
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _01_BaseAgent import BaseAgent, AgentResult, ProcessingError

from config import API_KEY, BASE_URL, MODEL, get_client

client = get_client()


# ========== System Prompt ==========
# 这是 Agent 的"大脑"，Prompt 写得好不好直接决定 Agent 聪不聪明。
# 好的 Prompt 有三个特点：
#   1. 明确告诉 AI 它的角色和任务
#   2. 列清楚所有分类和关键词
#   3. 强制要求返回固定 JSON 格式
SYSTEM_PROMPT = """你是一位专业的问卷分析专家，你的任务是分析用户的问卷回答。

你需要判断回答是否涉及以下四类问题：
1. 房产车位降价 - 关键词：降价、便宜、价格、车位、房产、贬值、亏
2. 市政道路 - 关键词：道路、交通、路况、堵车、修路、街道
3. 市政供暖 - 关键词：供暖、暖气、取暖、供热、暖器、温度
4. 周边配套 - 关键词：配套、设施、学校、医院、商场、公园、超市

请严格按以下 JSON 格式返回，不要返回任何其他文字：
{
    "is_exist": 1,
    "method": "llm",
    "confidence": "high",
    "categories_detected": ["房产车位降价"],
    "reason": "用户提到'比别人买的贵'，涉及房产价格问题"
}

说明：
- is_exist: 1=存在问题, 2=不存在问题
- method: 固定填 "llm"
- confidence: "high"=非常确定, "medium"=比较确定, "low"=不太确定
- categories_detected: 检测到的类别数组，没有则为 []
- reason: 一句话说明判断理由"""


# ========== 关键词降级方案 ==========
# 当 LLM 不可用时，用关键词匹配做兜底。
# 为什么要降级？因为 LLM 可能超时、限流、宕机，但业务不能停。
# 前端类比：接口超时后用本地缓存兜底。
KEYWORD_RULES = {
    "房产车位降价": ["降价", "便宜", "价格", "车位", "房产", "贬值", "亏"],
    "市政道路": ["道路", "交通", "路况", "堵车", "修路", "街道"],
    "市政供暖": ["供暖", "暖气", "取暖", "供热", "暖器", "温度"],
    "周边配套": ["配套", "设施", "学校", "医院", "商场", "公园", "超市"],
}


class QuestionCheckAgent(BaseAgent):
    """
    问卷问题检查 Agent。

    功能：分析用户的问卷回答，判断是否涉及四类敏感问题。
    输入：{ "question": "问题文本", "answer": "回答文本" }
    输出：{ "is_exist": 1/2, "method": "llm"/"keyword", "confidence": "...", ... }

。
    """

    def get_required_fields(self) -> List[str]:
        """告诉平台：我需要 question 和 answer 两个字段"""
        return ["question", "answer"]

    def get_description(self) -> str:
        """告诉平台：我是干嘛的"""
        return "问卷问题检查Agent - 分析问卷回答是否涉及房产降价、市政道路、市政供暖、周边配套四类问题"

    def process(self, input_json: Dict[str, Any]) -> AgentResult:
        """
        【核心方法】处理问卷回答。

        流程：
        1. 校验输入
        2. 判断是单条还是批量
        3. 调 LLM 分析每条回答
        4. 如果 LLM 失败，降级到关键词匹配
        5. 返回结构化结果


        """
        start_time = time.time()

        # 第 1 步：校验输入（基类已经实现了 validate_input）
        self.validate_input(input_json)

        question = input_json["question"]
        answer = input_json["answer"]

        try:
            # 第 2 步：判断是单条回答还是批量回答
            # 前端类比：就像你判断 props.data 是单个对象还是数组
            if isinstance(answer, list):
                # 批量模式：逐条处理
                results = []
                for item in answer:
                    text = item.get("answer", "") if isinstance(item, dict) else str(item)
                    single_result = self._check_single(question, text)
                    results.append(single_result)

                return AgentResult(
                    success=True,
                    result={
                        "total": len(results),
                        "results": results,
                        "summary": self._make_summary(results),
                    },
                    execution_time=time.time() - start_time,
                )
            else:
                # 单条模式
                result = self._check_single(question, str(answer))
                return AgentResult(
                    success=True,
                    result=result,
                    execution_time=time.time() - start_time,
                )

        except Exception as e:
            # 任何异常都返回失败结果，不要让整个 Agent 崩掉
            # 前端类比：try-catch 包住请求，出错时显示兜底 UI
            return AgentResult(
                success=False,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time,
            )

    def _check_single(self, question: str, answer_text: str) -> dict:
        """
        检查单条回答。先试 LLM，失败了降级到关键词。

        """
        # 先试 LLM
        try:
            return self._llm_check(question, answer_text)
        except Exception as e:
            print(f"  ⚠️ LLM 调用失败({e})，降级到关键词匹配")
            return self._keyword_check(answer_text)

    def _llm_check(self, question: str, answer_text: str) -> dict:
        """
        调用 LLM 进行分析。

        """
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"问题：{question}\n回答：{answer_text}"},
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        # 清理可能的 markdown 代码块标记
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        result = json.loads(raw)
        result["method"] = "llm"
        return result

    def _keyword_check(self, answer_text: str) -> dict:
        """
        关键词降级方案。

        """
        detected = []
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                if kw in answer_text:
                    detected.append(category)
                    break

        return {
            "is_exist": 1 if detected else 2,
            "method": "keyword",
            "confidence": "medium",
            "categories_detected": detected,
            "reason": "关键词匹配" + ("命中" + ", ".join(detected) if detected else "未命中"),
        }

    def _make_summary(self, results: list) -> dict:
        """生成批量处理的统计摘要"""
        total = len(results)
        success = sum(1 for r in results if r.get("is_exist") == 1)
        return {
            "total": total,
            "detected_count": success,
            "detection_rate": f"{success/total*100:.1f}%" if total else "0%",
        }


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 2-2：问卷检查 Agent —— 你的第一个完整 Agent")
    print("=" * 60)

    # 创建 Agent 实例
    agent = QuestionCheckAgent()

    # 展示 Agent 信息
    info = agent.get_agent_info()
    print(f"\n📋 Agent 信息：")
    print(f"   类型：{info['agent_type']}")
    print(f"   描述：{info['description']}")
    print(f"   必需字段：{info['required_fields']}")

    # 测试单条
    print(f"\n{'='*60}")
    print("单条测试：")
    test_input = {
        "question": "您对小区的整体满意度如何？",
        "answer": "因为别人买的比我便宜，我买的比较贵。",
    }
    result = agent.process(test_input)
    print(f"  输入：{test_input['answer']}")
    print(f"  结果：{json.dumps(result.model_dump(), ensure_ascii=False, indent=2)}")

    # 测试批量
    print(f"\n{'='*60}")
    print("批量测试：")
    batch_input = {
        "question": "您对小区有什么不满意的地方？",
        "answer": [
            {"mobile": "138****1234", "answer": "暖气不热，冬天在家穿棉袄"},
            {"mobile": "139****5678", "answer": "物业服务态度很好，很满意"},
            {"mobile": "137****9012", "answer": "学校太远了，配套不行"},
        ],
    }
    batch_result = agent.process(batch_input)
    print(f"  结果：{json.dumps(batch_result.model_dump(), ensure_ascii=False, indent=2)}")

    print(f"\n{'='*60}")
    print("✅ 你刚刚写了一个完整的 Agent！")
    print("   结构是不是一模一样？你现在能看懂团队的代码了。")
