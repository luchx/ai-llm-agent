"""
================================================================
阶段 2-3：Agent 工厂 —— 根据类型字符串动态创建 Agent
================================================================

【这个文件教会你什么】
  平台有十几种 Agent。当一个任务进来说"我要 ai_question_check"，
  工厂负责找到对应的 Agent 类并创建实例。

  这就是"工厂模式"——调用方不需要知道具体是哪个类，
  只需要告诉工厂一个类型字符串，工厂帮你搞定一切。

  app/agent/factory.py  ← 核心逻辑几乎一样

【前端类比】
  就像你写的动态组件渲染：
    const Component = componentMap[type]
    return <Component {...props} />
  或者一个 createComponent(type) 函数。

【运行方式】
  python 02_Agent核心/03_Agent工厂.py
================================================================
"""

import importlib
import sys
import os
from typing import Dict, Any, Optional, Type

# 导入基类
sys.path.insert(0, os.path.dirname(__file__))
from _01_BaseAgent import BaseAgent, AgentResult, UnsupportedAgentError


# ========== 第 1 部分：注册表 ==========
# 这是一个"类型字符串 → 类路径"的映射表。
#
# 为什么存字符串路径而不是直接 import？
# 因为用到哪个才加载哪个（懒加载），不启动时全量 import，
# 这样可以降低 Worker 启动时的内存占用。
# 前端类比：就像 React.lazy(() => import('./MyComponent')) 的懒加载。
BUILTIN_AGENT_PATHS: Dict[str, str] = {
    "question_check": "02_问卷检查Agent.QuestionCheckAgent",
    # 你以后写的其他 Agent 也在这里注册：
    # "message_summary": "agents.message_summary_agent.MessageSummaryAgent",
    # "knowledge_base": "agents.kb_agent.KnowledgeBaseAgent",
}


class AgentFactory:
    """
    Agent 工厂：根据 agent_type 字符串动态创建 Agent 实例。

    核心能力：
    1. 懒加载：用到哪个 Agent 才 import 哪个，不全量加载
    2. 三种注册来源：内置映射表、YAML 配置、运行时动态注册
    3. 实例复用：支持缓存 Agent 实例，避免重复创建


    """

    def __init__(self):
        # 已注册的 Agent 类（缓存，避免重复 import）
        # 前端类比：就像一个 componentCache 对象
        self._registry: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_type: str, agent_class: Type[BaseAgent]):
        """
        手动注册一个 Agent 类。
        用于运行时动态注册新 Agent，不需要重启服务。

        """
        self._registry[agent_type] = agent_class
        print(f"  📝 注册 Agent: {agent_type} → {agent_class.__name__}")

    def _load_class(self, class_path: str, agent_type: str) -> Type[BaseAgent]:
        """
        根据类路径字符串，动态 import 并返回类对象。
        这是懒加载的核心：只在第一次需要时才 import。

        class_path 格式："模块路径.类名"
        例如："02_问卷检查Agent.QuestionCheckAgent"


        """
        # 拆分模块路径和类名
        # "02_问卷检查Agent.QuestionCheckAgent" → module="02_问卷检查Agent", class="QuestionCheckAgent"
        module_path, class_name = class_path.rsplit(".", 1)

        # importlib.import_module 就是动态 import
        # 前端类比：就像 import(`./agents/${modulePath}.js`)
        try:
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"无法加载 Agent {agent_type} ({class_path}): {e}")

        # 确保它确实是 BaseAgent 的子类
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"{class_name} 必须继承 BaseAgent")

        # 加入缓存，下次直接用
        self.register(agent_type, agent_class)
        return agent_class

    def create(self, agent_type: str, config: Optional[Dict[str, Any]] = None) -> BaseAgent:
        """
        【核心方法】根据 agent_type 创建 Agent 实例。

        查找顺序：
        1. 先看缓存（已经 import 过的）
        2. 再看内置映射表（BUILTIN_AGENT_PATHS）
        3. 都没有就报错


        """
        # 第 1 步：看缓存里有没有
        if agent_type in self._registry:
            agent_class = self._registry[agent_type]
        # 第 2 步：看内置映射表
        elif agent_type in BUILTIN_AGENT_PATHS:
            class_path = BUILTIN_AGENT_PATHS[agent_type]
            agent_class = self._load_class(class_path, agent_type)
        else:
            raise UnsupportedAgentError(
                f"不支持的 Agent 类型: {agent_type}\n"
                f"已注册的类型: {list(self._registry.keys()) + list(BUILTIN_AGENT_PATHS.keys())}"
            )

        # 创建实例并返回
        return agent_class(config=config)

    def list_agents(self) -> Dict[str, str]:
        """列出所有可用的 Agent 类型及其描述"""
        result = {}
        all_types = set(list(self._registry.keys()) + list(BUILTIN_AGENT_PATHS.keys()))
        for agent_type in all_types:
            try:
                agent = self.create(agent_type)
                result[agent_type] = agent.get_description()
            except Exception as e:
                result[agent_type] = f"(加载失败: {e})"
        return result


# ========== 运行演示 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("阶段 2-3：Agent 工厂 —— 动态创建 Agent")
    print("=" * 60)

    factory = AgentFactory()

    # 第 1 步：列出所有可用的 Agent
    print("\n📋 可用的 Agent 类型：")
    agents = factory.list_agents()
    for agent_type, desc in agents.items():
        print(f"  • {agent_type}: {desc}")

    # 第 2 步：用工厂创建 Agent（调用方不需要知道具体是哪个类）
    print(f"\n{'='*60}")
    print("用工厂创建 Agent 并执行任务：")

    # 调用方只需要传一个字符串，工厂帮你找到对应的类并创建实例
    # 前端类比：const Component = componentMap[type]
    agent = factory.create("question_check")

    result = agent.process({
        "question": "您对小区满意吗？",
        "answer": "小区门口的路一直在修，出行很不方便。",
    })
    print(f"  agent_type: question_check")
    print(f"  结果：{result.result}")

    # 第 3 步：动态注册新 Agent
    print(f"\n{'='*60}")
    print("动态注册一个新 Agent：")

    class SimpleEchoAgent(BaseAgent):
        """一个最简单的 Agent，原样返回输入（用于测试）"""
        def process(self, input_json):
            return AgentResult(success=True, result={"echo": input_json})
        def get_required_fields(self):
            return ["message"]
        def get_description(self):
            return "回声Agent - 原样返回输入（测试用）"

    # 动态注册
    factory.register("echo", SimpleEchoAgent)

    # 现在可以用 "echo" 类型创建了
    echo_agent = factory.create("echo")
    echo_result = echo_agent.process({"message": "hello"})
    print(f"  echo 结果：{echo_result.result}")

    print(f"\n{'='*60}")
    print("✅ 工厂模式的核心就三点：")
    print("   1. 注册表：字符串 → 类的映射")
    print("   2. 懒加载：用到才 import，省内存")
    print("   3. 统一创建接口：调用方只传类型字符串")
    print("。")
