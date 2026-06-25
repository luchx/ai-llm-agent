# 阶段 5：LangGraph 编排

## 目标
当任务需要多步处理时，用 LangGraph 的"图"来编排流程。

## 文件说明

| 文件 | 内容 | 对应 llm-agent |
|---|---|---|
| `01_简单图.py` | 分类路由：根据输入走不同分支 | `app/graph/` |
| `02_问卷分析图.py` | 真实业务：预处理 → 关键词 → LLM → 合并 | `app/agent/identify_answer/workflow.py` |

## 运行顺序

```bash
pip install langchain langgraph

python 05_LangGraph编排/01_简单图.py
python 05_LangGraph编排/02_问卷分析图.py
```

## 学完后你应该能回答

- [ ] LangGraph 的三个核心概念是什么？
- [ ] 条件路由（conditional edges）怎么工作？
- [ ] 为什么要用图而不是 if-else？
