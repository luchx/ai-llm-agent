# 阶段 6：进阶优化

## 目标
理解 llm-agent 在生产环境中的工程优化。

## 文件说明

| 文件 | 内容 |
|---|---|---|
| `01_LLM抽象层.py` | 统一接口调不同模型 + Token 追踪 | `app/llm/service.py` + `tracker.py` |
| `02_运行时管理.py` | 执行预算 + 进程回收 + 内存裁剪 | `app/runtime/agent_runtime.py` |

## 运行顺序

```bash
python 06_进阶优化/01_LLM抽象层.py
python 06_进阶优化/02_运行时管理.py
```

## 学完后你应该能回答

- [ ] LLM 抽象层解决了什么问题？
- [ ] 执行预算（信号量）怎么防止雪崩？
- [ ] 为什么 gc.collect() 还不够，还需要 malloc_trim？
- [ ] 进程回收的触发条件是什么？
