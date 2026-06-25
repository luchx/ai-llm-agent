# 阶段 2：Agent 核心模式

## 目标
理解 Agent 的三层设计：基类定义接口 → 具体 Agent 实现逻辑 → 工厂模式动态创建。

## 文件说明

| 文件 | 内容 | 对应 llm-agent |
|---|---|---|
| `01_BaseAgent.py` | Agent 抽象基类，定义接口 | `app/agent/base_agent.py` |
| `02_问卷检查Agent.py` | 最简单的 Agent 实现 | `app/agent/question_check_agent.py` |
| `03_Agent工厂.py` | 根据类型字符串动态创建 Agent | `app/agent/factory.py` |
| `_01_BaseAgent.py` | 基类的可导入副本（给其他文件用） | - |

## 运行顺序

```bash
# 01 主要是定义，阅读理解即可
# python 02_Agent核心/01_BaseAgent.py

# 02 运行问卷检查 Agent
python 02_Agent核心/02_问卷检查Agent.py

# 03 运行工厂模式
python 02_Agent核心/03_Agent工厂.py
```

## 学完后你应该能回答

- [ ] BaseAgent 的三个抽象方法是什么？
- [ ] 工厂模式的懒加载是什么意思？为什么要懒加载？
- [ ] 关键词降级策略的作用是什么？
