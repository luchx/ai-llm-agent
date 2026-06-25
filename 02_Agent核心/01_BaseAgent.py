"""
================================================================
阶段 2-1：Agent 基类 —— 定义所有 Agent 的"接口规范"
================================================================

【这个文件教会你什么】
  所有 Agent 都必须遵循同一个接口：process()、get_required_fields()、get_description()。
  这就是"面向接口编程"——平台不关心你具体怎么实现，只关心你有没有这三个方法。

  app/agent/base_agent.py  ← 几乎一模一样

【前端类比】
  就像你定义一个 React 组件的 Props 接口：
  interface AgentProps {
    process(input: InputJSON): AgentResult
    getRequiredFields(): string[]
    getDescription(): string
  }
  所有组件（Agent）都必须实现这个接口。

【运行方式】
  这个文件主要是定义，不需要单独运行。
  直接看 02_问卷检查Agent.py 就是基于这个基类实现的。
================================================================
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
# Pydantic：数据验证库，前端类比就像 TypeScript 的 interface + 运行时校验
# 你定义一个 class，它自动帮你验证每个字段的类型


# ========== 第 1 部分：定义 Agent 的返回结果结构 ==========
# 前端类比：就像你定义一个接口 { success, data, error, metadata }
class AgentResult(BaseModel):
    """
    Agent 执行结果的标准格式。
    所有 Agent 都返回这个结构，这样上层代码可以用统一方式处理结果。

    前端类比：后端接口统一返回 { code, data, message }
    """
    success: bool                                    # 是否成功
    result: Any                                      # 具体结果（每个 Agent 不同）
    error_message: Optional[str] = None              # 错误信息（失败时才有）
    metadata: Optional[Dict[str, Any]] = None        # 额外信息（如 token 用量、耗时等）
    execution_time: Optional[float] = None           # 执行耗时（秒）
    token_usage: Optional[Dict[str, int]] = None     # Token 使用量（输入/输出/总计）
    cost: Optional[float] = None                     # 本次调用成本（元）


# ========== 第 2 部分：定义 Agent 的接口（抽象基类） ==========
# ABC = Abstract Base Class，表示这个类不能直接实例化，必须被继承
class BaseAgent(ABC):
    """
    Agent 抽象基类。所有 Agent 都必须继承它并实现三个方法。

    为什么用抽象基类？
    - 强制要求子类实现特定方法（不实现就报错）
    - 平台可以统一调用所有 Agent，不关心具体实现

    前端类比：就像你定义一个 abstract class Component，
    所有页面组件都必须实现 render() 方法。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agent_type = self.__class__.__name__  # 自动获取类名作为 agent_type

    @abstractmethod
    def process(self, input_json: Dict[str, Any]) -> AgentResult:
        """
        【核心方法】处理输入数据，返回结构化结果。
        每个 Agent 的业务逻辑就写在这里。

        参数：
            input_json: 业务输入数据（每个 Agent 不同）
        返回：
            AgentResult: 统一格式的结果

        前端类比：这就是组件的 render() 方法——你在这里写业务逻辑。
        """
        pass  # pass 表示"子类必须自己实现"

    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        返回这个 Agent 需要的输入字段列表。
        用于输入校验——如果调用方少了字段，直接报错。

        前端类比：就像 TypeScript 的 Required<Pick<Input, 'name' | 'age'>>
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        返回 Agent 的描述信息。
        用于文档生成、API 返回可用 Agent 列表等。

        前端类比：就像组件的 displayName + 注释
        """
        pass

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """
        验证输入数据是否包含所有必需字段。
        不需要子类重写，基类已经实现了。

        前端类比：就像一个通用的 form.validate() 函数
        """
        required_fields = self.get_required_fields()
        missing_fields = [f for f in required_fields if f not in input_json]
        if missing_fields:
            raise ValueError(f"缺少必需字段: {missing_fields}")

    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取 Agent 的元信息（类型、描述、必需字段等）。
        用于 API 返回 Agent 列表。

        前端类比：就像一个组件的 getMetadata() 方法
        """
        return {
            "agent_type": self.agent_type,
            "description": self.get_description(),
            "required_fields": self.get_required_fields(),
            "config": self.config,
        }


# ========== 第 3 部分：自定义异常类 ==========
# 前端类比：就像你自定义的 ApiError、ValidationError 等
class UnsupportedAgentError(Exception):
    """不支持的 Agent 类型（工厂找不到对应的 Agent）"""
    pass

class ValidationError(Exception):
    """输入验证失败（缺少必需字段）"""
    pass

class ProcessingError(Exception):
    """Agent 处理过程出错（LLM 调用失败等）"""
    pass


# ========== 演示：不实现抽象方法会怎样 ==========
if __name__ == "__main__":
    print("=" * 55)
    print("阶段 2-1：Agent 基类演示")
    print("=" * 55)

    # 尝试直接实例化 BaseAgent（会报错，因为它是抽象类）
    try:
        agent = BaseAgent()
    except TypeError as e:
        print(f"\n❌ 直接实例化 BaseAgent 报错了：{e}")
        print("   这说明你必须继承它并实现三个方法才能用。")

    # 演示 AgentResult 的用法
    result = AgentResult(
        success=True,
        result={"is_exist": 1, "category": "房产降价"},
        execution_time=1.5,
        token_usage={"input": 100, "output": 50, "total": 150},
        cost=0.001,
    )
    print(f"\n✅ AgentResult 示例：{result.model_dump_json(indent=2)}")
    print("\n→ 接下来看 02_问卷检查Agent.py，看一个真实的 Agent 是怎么实现的。")
