# 阶段 3：工具调用（Function Calling）

## 目标
让 AI 自己决定调用哪个函数来完成任务。这是 Agent 和普通聊天机器人的核心区别。

## 文件说明

| 文件 | 内容 |
|---|---|---|
| `01_FunctionCalling.py` | 单工具调用的完整流程 | Agent 的 tool_calls 能力 |
| `02_多工具Agent.py` | 多工具并行调用 | `app/agent/kf_chat_task/` |

## 运行顺序

```bash
python 03_工具调用/01_FunctionCalling.py
python 03_工具调用/02_多工具Agent.py
```

## 学完后你应该能回答

- [ ] Function Calling 的 5 步流程是什么？
- [ ] AI 怎么决定什么时候该用工具？
- [ ] 工具的结果怎么喂回给 AI？
