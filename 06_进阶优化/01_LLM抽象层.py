"""
================================================================
阶段 6-1：LLM 抽象层 —— 换模型不改业务代码
================================================================

【这个文件教会你什么】
  把"调用大模型"封装成统一接口。今天用豆包，明天想换 OpenAI、
  或者换本地的 Ollama，业务代码一行都不用改。

  这是工程化的关键设计：业务逻辑和基础设施解耦。

【对应 llm-agent】
  app/llm/service.py       ← LLM Provider 抽象层
  app/llm/myopenai_client.py ← 具体的 OpenAI 兼容客户端
  app/llm/tracker.py       ← Token 追踪

【前端类比】
  就像你封装 axios 实例：
  const http = axios.create({ baseURL: '...' })
  换 baseURL 不影响业务代码。
  这里就是换 LLM Provider 不影响 Agent 代码。

【运行方式】
  python 06_进阶优化/01_LLM抽象层.py
================================================================
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


# ========== 第 1 部分：定义统一的返回结构 ==========
# 对照 llm-agent：app/llm/tracker.py 里的 TokenUsage
@dataclass
class LLMResponse:
    """
    LLM 调用的统一返回格式。
    不管用哪个模型，返回的都是这个结构。
    前端类比：就像后端统一返回 { code, data, message }
    """
    content: str                           # 模型的回复文本
    model: str                             # 实际使用的模型名
    input_tokens: int = 0                  # 输入 token 数
    output_tokens: int = 0                 # 输出 token 数
    total_tokens: int = 0                  # 总 token 数
    cost: float = 0.0                      # 本次调用成本（元）
    latency: float = 0.0                   # 调用耗时（秒）


# ========== 第 2 部分：定义 LLM Provider 接口 ==========
# 对照 llm-agent：app/llm/service.py 里的 BaseLLMProvider
class BaseLLMProvider(ABC):
    """
    LLM Provider 抽象基类。
    所有具体的 LLM 实现都必须继承它。

    这样做的好处：
    - 业务代码只调 chat() 方法，不关心底层用的哪个模型
    - 换模型只需要换 Provider，业务代码零修改
    - 可以统一做 Token 统计、超时、重试、日志

    前端类比：就像你定义一个 interface HttpClient { get(), post() }
    然后有 AxiosClient、FetchClient 等不同实现。
    """

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """发送对话请求，返回 LLMResponse"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """返回当前使用的模型名"""
        pass


# ========== 第 3 部分：实现具体的 Provider ==========

class DoubaoProvider(BaseLLMProvider):
    """
    豆包（字节跳动）Provider。
    对照 llm-agent：app/llm/myopenai_client.py
    """
    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def get_model_name(self) -> str:
        return self.model

    def chat(self, messages, temperature=0.7, **kwargs) -> LLMResponse:
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        latency = time.time() - start

        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            cost=self._calculate_cost(usage),
            latency=latency,
        )

    def _calculate_cost(self, usage) -> float:
        """计算 Token 成本（不同模型单价不同）"""
        if not usage:
            return 0.0
        # 豆包 1.5-pro 的示例价格（实际价格查官方文档）
        input_price = 0.0008 / 1000   # 每千 token 0.0008 元
        output_price = 0.002 / 1000   # 每千 token 0.002 元
        return usage.prompt_tokens * input_price + usage.completion_tokens * output_price


class MockProvider(BaseLLMProvider):
    """
    模拟 Provider（不需要真实 API Key，用于学习和测试）。
    前端类比：就像 mock 数据的 API 层
    """
    def get_model_name(self) -> str:
        return "mock-model"

    def chat(self, messages, temperature=0.7, **kwargs) -> LLMResponse:
        # 模拟回复
        last_msg = messages[-1]["content"] if messages else ""
        mock_content = json.dumps({
            "is_exist": 1,
            "confidence": "high",
            "categories_detected": ["模拟分类"],
            "reason": f"模拟分析：'{last_msg[:30]}'"
        }, ensure_ascii=False)

        return LLMResponse(
            content=mock_content,
            model="mock-model",
            input_tokens=50,
            output_tokens=30,
            total_tokens=80,
            cost=0.0,
            latency=0.1,
        )


# ========== 第 4 部分：LLM 工厂 ==========
# 对照 llm-agent：app/llm/factory.py
class LLMFactory:
    """
    LLM 工厂：根据配置创建不同的 Provider。
    业务代码通过工厂获取 Provider，不直接 import 具体实现。
    """
    _providers = {}

    @classmethod
    def register(cls, name: str, provider: BaseLLMProvider):
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str = "default") -> BaseLLMProvider:
        if name not in cls._providers:
            raise ValueError(f"未注册的 LLM Provider: {name}")
        return cls._providers[name]

    @classmethod
    def chat(cls, messages, temperature=0.7, provider_name="default") -> LLMResponse:
        """快捷方法：一步完成 LLM 调用"""
        return cls.get(provider_name).chat(messages, temperature)


# ========== 第 5 部分：Token 追踪中间件 ==========
# 对照 llm-agent：app/llm/tracker.py
class TokenTracker:
    """
    Token 用量追踪器。
    记录每次 LLM 调用的 Token 用量和成本。
    前端类比：就像你封装的 axios 拦截器，自动记录请求耗时和错误。
    """
    def __init__(self):
        self.records: list = []

    def track(self, response: LLMResponse, task_id: str = ""):
        """记录一次 LLM 调用"""
        record = {
            "task_id": task_id,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "total_tokens": response.total_tokens,
            "cost": response.cost,
            "latency": response.latency,
        }
        self.records.append(record)

    def get_summary(self) -> dict:
        """获取汇总统计"""
        if not self.records:
            return {"total_calls": 0}
        return {
            "total_calls": len(self.records),
            "total_tokens": sum(r["total_tokens"] for r in self.records),
            "total_cost": sum(r["cost"] for r in self.records),
            "avg_latency": sum(r["latency"] for r in self.records) / len(self.records),
        }


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 6-1：LLM 抽象层 —— 换模型不改业务代码")
    print("=" * 60)

    # 注册 Mock Provider（不需要 API Key）
    LLMFactory.register("default", MockProvider())

    # Token 追踪器
    tracker = TokenTracker()

    # 业务代码完全不关心用的哪个模型
    # 前端类比：const res = await http.post('/chat', data)
    print("\n📝 业务代码调用 LLM（不关心底层是哪个模型）：")
    print("-" * 60)

    test_messages = [
        [
            {"role": "system", "content": "你是问卷分析专家"},
            {"role": "user", "content": "分析：暖气不热，冬天在家还要穿棉袄"},
        ],
        [
            {"role": "system", "content": "你是问卷分析专家"},
            {"role": "user", "content": "分析：你们的服务态度很好"},
        ],
    ]

    for i, messages in enumerate(test_messages, 1):
        response = LLMFactory.chat(messages)
        tracker.track(response, task_id=f"task-{i}")

        print(f"\n  调用 {i}:")
        print(f"    输入：{messages[-1]['content'][:30]}...")
        print(f"    返回：{response.content[:50]}...")
        print(f"    Token：{response.total_tokens} (输入:{response.input_tokens} 输出:{response.output_tokens})")
        print(f"    成本：¥{response.cost:.6f}")
        print(f"    耗时：{response.latency:.2f}s")

    # 汇总统计
    summary = tracker.get_summary()
    print(f"\n{'='*60}")
    print(f"📊 汇总统计：")
    print(f"   总调用次数：{summary['total_calls']}")
    print(f"   总 Token 数：{summary['total_tokens']}")
    print(f"   总成本：¥{summary['total_cost']:.6f}")
    print(f"   平均耗时：{summary['avg_latency']:.2f}s")

    print(f"\n{'='*60}")
    print("✅ LLM 抽象层的核心价值：")
    print("   1. 业务代码只调 provider.chat()，不关心底层模型")
    print("   2. 换模型 = 换 Provider，业务代码零修改")
    print("   3. Token 追踪、成本统计、超时重试统一在 Provider 层处理")
    print("   对照 llm-agent/app/llm/ 三层设计：")
    print("   service.py（抽象层）→ myopenai_client.py（实现）→ tracker.py（追踪）")
