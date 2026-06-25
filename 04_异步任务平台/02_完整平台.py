"""
================================================================
阶段 4-2：完整异步任务平台 —— llm-agent 的最小复刻
================================================================

【这个文件教会你什么】
  这是整个学习手册里最重要的文件之一。
  它用不到 300 行代码，复刻了 llm-agent 的核心架构：
  提交任务 → 返回 ID → 后台异步执行 → 轮询查询结果。

  这就是 llm-agent 的"请求-ID 异步模式"。

【对应 llm-agent 的完整链路】
  app/api/v1/task.py        → 提交接口 + 查询接口
  app/queue/functions.py    → 队列任务函数
  app/queue/worker.py       → Worker 启动
  app/runtime/agent_runtime.py → 运行时执行
  app/models/task.py        → 任务数据模型
  app/services/task_service.py → 任务服务层

【前端类比】
  你点击"提交"按钮 → 拿到一个订单号 → 显示 loading → 轮询查状态 → 拿到结果渲染。
  一模一样的异步模式。

【运行方式】
  python 04_异步任务平台/02_完整平台.py

  测试：
  # 1. 提交任务
  curl -X POST http://localhost:8000/v1/task/submit \
    -H "Content-Type: application/json" \
    -d '{"agent_type": "question_check", "input_json": {"question": "满意吗", "answer": "暖气不热"}}'

  # 2. 用返回的 request_id 查询结果
  curl http://localhost:8000/v1/task/{request_id}
================================================================
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ================================================================
# 第 1 层：数据模型（对应 llm-agent/app/models/task.py）
# ================================================================

class TaskStatus(str, Enum):
    """
    任务状态机：queued → running → success/failed
    对照 llm-agent：app/models/task.py 里的 TaskStatus
    前端类比：就像订单状态 pending → processing → done/error
    """
    QUEUED = "queued"       # 已入队，等待执行
    RUNNING = "running"     # 正在执行
    SUCCESS = "success"     # 执行成功
    FAILED = "failed"       # 执行失败


class Task:
    """任务数据模型 —— 对应 llm-agent/app/models/task.py"""
    def __init__(self, request_id: str, agent_type: str, input_json: dict):
        self.request_id = request_id
        self.agent_type = agent_type
        self.input_json = input_json
        self.status = TaskStatus.QUEUED
        self.output_json: Optional[dict] = None
        self.error_msg: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.execution_time: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "output_json": self.output_json,
            "error_msg": self.error_msg,
            "created_at": self.created_at,
            "execution_time": self.execution_time,
        }


# ================================================================
# 第 2 层：任务数据库（对应 llm-agent/app/services/task_service.py）
# ================================================================
# 真实项目用 MySQL + SQLAlchemy，这里用内存字典模拟。
# 前端类比：就像一个全局 store / Redux

class TaskStore:
    """任务存储 —— 对应 llm-agent 的 TaskService + MySQL"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def create(self, agent_type: str, input_json: dict) -> Task:
        """创建新任务，分配 request_id"""
        request_id = str(uuid.uuid4())
        task = Task(request_id, agent_type, input_json)
        self._tasks[request_id] = task
        return task

    def get(self, request_id: str) -> Optional[Task]:
        """根据 request_id 查询任务"""
        return self._tasks.get(request_id)

    def update_status(self, request_id: str, status: TaskStatus, **kwargs):
        """更新任务状态"""
        task = self._tasks.get(request_id)
        if task:
            task.status = status
            task.updated_at = datetime.now().isoformat()
            for k, v in kwargs.items():
                setattr(task, k, v)


# ================================================================
# 第 3 层：Agent 逻辑（对应 llm-agent/app/agent/）
# ================================================================

AGENTS = {
    "question_check": {
        "description": "问卷问题检查",
        "keywords": ["降价", "便宜", "堵车", "修路", "暖气", "供暖", "配套", "学校", "医院"],
    },
    "message_summary": {
        "description": "消息摘要",
    },
}


def execute_agent(agent_type: str, input_json: dict) -> dict:
    """
    执行 Agent（模拟版，真实项目会调 LLM）
    对应 llm-agent：AgentFactory.create(agent_type).process(input_json)
    """
    if agent_type == "question_check":
        answer = str(input_json.get("answer", ""))
        config = AGENTS.get("question_check", {})
        keywords = config.get("keywords", [])
        detected = [kw for kw in keywords if kw in answer]
        time.sleep(2)  # 模拟 LLM 调用耗时（真实项目可能几秒到几十秒）
        return {
            "is_exist": 1 if detected else 2,
            "method": "keyword",
            "categories_detected": detected,
            "confidence": "high" if detected else "medium",
        }
    elif agent_type == "message_summary":
        time.sleep(1)
        text = str(input_json.get("text", ""))
        return {"summary": text[:50] + "..." if len(text) > 50 else text}
    else:
        raise ValueError(f"不支持的 Agent 类型: {agent_type}")


# ================================================================
# 第 4 层：异步任务队列（对应 llm-agent/app/queue/）
# ================================================================
# 真实项目用 ARQ + Redis，这里用 asyncio.Queue 模拟。
# 前端类比：就像一个消息队列 / Web Worker

class TaskQueue:
    """
    异步任务队列 —— 对应 llm-agent 的 ARQ 队列

    核心流程：
    1. submit() 把任务放入队列
    2. Worker 从队列取出任务执行
    3. 执行结果写回 TaskStore
    """

    def __init__(self, store: TaskStore):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._store = store
        self._worker_running = False

    async def submit(self, task: Task):
        """把任务放入队列"""
        await self._queue.put(task)
        print(f"  📥 任务 {task.request_id[:8]}... 已入队 (agent={task.agent_type})")

    async def worker(self):
        """
        Worker：不断从队列取任务并执行。
        对照 llm-agent：app/queue/worker.py + app/queue/functions.py

        这就是后台"工人"的工作循环：
        while True:
            task = queue.get()    # 取任务
            result = agent(task)  # 执行
            store.save(result)    # 存结果
        """
        self._worker_running = True
        print("  👷 Worker 已启动，等待任务...")

        while self._worker_running:
            # 从队列取一个任务（如果队列为空，会等待）
            task = await self._queue.get()

            print(f"  ⚡ Worker 开始处理：{task.request_id[:8]}... (agent={task.agent_type})")

            # 更新状态为 running
            self._store.update_status(task.request_id, TaskStatus.RUNNING)

            try:
                # 在线程池中执行 Agent（因为 Agent 可能是同步的 IO 操作）
                loop = asyncio.get_event_loop()
                start_time = time.time()
                result = await loop.run_in_executor(
                    None,  # 默认线程池
                    execute_agent,
                    task.agent_type,
                    task.input_json,
                )
                execution_time = time.time() - start_time

                # 成功：写回结果
                self._store.update_status(
                    task.request_id,
                    TaskStatus.SUCCESS,
                    output_json={"result": result},
                    execution_time=execution_time,
                )
                print(f"  ✅ 任务 {task.request_id[:8]}... 完成 (耗时 {execution_time:.1f}s)")

            except Exception as e:
                # 失败：记录错误
                self._store.update_status(
                    task.request_id,
                    TaskStatus.FAILED,
                    error_msg=str(e),
                )
                print(f"  ❌ 任务 {task.request_id[:8]}... 失败: {e}")

            # 标记队列任务完成
            self._queue.task_done()


# ================================================================
# 第 5 层：FastAPI 接口（对应 llm-agent/app/api/v1/task.py）
# ================================================================

# 全局实例
store = TaskStore()
queue = TaskQueue(store)

# Pydantic 模型（对应 llm-agent/app/schemas/task.py）
class TaskSubmitRequest(BaseModel):
    agent_type: str
    input_json: Dict[str, Any]

class TaskResponse(BaseModel):
    request_id: str
    status: str
    output_json: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None
    execution_time: Optional[float] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动启动 Worker"""
    worker_task = asyncio.create_task(queue.worker())
    yield  # 应用运行期间
    # 应用关闭时停止 Worker
    queue._worker_running = False


app = FastAPI(
    title="AI Agent 异步任务平台",
    description="llm-agent 的最小复刻版，展示请求-ID 异步模式",
    lifespan=lifespan,
)


@app.post("/v1/task/submit", response_model=TaskResponse)
async def submit_task(request: TaskSubmitRequest):
    """
    提交任务 —— 对应 llm-agent 的 POST /v1/task/submit

    关键设计：立即返回 request_id，不等结果。
    前端类比：点击提交 → 拿到订单号 → 显示 loading → 轮询查状态
    """
    # 校验 Agent 类型
    if request.agent_type not in AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的 Agent 类型: {request.agent_type}，可用: {list(AGENTS.keys())}"
        )

    # 创建任务
    task = store.create(request.agent_type, request.input_json)

    # 放入异步队列（不等执行结果）
    await queue.submit(task)

    # 立即返回 request_id 和 queued 状态
    return TaskResponse(
        request_id=task.request_id,
        status=task.status.value,
    )


@app.get("/v1/task/{request_id}", response_model=TaskResponse)
async def get_task(request_id: str):
    """
    查询任务状态 —— 对应 llm-agent 的 GET /v1/task/{request_id}

    客户端拿 request_id 轮询这个接口，直到 status 变成 success/failed。
    前端类比：setInterval(() => fetch(`/task/${id}`), 2000)
    """
    task = store.get(request_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {request_id}")

    return TaskResponse(
        request_id=task.request_id,
        status=task.status.value,
        output_json=task.output_json,
        error_msg=task.error_msg,
        execution_time=task.execution_time,
    )


@app.get("/v1/agents")
async def list_agents():
    """列出所有可用的 Agent"""
    return {"agents": {k: v["description"] for k, v in AGENTS.items()}}


# ================================================================
# 启动
# ================================================================
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("阶段 4-2：完整异步任务平台")
    print("=" * 60)
    print()
    print("架构：FastAPI + asyncio Queue + Worker")
    print("对应：llm-agent 的 API → MySQL → Redis/ARQ → Worker 链路")
    print()
    print("📖 API 文档：http://localhost:8000/docs")
    print()
    print("测试流程：")
    print('  1. POST /v1/task/submit → 拿到 request_id（秒回）')
    print('  2. GET /v1/task/{request_id} → 轮询直到 success')
    print()
    print("测试命令：")
    print('  curl -X POST http://localhost:8000/v1/task/submit \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"agent_type":"question_check","input_json":{"question":"满意吗","answer":"暖气不热"}}\'')
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
