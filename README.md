# AI Agent 开发学习手册

> 从零到能独立实现一个 Agent 平台。
> 适合：前端扎实、Python 入门水平的同学。

## 学习路线总览

```
阶段 0  环境准备          ← 30 分钟
  │
阶段 1  LLM 基础调用      ← 1-2 天    01_LLM基础调用/
  │
阶段 2  Agent 核心模式    ← 2-3 天    02_Agent核心/
  │
阶段 3  工具调用          ← 1-2 天    03_工具调用/
  │
阶段 4  异步任务平台      ← 3-5 天    04_异步任务平台/
  │
阶段 5  LangGraph 编排    ← 2-3 天    05_LangGraph编排/
  │
阶段 6  进阶优化          ← 按需      06_进阶优化/
```

## 每个文件夹里有什么

| 文件夹 | 学什么 |
|---|---|
| `01_LLM基础调用/` | 调通大模型 API、结构化输出 |
| `02_Agent核心/` | BaseAgent、具体 Agent、工厂模式 |
| `03_工具调用/` | Function Calling、AI 决定调哪个函数 |
| `04_异步任务平台/` | FastAPI + 队列 + Worker 完整链路 |
| `05_LangGraph编排/` | 多步流程图、状态流转 |
| `06_进阶优化/` | LLM 抽象层、内存回收、Token 追踪 |

## 运行前准备（阶段 0）

### 1. 安装 Python

```bash
# macOS 自带 python3，确认版本 >= 3.11
python3 --version

# 如果版本太低，用 Homebrew 安装
brew install python@3.13
```

### 2. 创建虚拟环境 + 安装依赖

```bash
# 在 AI-Agent学习手册/ 目录下执行
python3 -m venv .venv
source .venv/bin/activate

# 一键安装所有依赖
pip install -r requirements.txt
```

### 3. 配置 API Key

打开根目录的 **`config.py`**，把 `API_KEY` / `BASE_URL` / `MODEL` 替换成你自己的。
所有文件共用这一个配置，只需填一次。

> 没有 Key 可以去火山引擎控制台申请豆包的，或用 OpenAI 的。

### 4. 运行方式

```bash
source .venv/bin/activate

# 从学习手册根目录运行（这样 config.py 才能被找到）
cd ~/Desktop/AI-Agent学习手册
python 01_LLM基础调用/01_最小调用.py
```

## 学习方法

1. **先跑通，再读代码**。每个文件开头都有"运行方式"。
2. **看注释里的"前端类比"**。每个核心概念都用了前端知识做类比。
3. **跑通后改一改**。改 prompt、改参数、加个新工具——改坏了再修回来。
4. **每完成一个阶段，在下面打勾**。

## 进度自检

- [ ] 阶段 0：Python 环境装好，`pip install openai` 不报错
- [ ] 阶段 1：能调通大模型，拿到 JSON 格式的返回
- [ ] 阶段 2：能自己写一个继承 BaseAgent 的 Agent
- [ ] 阶段 3：能让 AI 自己决定调用哪个工具
- [ ] 阶段 4：有一个能通过 HTTP 提交任务、异步执行、查询结果的最小平台
- [ ] 阶段 5：能用 LangGraph 串一个多步流程
- [ ] 阶段 6：理解运行时回收和 LLM 抽象层的设计


> Agent 没那么玄，本质就是"调模型 + 解析返回 + 按规则处理"。
> 你前端天天做的"调接口 + 解析响应 + 渲染页面"，换个皮就是 Agent。
