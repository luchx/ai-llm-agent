"""
================================================================
阶段 4-1：FastAPI 接口 —— 把 Agent 包装成 HTTP 服务
================================================================

【这个文件教会你什么】
  把之前写的 Agent 变成一个 Web API，让其他系统可以通过 HTTP 调用。
  这就是真实项目的 API 层。

  app/api/v1/task.py  ← 任务提交和查询接口
  app/main.py         ← FastAPI 应用入口
  app/schemas/task.py  ← 请求和响应的数据结构

【前端类比】
  就像你用 Express/Koa 写后端接口一样。
  FastAPI 是 Python 的 Web 框架，自动帮你生成 API 文档。

【运行方式】
  pip install fastapi uvicorn
  python 04_异步任务平台/01_FastAPI接口.py
  然后打开 http://localhost:8000/docs 查看 Swagger 文档
================================================================
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import time

# ========== 第 1 步：创建 FastAPI 应用 ==========
# 前端类比：const app = express()
app = FastAPI(
    title="AI Agent 平台（学习版）",
    description="最小可运行的 AI Agent 平台",
    version="0.1.0",
)


# ========== 第 2 步：定义请求和响应的数据结构 ==========
# 前端类比：就像你定义 TypeScript interface
class TaskSubmitRequest(BaseModel):
    """任务提交请求 ——"""
    agent_type: str                    # 要用哪个 Agent，如 "question_check"
    input_json: Dict[str, Any]         # Agent 的输入数据

class TaskResponse(BaseModel):
    """任务响应 ——"""
    request_id: str                    # 任务唯一 ID
    status: str                        # 状态：queued / running / success / failed
    output_json: Optional[Dict[str, Any]] = None  # 执行结果（成功时有值）
    error_msg: Optional[str] = None    # 错误信息（失败时有值）


# ========== 第 3 步：模拟数据库 ==========
# 真实项目用 MySQL，这里用内存字典模拟。
# 前端类比：就像用 useState 存数据，刷新就没了。
task_db: Dict[str, TaskResponse] = {}


# ========== 第 4 步：模拟一个最简单的 Agent ==========
# 这里为了不依赖 LLM API，用简单的关键词匹配模拟。
def run_agent(agent_type: str, input_json: dict) -> dict:
    """模拟执行 Agent（真实项目会调 LLM）"""
    if agent_type == "question_check":
        answer = input_json.get("answer", "")
        keywords = ["降价", "便宜", "堵车", "修路", "暖气", "供暖", "配套", "学校"]
        detected = [kw for kw in keywords if kw in str(answer)]
        return {
            "is_exist": 1 if detected else 2,
            "method": "keyword",
            "categories_detected": detected,
        }
    elif agent_type == "echo":
        return {"echo": input_json}
    else:
        raise ValueError(f"不支持的 Agent 类型: {agent_type}")


# ========== 第 5 步：定义 API 接口 ==========

@app.post("/v1/task/submit", response_model=TaskResponse, tags=["任务管理"])
async def submit_task(request: TaskSubmitRequest):
    """
    提交任务 ——

    这是同步版本：直接执行 Agent 并返回结果。
    后面的 02_异步任务.py 会改成异步：先返回 ID，后台慢慢执行。

    前端类比：这就是你写的 POST /api/submit 接口。
    """
    # 生成唯一 request_id（就像一个取餐号）
    request_id = str(uuid.uuid4())

    try:
        # 执行 Agent
        result = run_agent(request.agent_type, request.input_json)

        # 构造响应
        response = TaskResponse(
            request_id=request_id,
            status="success",
            output_json={"result": result},
        )
    except Exception as e:
        response = TaskResponse(
            request_id=request_id,
            status="failed",
            error_msg=str(e),
        )

    # 存到"数据库"
    task_db[request_id] = response
    return response


@app.get("/v1/task/{request_id}", response_model=TaskResponse, tags=["任务管理"])
async def get_task(request_id: str):
    """
    查询任务状态 ——

    前端类比：这就是你写的 GET /api/task/:id 接口。
    """
    if request_id not in task_db:
        raise HTTPException(status_code=404, detail=f"任务不存在: {request_id}")
    return task_db[request_id]


@app.get("/v1/agents", tags=["系统信息"])
async def list_agents():
    """
    列出所有可用的 Agent 类型 ——
    """
    return {
        "agents": [
            {"type": "question_check", "description": "问卷问题检查"},
            {"type": "echo", "description": "回声测试"},
        ]
    }


@app.get("/", tags=["系统信息"])
async def root():
    """健康检查"""
    return {"status": "ok", "message": "AI Agent 平台运行中"}


# ========== 启动 ==========
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("阶段 4-1：FastAPI 接口")
    print("=" * 60)
    print()
    print("🚀 启动服务...")
    print("📖 API 文档：http://localhost:8000/docs")
    print("🔍 提交任务：POST http://localhost:8000/v1/task/submit")
    print()
    print("测试命令（在另一个终端执行）：")
    print('  curl -X POST http://localhost:8000/v1/task/submit \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"agent_type": "question_check", "input_json": {"answer": "暖气不热"}}\'')
    print()

    # 启动 uvicorn 服务器
    # 前端类比：app.listen(8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
