"""
================================================================
阶段 6-2：运行时管理 —— 生产环境的并发控制与内存回收
================================================================

【这个文件教会你什么】
  真实项目在生产环境中面临的两大难题：
  1. 并发失控：同时来 100 个 LLM 任务，内存和 CPU 撑不住
  2. 内存膨胀：Worker 跑久了内存只涨不降，最终 OOM 被系统强杀

  这个文件用最简化的代码展示解决方案。

  app/runtime/agent_runtime.py  ← 完整的运行时实现

  三大机制：
  - 执行预算（Execution Budget）：限制同时执行的任务数
  - 进程回收（Process Recycle）：按任务数或内存阈值重启 Worker
  - 内存裁剪（Memory Trim）：gc.collect() + malloc_trim

【前端类比】
  - 执行预算 = 请求并发限制（不要同时发太多请求）
  - 进程回收 = 定时刷新页面（开久了内存泄漏，刷新一下就好）
  - 内存裁剪 = 手动清理缓存

【运行方式】
  python 06_进阶优化/02_运行时管理.py
================================================================
"""

import asyncio
import gc
import os
import time
import threading
from typing import Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor


# ========== 第 1 部分：执行预算（Execution Budget） ==========
#
# 问题：如果同时来 100 个 LLM 任务，每个都占内存和连接，
#       Worker 会撑不住。
# 解决：设置一个"预算"，比如同时最多跑 5 个任务，
#       第 6 个必须等前面的完成才能开始。
#
# 前端类比：就像你限制并发请求数为 5（Promise.all 的并发控制）。

class ExecutionBudget:
    """
    执行预算：限制同时执行的任务数。


    实现原理：asyncio.Semaphore（信号量）
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active = 0
        self._rejected = 0

    async def acquire(self, task_name: str = "") -> bool:
        """
        获取执行预算。如果预算满了，等待。
        前端类比：就像一个请求池，满了就排队。
        """
        print(f"  📊 [{task_name}] 等待执行预算... (当前活跃: {self._active}/{self.max_concurrent})")

        try:
            # 等待，直到有空闲预算（最多等 10 秒）
            await asyncio.wait_for(self._semaphore.acquire(), timeout=10.0)
            self._active += 1
            print(f"  ✅ [{task_name}] 获得预算 (活跃: {self._active}/{self.max_concurrent})")
            return True
        except asyncio.TimeoutError:
            self._rejected += 1
            print(f"  ❌ [{task_name}] 预算超时，拒绝执行")
            return False

    async def release(self, task_name: str = ""):
        """释放执行预算"""
        self._active = max(0, self._active - 1)
        self._semaphore.release()
        print(f"  🔓 [{task_name}] 释放预算 (活跃: {self._active}/{self.max_concurrent})")

    def stats(self) -> dict:
        return {
            "max_concurrent": self.max_concurrent,
            "active": self._active,
            "rejected": self._rejected,
        }


# ========== 第 2 部分：进程回收（Process Recycle） ==========
#
# 问题：Worker 跑久了内存只涨不降（Python 对象未及时回收、
#       glibc 的 malloc 不把 free 的内存还给 OS）。
# 解决：当处理了 N 个任务或内存超过阈值时，优雅退出，
#       由进程管理器（ARQ / Gunicorn）自动拉起新进程。
#
# 前端类比：就像 SPA 开久了变卡，定时刷新一下页面。

class RecyclePolicy:
    """
    进程回收策略：决定什么时候该"重启" Worker。


    """

    def __init__(
        self,
        max_tasks: int = 100,       # 处理多少个任务后回收
        max_memory_mb: int = 512,    # 内存超过多少 MB 后回收
    ):
        self.max_tasks = max_tasks
        self.max_memory_mb = max_memory_mb
        self.processed_tasks = 0
        self.recycle_requested = False
        self.recycle_reason = ""

    def on_task_done(self):
        """
        每个任务完成后调用，检查是否需要回收。

        """
        self.processed_tasks += 1

        # 检查 1：任务数达到上限
        if self.processed_tasks >= self.max_tasks:
            self.recycle_requested = True
            self.recycle_reason = f"已处理 {self.processed_tasks} 个任务，达到上限 {self.max_tasks}"
            return

        # 检查 2：内存达到上限（这里用简化方式估算）
        try:
            import psutil
            rss_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            if rss_mb >= self.max_memory_mb:
                self.recycle_requested = True
                self.recycle_reason = f"RSS={rss_mb:.0f}MB，达到上限 {self.max_memory_mb}MB"
        except ImportError:
            pass  # psutil 未安装，跳过内存检查

    def should_recycle(self) -> bool:
        return self.recycle_requested


# ========== 第 3 部分：内存裁剪（Memory Trim） ==========
#
# 问题：Python 的 gc.collect() 只回收 Python 对象，
#       但 glibc 的 malloc 不会把 free 的内存还给操作系统。
#       所以即使 Python 对象被回收了，进程的 RSS（物理内存占用）还是不降。
# 解决：
#   1. gc.collect() —— 回收 Python 对象
#   2. malloc_trim(0) —— 强制 glibc 把空闲内存还给 OS
#
# 前端类比：就像你手动清空 localStorage + 触发 GC

def memory_trim():
    """
    主动释放内存。

    """
    # 第 1 步：Python 垃圾回收
    collected = gc.collect()
    print(f"  🧹 gc.collect() 回收了 {collected} 个对象")

    # 第 2 步：尝试调用 libc 的 malloc_trim（把内存还给 OS）
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
        print(f"  🧹 malloc_trim(0) 已执行，空闲内存归还 OS")
    except (OSError, AttributeError):
        # macOS 或 Windows 没有 libc.so.6，跳过
        print(f"  ℹ️ malloc_trim 不可用（非 Linux 环境）")


# ========== 第 4 部分：模拟 Agent 任务 ==========
async def simulate_agent_task(task_id: int, budget: ExecutionBudget, recycle: RecyclePolicy):
    """
    模拟一个 Agent 任务的完整生命周期：
    1. 获取执行预算
    2. 执行任务
    3. 释放预算
    4. 检查是否需要回收
    """
    task_name = f"task-{task_id}"

    # 第 1 步：获取预算
    acquired = await budget.acquire(task_name)
    if not acquired:
        return {"task_id": task_id, "status": "rejected", "reason": "budget_exhausted"}

    try:
        # 第 2 步：模拟执行（这里用 sleep 模拟 LLM 调用耗时）
        print(f"  ⚡ [{task_name}] 开始执行...")
        await asyncio.sleep(0.5)  # 模拟 LLM 调用
        print(f"  ✅ [{task_name}] 执行完成")

        # 第 3 步：检查是否需要回收
        recycle.on_task_done()
        if recycle.should_recycle():
            print(f"\n  🔄 触发进程回收：{recycle.recycle_reason}")
            memory_trim()

        return {"task_id": task_id, "status": "success"}

    finally:
        # 无论成功失败，都释放预算
        await budget.release(task_name)


# ========== 运行演示 ==========
async def main():
    print("=" * 60)
    print("阶段 6-2：运行时管理 —— 并发控制 + 内存回收")
    print("=" * 60)

    # 创建运行时组件
    budget = ExecutionBudget(max_concurrent=3)    # 最多同时跑 3 个任务
    recycle = RecyclePolicy(max_tasks=5)          # 处理 5 个任务后回收

    print(f"\n📊 配置：最大并发={budget.max_concurrent}, 回收阈值={recycle.max_tasks}个任务")

    # 模拟同时提交 8 个任务
    print(f"\n{'─'*60}")
    print("提交 8 个任务（超过并发限制 3）：")

    tasks = [simulate_agent_task(i, budget, recycle) for i in range(1, 9)]
    results = await asyncio.gather(*tasks)

    # 汇总
    print(f"\n{'='*60}")
    print(f"📊 执行统计：")
    success = sum(1 for r in results if r["status"] == "success")
    rejected = sum(1 for r in results if r["status"] == "rejected")
    print(f"   成功：{success}, 拒绝：{rejected}")
    print(f"   预算统计：{budget.stats()}")

    print(f"\n{'='*60}")
    print("✅ 运行时管理的三大机制：")
    print("   1. 执行预算：信号量限制并发，超时快速失败（防雪崩）")
    print("   2. 进程回收：任务数/内存阈值触发优雅重启（防 OOM）")
    print("   3. 内存裁剪：gc.collect + malloc_trim 主动归还内存")
    print("。")


if __name__ == "__main__":
    asyncio.run(main())
