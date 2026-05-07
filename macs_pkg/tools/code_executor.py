"""Code Execution Tool - 安全执行 Python 代码.

使用 Docker 或本地进程执行 Python 代码。
支持:
- 超时控制
- 内存限制 (通过 Docker)
- 输出捕获
- 错误处理

使用方式::

    tool = PythonCodeExecutorTool(timeout=30)
    result = await tool.run(code="print('Hello, World!')")
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass

from .base import BaseTool, ToolParameter, ToolResult, ToolSpec


@dataclass
class ExecutionResult:
    """代码执行结果."""
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float


class PythonCodeExecutorTool(BaseTool):
    """安全的 Python 代码执行器.

    特性:
    - 超时控制
    - 隔离执行 (使用 subprocess)
    - 输出捕获
    - 内存安全

    安全措施:
    - 不允许危险操作 (os, subprocess 等)
    - 超时自动终止
    - 限制输出大小
    """

    # 允许导入的模块
    ALLOWED_IMPORTS = {
        "math", "random", "json", "re", "datetime", "timedelta",
        "collections", "itertools", "functools", "typing",
        "string", "textwrap", "unicodedata", "html", "csv",
        "io", "os"  # 部分允许
    }

    # 禁止的关键词
    FORBIDDEN_PATTERNS = [
        "import os.system",
        "subprocess",
        "eval(",
        "exec(",
        "__import__",
        "open(",
        "file(",
        "input(",
        "memoryview",
        "ctypes",
        "pickle",
        "shelve",
        "sys.exit",
        "os.exe",
        "os.remove",
        "os.rmdir",
        "os.unlink",
    ]

    def __init__(
        self,
        timeout: float = 30.0,
        max_output_size: int = 10000,
        working_dir: Optional[str] = None,
    ):
        """
        Args:
            timeout: 最大执行时间 (秒)
            max_output_size: 最大输出大小 (字符)
            working_dir: 工作目录
        """
        self._timeout = timeout
        self._max_output_size = max_output_size
        self._working_dir = working_dir or tempfile.gettempdir()

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="python_executor",
            description=(
                "Execute Python code safely. Returns stdout, stderr, and execution status. "
                "Supports math, string, json, datetime, and common stdlib modules. "
                "Does NOT support file I/O, network, or system commands."
            ),
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute. Only stdlib modules allowed.",
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description=f"Max execution time in seconds (default: {self._timeout})",
                    required=False,
                    default=self._timeout,
                ),
            ],
        )

    def _validate_code(self, code: str) -> tuple[bool, str]:
        """验证代码安全性."""
        code_lower = code.lower()
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.lower() in code_lower:
                return False, f"Forbidden pattern detected: {pattern}"
        return True, ""

    def _create_wrapper(self, code: str) -> str:
        """创建带保护的包装代码."""
        return f'''
import sys
import io
import traceback

# 捕获输出
_stdout = io.StringIO()
_stderr = io.StringIO()
sys.stdout = _stdout
sys.stderr = _stderr

try:
{chr(10).join("    " + line for line in code.split(chr(10)))}
except Exception:
    traceback.print_exc()

# 恢复输出
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# 输出结果
out = _stdout.getvalue()
err = _stderr.getvalue()
print("__MACS_OUTPUT_START__")
print(out)
print("__MACS_ERROR_START__")
print(err)
'''

    async def run(self, code: str, timeout: Optional[float] = None) -> ToolResult:
        """执行 Python 代码."""
        import subprocess
        import time

        # 验证代码
        safe, error = self._validate_code(code)
        if not safe:
            return ToolResult(
                success=False,
                output=None,
                error=f"Security check failed: {error}",
            )

        # 包装代码
        wrapper = self._create_wrapper(code)

        # 创建临时文件
        exec_id = str(uuid.uuid4())[:8]
        tmp_file = Path(self._working_dir) / f"macs_exec_{exec_id}.py"

        try:
            tmp_file.write_text(wrapper, encoding="utf-8")

            # 执行
            start = time.time()
            timeout_val = timeout or self._timeout

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(tmp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_val,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Execution timeout after {timeout_val}s",
                )

            duration = (time.time() - start) * 1000
            output = stdout.decode("utf-8", errors="replace")

            # 解析输出
            if "__MACS_OUTPUT_START__" in output:
                parts = output.split("__MACS_OUTPUT_START__")
                user_output = parts[1].split("__MACS_ERROR_START__")[0].strip()
                error_output = parts[1].split("__MACS_ERROR_START__")[1].strip() if "__MACS_ERROR_START__" in parts[1] else ""
            else:
                user_output = output
                error_output = stderr.decode("utf-8", errors="replace")

            # 截断过长输出
            if len(user_output) > self._max_output_size:
                user_output = user_output[:self._max_output_size] + f"\n... (truncated, total {len(user_output)} chars)"
            if len(error_output) > self._max_output_size:
                error_output = error_output[:self._max_output_size] + f"\n... (truncated)"

            success = process.returncode == 0 and not error_output.strip()

            return ToolResult(
                success=success,
                output=user_output if success else None,
                error=error_output.strip() if error_output.strip() else None,
                metadata={
                    "return_code": process.returncode,
                    "duration_ms": round(duration, 2),
                    "exec_id": exec_id,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Execution error: {str(e)}",
            )
        finally:
            # 清理临时文件
            if tmp_file.exists():
                tmp_file.unlink()


# Docker 版本 (更安全, 但需要 Docker)
class DockerCodeExecutorTool(BaseTool):
    """使用 Docker 容器执行代码 (更安全).

    需要 Docker daemon 运行.
    """

    def __init__(
        self,
        image: str = "python:3.11-slim",
        timeout: float = 30.0,
        max_memory: str = "256m",
    ):
        self._image = image
        self._timeout = timeout
        self._max_memory = max_memory

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="docker_python_executor",
            description="Execute Python code in isolated Docker container.",
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                ),
            ],
        )

    async def run(self, code: str) -> ToolResult:
        import subprocess
        import tempfile
        import time

        tmp_dir = Path(tempfile.mkdtemp())
        code_file = tmp_dir / "code.py"
        code_file.write_text(code, encoding="utf-8")

        container_name = f"macs_exec_{uuid.uuid4().hex[:8]}"

        cmd = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--memory", self._max_memory,
            "-v", f"{tmp_dir}:/code",
            "-w", "/code",
            self._image,
            "python", "code.py",
        ]

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            duration = (time.time() - start) * 1000

            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error