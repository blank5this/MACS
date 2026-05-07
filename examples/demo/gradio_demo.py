"""
MACS Gradio Demo - 可在线演示的多智能体协作系统

使用方法:
    pip install gradio
    python examples/demo/gradio_demo.py

访问 http://localhost:7860 查看 Demo
"""

import gradio as gr
from macs_pkg.collaboration.hierarchical import HierarchicalMode
from macs_pkg.collaboration.pipeline import PipelineMode
from macs_pkg.collaboration.decentralized import DecentralizedMode
from macs_pkg.core.agent import AgentRole
from macs_pkg.llm.base import LLMMessage

# ============================================
# 模拟 Agent 响应 (Demo 模式，无需 API Key)
# ============================================

DEMO_RESPONSES = {
    "planner": {
        "input": "写一个快速排序算法",
        "output": """【任务分析】
输入: [8, 3, 1, 7, 0, 10, 2]
目标: 将数组排序为 [0, 1, 2, 3, 7, 8, 10]

【执行计划】
1. 选择基准元素 (选最后一个: 2)
2. 分区: 小于2的放左边，大于2的放右边
3. 递归处理左右两部分

【分工】
- Executor: 实现快速排序代码
- Reviewer: 检查边界情况和性能""",
    },
    "executor": {
        "input": "写一个快速排序算法",
        "output": """```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[-1]
    left = [x for x in arr[:-1] if x <= pivot]
    right = [x for x in arr[:-1] if x > pivot]
    return quicksort(left) + [pivot] + quicksort(right)

# 测试
arr = [8, 3, 1, 7, 0, 10, 2]
print(quicksort(arr))  # [0, 1, 2, 3, 7, 8, 10]
```""",
    },
    "reviewer": {
        "input": "写一个快速排序算法",
        "output": """【代码审查】

✅ 优点:
- 递归终止条件正确
- 分区逻辑清晰
- 代码简洁易懂

⚠️ 改进建议:
- 添加类型注解
- 考虑原地排序版本节省内存
- 添加基准选择优化(避免最坏情况)

【最终评分】8/10""",
    },
    "web_search": {
        "input": "深圳天气",
        "output": """【网络搜索结果】
- 当前天气: 多云，26°C
- 湿度: 65%
- 建议: 适合出行，记得带伞
- PM2.5: 良""",
    },
    "calculator": {
        "input": "123 * 456 + 789",
        "output": """【计算结果】
123 × 456 = 56,088
56,088 + 789 = 56,877

✅ 结果: 56,877""",
    },
}


def get_agent_response(agent_name: str, task: str) -> str:
    """获取 Agent 响应 (Demo 模式)"""
    if agent_name in DEMO_RESPONSES:
        demo = DEMO_RESPONSES[agent_name]
        if task.strip():
            return f"📥 任务: {task}\n\n{demo['output']}"
    return f"⚠️ Demo 模式: {agent_name} 收到任务: {task}"


# ============================================
# Gradio 界面
# ============================================

def run_hierarchical(task: str) -> str:
    """层级式协作模式"""
    if not task.strip():
        return "请输入任务..."

    result = "=" * 50 + "\n"
    result += "🏛️ 层级式协作 (Hierarchical Mode)\n"
    result += "=" * 50 + "\n\n"

    # Planner
    result += "👤 **Planner Agent** (任务规划)\n"
    result += "-" * 30 + "\n"
    result += get_agent_response("planner", task) + "\n\n"

    # Executor
    result += "⚙️ **Executor Agent** (执行)\n"
    result += "-" * 30 + "\n"
    result += get_agent_response("executor", task) + "\n\n"

    # Reviewer
    result += "🔍 **Reviewer Agent** (审查)\n"
    result += "-" * 30 + "\n"
    result += get_agent_response("reviewer", task) + "\n"

    result += "\n" + "=" * 50
    result += "\n✅ 层级式协作完成\n"

    return result


def run_pipeline(task: str) -> str:
    """管道式协作模式"""
    if not task.strip():
        return "请输入任务..."

    result = "=" * 50 + "\n"
    result += "🔗 管道式协作 (Pipeline Mode)\n"
    result += "=" * 50 + "\n\n"

    steps = [
        ("Step 1: 分析", "planner"),
        ("Step 2: 执行", "executor"),
        ("Step 3: 审查", "reviewer"),
    ]

    for step_name, agent in steps:
        result += f"📍 **{step_name}**\n"
        result += "-" * 30 + "\n"
        result += get_agent_response(agent, task) + "\n\n"

    result += "=" * 50 + "\n"
    result += "✅ 管道式协作完成\n"

    return result


def run_decentralized(task: str) -> str:
    """去中心化协作模式"""
    if not task.strip():
        return "请输入任务..."

    result = "=" * 50 + "\n"
    result += "🌐 去中心化协作 (Decentralized Mode)\n"
    result += "=" * 50 + "\n\n"

    # 模拟多个 Agent 协商
    result += "🤖 Agent A: 我认为应该...\n"
    result += get_agent_response("planner", task).replace("【任务分析】", "观点A: ")[:200] + "...\n\n"

    result += "🤖 Agent B: 我的看法是...\n"
    result += get_agent_response("executor", task).replace("```python", "```").replace("```", "")[:200] + "...\n\n"

    result += "🤖 Agent C: 综合考虑...\n"
    result += get_agent_response("reviewer", task).replace("【代码审查】", "综合结论: ")[:200] + "...\n\n"

    result += "=" * 50 + "\n"
    result += "✅ 去中心化协商完成，达成共识\n"

    return result


def run_tools_demo(tool: str, query: str) -> str:
    """工具使用演示"""
    if not query.strip():
        return "请输入查询..."

    result = f"🛠️ 使用工具: {tool}\n"
    result += "-" * 30 + "\n"
    result += get_agent_response(tool.lower(), query) + "\n"

    return result


def get_system_info() -> str:
    """获取系统信息"""
    return """
## MACS - Multi-Agent Collaboration System

**版本**: 0.2.0

**支持的功能**:
- ✅ 多 Agent 协作 (层级/管道/去中心化)
- ✅ 多种 LLM Provider (混元/Qwen/Claude/DeepSeek 等)
- ✅ 丰富的工具集 (搜索/计算/代码执行)
- ✅ RAG 知识库增强
- ✅ MCP 协议支持

**Demo 模式**: 无需 API Key，直接体验核心功能

**实际使用**: 需要配置 LLM API Key
```python
from macs_pkg.llm import HunyuanProvider
provider = HunyuanProvider(api_key="your_key")
```
"""


# ============================================
# 创建 Gradio 界面
# ============================================

with gr.Blocks(
    title="MACS Demo - 多智能体协作系统",
    theme=gr.themes.Soft(),
) as demo:

    gr.Markdown("""
    # 🎭 MACS Demo
    ## Multi-Agent Collaboration System 多智能体协作系统

    <center>
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
    <img src="https://img.shields.io/badge/AI-Agent-red.svg" alt="AI Agent">
    <img src="https://img.shields.io/badge/LLM-Multi--Provider-green.svg" alt="LLM">
    </center>

    这是一个 Demo 演示，无需 API Key 即可体验 MACS 的核心功能。
    """)

    with gr.Tabs():
        # Tab 1: 协作模式
        with gr.TabItem("🤝 协作模式"):
            gr.Markdown("### 选择协作模式处理任务")
            mode = gr.Radio(
                ["层级式", "管道式", "去中心化"],
                value="层级式",
                label="协作模式",
            )
            task_input = gr.Textbox(
                placeholder="输入任务，例如：写一个快速排序算法"
            )
            submit_btn = gr.Button("🚀 执行任务", variant="primary")
            output = gr.Markdown()

            # 事件绑定
            submit_btn.click(
                fn=lambda m, t: {
                    "层级式": run_hierarchical,
                    "管道式": run_pipeline,
                    "去中心化": run_decentralized,
                }.get(m, run_hierarchical)(t),
                inputs=[mode, task_input],
                outputs=output,
            )

        # Tab 2: 工具演示
        with gr.TabItem("🛠️ 工具演示"):
            gr.Markdown("### 体验不同工具的能力")
            tool = gr.Dropdown(
                ["网络搜索", "计算器", "代码执行"],
                value="计算器",
                label="选择工具",
            )
            tool_input = gr.Textbox(
                placeholder="输入查询，例如：深圳天气 或 123 * 456",
            )
            tool_btn = gr.Button("🔧 执行", variant="primary")
            tool_output = gr.Markdown()

            tool_btn.click(
                fn=run_tools_demo,
                inputs=[tool, tool_input],
                outputs=tool_output,
            )

        # Tab 3: 系统信息
        with gr.TabItem("ℹ️ 系统信息"):
            gr.Markdown(get_system_info())

            gr.Markdown("""
            ## 快速开始

            ```bash
            # 安装
            pip install gradio
            cd macs
            python examples/demo/gradio_demo.py
            ```

            ## 真实 API 使用

            ```python
            from macs_pkg import create_runtime
            from macs_pkg.llm import HunyuanProvider

            # 创建运行时
            runtime = create_runtime(
                agents=[
                    {"name": "planner", "role": "planner"},
                    {"name": "executor", "role": "executor"},
                    {"name": "reviewer", "role": "reviewer"},
                ],
                mode="hierarchical",
                default_provider=HunyuanProvider(api_key="your_key"),
            )

            # 执行任务
            result = await runtime.execute({"description": "写一个排序算法"})
            ```
            """)

    # Footer
    gr.Markdown("""
    <center>
    <a href="https://github.com/blank5this/MACS">📦 GitHub</a> |
    <a href="https://github.com/blank5this/MACS/issues">🐛 问题反馈</a>
    </center>
    """)


if __name__ == "__main__":
    print("🎭 启动 MACS Demo...")
    print("📍 访问 http://localhost:7860")
    demo.launch(server_name="0.0.0.0", server_port=7860)
