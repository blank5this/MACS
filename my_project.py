"""
MACS 多智能体协作系统 - 可运行项目模板

使用方法：
1. 设置 ANTHROPIC_API_KEY 环境变量，或修改下方 API_KEY 变量
2. 修改 TASK 变量定义你的任务
3. 运行: python my_project.py

示例任务已预设，可直接运行测试。
"""

import asyncio
import os
import re
import sys

# 强制 Windows 下 stdout/stderr 走 UTF-8（中文不乱码）
from macs_pkg._compat import force_utf8_io
force_utf8_io()

# ==================== 配置区 ====================

# 使用环境变量（推荐）
# MiniMax: export MINIMAX_API_KEY=your-key
# 或创建 .env 文件存储
API_KEY = os.environ.get("MINIMAX_API_KEY", "")

# ==================== 任务定义区 ====================

# 在这里定义你的任务
TASK = {
    "type": "erp_procurement",
    "description": "采购订单审批流程",
    "requirements": [
        "员工提交采购申请（商品名称、数量、预算）",
        "部门主管审批（通过/拒绝/打回修改）",
        "财务复核（预算检查、超额审批）",
        "采购经理最终确认",
        "自动发送邮件/短信通知",
        "审批状态实时追踪",
    ],
}

# ==================== 系统配置区 ====================

COLLABORATION_MODE = "hierarchical"  # hierarchical, decentralized, pipeline
ENABLE_MEMORY = True  # 是否启用 MemPalace 记忆系统

# ==================== 以下无需修改 ====================


def print_banner():
    print("=" * 60)
    print("  MACS - Multi-Agent Collaboration System")
    print("=" * 60)
    print()


def print_config():
    print("[配置]")
    print(f"  协作模式: {COLLABORATION_MODE}")
    print(f"  记忆系统: {'启用' if ENABLE_MEMORY else '禁用'}")
    print(f"  API Key: {'已设置' if (API_KEY or os.environ.get('ANTHROPIC_API_KEY')) else '未设置!'}")
    print()


def print_task():
    print("[任务]")
    print(f"  类型: {TASK.get('type', 'general')}")
    print(f"  描述: {TASK.get('description', '')}")
    if TASK.get('requirements'):
        print("  需求:")
        for req in TASK['requirements']:
            print(f"    - {req}")
    print()


def print_status(status):
    print("[系统状态]")
    for name, info in status.get("agents", {}).items():
        print(f"  {name}: {info['role']} ({info['state']})")
    print(f"  任务完成: {status.get('tasks_completed', 0)}")
    print(f"  任务失败: {status.get('tasks_failed', 0)}")
    print()


async def main():
    print_banner()

    # 检查 API Key
    api_key = API_KEY or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[错误] 请设置 ANTHROPIC_API_KEY")
        print("  方式 1: 在文件开头设置 API_KEY = 'your-key'")
        print("  方式 2: 运行前执行: export ANTHROPIC_API_KEY=your-key")
        return

    print_config()
    print_task()

    print("[初始化] 启动 MACS 系统...")
    print()

    try:
        # 导入 MACS 模块
        from macs_pkg.runtime.engine import RuntimeEngine, RuntimeConfig
        from macs_pkg.llm.openai_compatible import MiniMaxProvider

        # 创建 LLM Provider (MiniMax)
        print("[1/4] 创建 MiniMax Provider...")
        provider = MiniMaxProvider(
            api_key=api_key,
            group_id=os.environ.get("MINIMAX_GROUP_ID", ""),
            model="MiniMax-M2.7",
        )
        print("      Provider 创建成功")

        # 创建 Runtime
        print("[2/4] 创建 Runtime Engine...")
        runtime = RuntimeEngine(RuntimeConfig(
            enable_shared_memory=ENABLE_MEMORY,
            default_mode=COLLABORATION_MODE,
        ))
        print(f"      Runtime 创建成功 (模式: {COLLABORATION_MODE})")

        # 创建 Agents
        print("[3/4] 创建 Agent 团队...")
        runtime.create_and_register_agents([
            {"name": "planner", "role": "planner"},
            {"name": "executor", "role": "executor"},
            {"name": "reviewer", "role": "reviewer"},
            {"name": "tool_agent", "role": "tool"},
        ], provider=provider)
        print("      PlannerAgent   - 任务规划")
        print("      ExecutorAgent  - 任务执行")
        print("      ReviewerAgent  - 质量审核")
        print("      ToolAgent     - 工具调用")

        # 初始化记忆
        if ENABLE_MEMORY:
            print("      初始化 MemPalace 记忆系统...")
            await runtime.init_shared_memory_async()
            for name in runtime.list_agents():
                agent = runtime.get_agent(name)
                if agent and hasattr(agent, 'init_memory'):
                    await agent.init_memory()
            print("      记忆系统就绪")

        print()
        print("[执行] 开始处理任务...")
        print("-" * 60)

        # 执行任务
        result = await runtime.execute(TASK, mode=COLLABORATION_MODE)

        print("-" * 60)
        print()
        print("[完成] 任务执行完毕!")
        print()
        print("[结果]")
        import json
        # 只过滤控制字符，**保留所有 Unicode（含中文）**。
        # 旧实现用 ascii 'replace' 会把中文压成 ?，是 Windows 乱码的根因之一。
        _CTRL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

        def sanitize_output(obj):
            if isinstance(obj, str):
                return _CTRL_CHARS.sub("", obj)
            elif isinstance(obj, dict):
                return {k: sanitize_output(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_output(item) for item in obj]
            else:
                return obj

        print(json.dumps(sanitize_output(result), ensure_ascii=False, indent=2))
        print()

        # 显示状态
        print_status(runtime.get_system_status())

        # 显示历史
        history = runtime.get_task_history()
        if history:
            print("[历史]")
            for item in history:
                status_icon = "[OK]" if item.get("status") == "completed" else "[FAIL]"
                duration = item.get("duration_s", 0)
                print(f"  {status_icon} {item['task_id']} - {item['mode']} ({duration:.2f}s)")

    except ImportError as e:
        print(f"[错误] 导入模块失败: {e}")
        print()
        print("请确保已安装 MACS:")
        print("  cd C:\\Users\\admin\\Desktop\\macs")
        print("  pip install -e .")

    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
