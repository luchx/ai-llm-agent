# 阶段 1：LLM 基础调用

## 目标
学会用 Python 调通大模型 API，拿到结构化返回。

## 文件说明

| 文件 | 内容 | 对应 llm-agent |
|---|---|---|
| `01_最小调用.py` | 发一句话给大模型，拿回回复 | `app/llm/myopenai_client.py` |
| `02_结构化输出.py` | 让模型返回固定 JSON 格式 | 所有 Agent 的 prompt 设计 |
| `03_多轮对话.py` | 带上下文的多轮对话 | `app/agent/kf_chat_task/core/context_manager.py` |

## 运行顺序

```bash
source ../.venv/bin/activate   # 如果虚拟环境在上级目录

# 1. 最小调用
python 01_LLM基础调用/01_最小调用.py

# 2. 结构化输出
python 01_LLM基础调用/02_结构化输出.py

# 3. 多轮对话
python 01_LLM基础调用/03_多轮对话.py
```

## 学完后你应该能回答

- [ ] 大模型 API 的调用流程是什么？
- [ ] temperature 参数是干嘛的？
- [ ] 为什么要让 AI 返回 JSON 而不是自由文本？
- [ ] AI 是怎么"记住"上下文的？
