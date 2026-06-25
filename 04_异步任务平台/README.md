# 阶段 4：异步任务平台

## 目标
把 Agent 包装成一个完整的 HTTP 异步任务平台。这是 llm-agent 的核心架构。

## 文件说明

| 文件 | 内容 | 对应 llm-agent |
|---|---|---|
| `01_FastAPI接口.py` | 同步版本的 Web 接口 | `app/api/v1/task.py` |
| `02_完整平台.py` | 异步任务平台（API + 队列 + Worker） | 整个 llm-agent 的最小复刻 |

## 运行顺序

```bash
pip install fastapi uvicorn

# 1. 同步版本（先理解接口设计）
python 04_异步任务平台/01_FastAPI接口.py
# 打开 http://localhost:8000/docs 查看 Swagger

# 2. 异步版本（完整平台）
python 04_异步任务平台/02_完整平台.py
```

## 学完后你应该能回答

- [ ] "请求-ID 异步模式"是什么？
- [ ] 为什么 LLM 任务不能同步处理？
- [ ] Worker 的工作循环是什么？
