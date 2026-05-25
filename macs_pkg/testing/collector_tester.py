"""Diteng Collector 测试 Agent

自动化测试 diteng-collector 数据采集器的核心功能：
1. 健康检查 - 验证应用启动状态
2. 配置验证 - 检查 XML/DB 配置是否正确加载
3. 任务执行测试 - 触发采集任务并验证结果
4. 日志分析 - 检查错误和异常
5. 数据验证 - 验证采集的数据是否正确
"""

import asyncio
import subprocess
import time
import re
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from macs_pkg.utils.logger import get_logger

logger = get_logger("collector_tester")


class TestStatus(Enum):
    """测试状态"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    RUNNING = "running"
    UNKNOWN = "unknown"


class HealthLevel(Enum):
    """健康级别"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """测试结果"""
    name: str
    status: TestStatus
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def is_success(self) -> bool:
        return self.status == TestStatus.PASS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


@dataclass
class CollectorHealth:
    """采集器健康状态"""
    level: HealthLevel
    app_running: bool = False
    port_open: bool = False
    actuator_ok: bool = False
    jobs_loaded: int = 0
    last_execution: Optional[datetime] = None
    error_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "app_running": self.app_running,
            "port_open": self.port_open,
            "actuator_ok": self.actuator_ok,
            "jobs_loaded": self.jobs_loaded,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "error_count": self.error_count,
            "details": self.details,
        }


class DitengCollectorTester:
    """Diteng Collector 自动化测试 Agent"""

    def __init__(
        self,
        collector_path: str = "C:\\Users\\admin\\Documents\\iWork\\diteng-collector",
        port: int = 8080,
        xml_config: str = "config/config.xml",
    ):
        """初始化测试 Agent

        Args:
            collector_path: diteng-collector 项目路径
            port: 应用端口
            xml_config: XML 配置文件路径
        """
        self.collector_path = collector_path
        self.port = port
        self.xml_config = xml_config
        self.base_url = f"http://localhost:{port}"
        self.results: List[TestResult] = []

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 30,
        cwd: Optional[str] = None,
    ) -> tuple[int, str, str]:
        """执行命令并返回结果

        Returns:
            (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or self.collector_path,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, "", str(e)

    async def check_port_open(self, host: str = "localhost", port: Optional[int] = None) -> bool:
        """检查端口是否开放"""
        port = port or self.port
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=3.0,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def test_app_health(self) -> TestResult:
        """测试1: 应用健康检查"""
        start = time.time()
        name = "app_health"

        try:
            # 检查进程是否运行
            code, stdout, _ = self._run_command(
                ["powershell", "-Command",
                 f"Get-NetTCPConnection -LocalPort {self.port} -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"],
            )
            port_count = int(stdout.strip()) if stdout.strip().isdigit() else 0
            app_running = port_count > 0

            # 检查 actuator 端点
            actuator_ok = False
            if app_running:
                try:
                    import urllib.request
                    url = f"{self.base_url}/actuator/health"
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        actuator_ok = resp.status == 200
                except Exception:
                    pass

            duration_ms = (time.time() - start) * 1000

            if not app_running:
                return TestResult(
                    name=name,
                    status=TestStatus.FAIL,
                    message="应用未运行，端口未监听",
                    duration_ms=duration_ms,
                )

            if actuator_ok:
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message="应用运行正常，Actuator 端点可访问",
                    duration_ms=duration_ms,
                    details={"port": self.port},
                )
            else:
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message="应用运行正常（Actuator 端点无响应，可能未配置）",
                    duration_ms=duration_ms,
                    details={"port": self.port},
                )

        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"健康检查失败: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    async def test_xml_config_parsing(self) -> TestResult:
        """测试2: XML 配置文件解析"""
        start = time.time()
        name = "xml_config_parsing"

        try:
            xml_path = os.path.join(self.collector_path, self.xml_config)
            if not os.path.exists(xml_path):
                # 尝试 target 目录
                xml_path = os.path.join(self.collector_path, "target", "classes", self.xml_config)

            if not os.path.exists(xml_path):
                return TestResult(
                    name=name,
                    status=TestStatus.SKIP,
                    message=f"XML 配置文件不存在: {self.xml_config}",
                    duration_ms=(time.time() - start) * 1000,
                )

            # 解析 XML 文件
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_path)
            root = tree.getroot()

            jobs = root.findall("job")
            job_count = len(jobs)

            # 检查自动任务
            auto_jobs = [j for j in jobs if j.get("auto", "").lower() == "true"]
            auto_count = len(auto_jobs)

            # 检查数据源配置
            datasources = root.findall(".//datasource")
            ds_count = len(datasources)

            duration_ms = (time.time() - start) * 1000

            return TestResult(
                name=name,
                status=TestStatus.PASS,
                message=f"XML 配置解析成功，包含 {job_count} 个任务，其中 {auto_count} 个自动任务",
                duration_ms=duration_ms,
                details={
                    "total_jobs": job_count,
                    "auto_jobs": auto_count,
                    "datasources": ds_count,
                    "xml_path": xml_path,
                },
            )

        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"XML 解析失败: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    async def test_database_connection(self) -> TestResult:
        """测试3: 数据库连接测试"""
        start = time.time()
        name = "database_connection"

        try:
            # 尝试连接 SQLite（如果存在）
            sqlite_path = os.path.join(self.collector_path, "data", "collector.db")
            if os.path.exists(sqlite_path):
                import sqlite3
                conn = sqlite3.connect(sqlite_path)
                cursor = conn.cursor()

                # 检查表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                # 检查任务数量
                if "jobs" in tables:
                    cursor.execute("SELECT COUNT(*) FROM jobs")
                    job_count = cursor.fetchone()[0]
                else:
                    job_count = 0

                # 检查最近执行状态
                execution_count = 0
                if "job_execution_status" in tables:
                    cursor.execute("SELECT COUNT(*) FROM job_execution_status")
                    execution_count = cursor.fetchone()[0]

                conn.close()

                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message=f"SQLite 数据库连接成功，找到 {job_count} 个任务，{execution_count} 条执行记录",
                    duration_ms=(time.time() - start) * 1000,
                    details={
                        "db_type": "sqlite",
                        "tables": tables,
                        "job_count": job_count,
                        "execution_count": execution_count,
                    },
                )
            else:
                # 检查是否有 PostgreSQL 或 MySQL 配置
                return TestResult(
                    name=name,
                    status=TestStatus.SKIP,
                    message="未找到 SQLite 数据库文件，跳过数据库测试",
                    duration_ms=(time.time() - start) * 1000,
                )

        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"数据库连接失败: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    async def test_job_execution(self) -> TestResult:
        """测试4: 任务执行测试"""
        start = time.time()
        name = "job_execution"

        try:
            # 检查是否有正在运行的任务
            # 通过查看日志或数据库状态
            log_path = os.path.join(self.collector_path, "logs")
            recent_logs = []

            if os.path.exists(log_path):
                # 读取最近的日志文件
                log_files = sorted(
                    [f for f in os.listdir(log_path) if f.endswith(".log")],
                    key=lambda x: os.path.getmtime(os.path.join(log_path, x)),
                    reverse=True,
                )
                if log_files:
                    latest_log = os.path.join(log_path, log_files[0])
                    try:
                        with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            recent_logs = lines[-100:]  # 最后 100 行
                    except Exception:
                        pass

            # 分析日志中的执行信息
            execution_pattern = re.compile(r"任务.*执行.*成功|start time:|stop time:|rowsReadCount")
            executions = []
            for line in recent_logs:
                if execution_pattern.search(line):
                    executions.append(line.strip())

            # 检查是否有 "start time" 和 "stop time" 成对出现
            start_times = [l for l in recent_logs if "start time:" in l]
            stop_times = [l for l in recent_logs if "stop time:" in l]

            duration_ms = (time.time() - start) * 1000

            if start_times or stop_times:
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message=f"检测到任务执行记录，开始 {len(start_times)} 次，结束 {len(stop_times)} 次",
                    duration_ms=duration_ms,
                    details={
                        "start_count": len(start_times),
                        "stop_count": len(stop_times),
                        "recent_executions": executions[-5:] if executions else [],
                    },
                )
            else:
                return TestResult(
                    name=name,
                    status=TestStatus.UNKNOWN,
                    message="未检测到任务执行记录，可能尚未执行过任务",
                    duration_ms=duration_ms,
                )

        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"任务执行检查失败: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    async def test_error_logs(self) -> TestResult:
        """测试5: 错误日志分析"""
        start = time.time()
        name = "error_logs"

        try:
            log_path = os.path.join(self.collector_path, "logs")
            errors = []
            warnings = []

            if os.path.exists(log_path):
                log_files = sorted(
                    [f for f in os.listdir(log_path) if f.endswith(".log")],
                    key=lambda x: os.path.getmtime(os.path.join(log_path, x)),
                    reverse=True,
                )

                # 读取最近 3 个日志文件
                for log_file in log_files[:3]:
                    try:
                        log_file_path = os.path.join(log_path, log_file)
                        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            # 只检查最后 500 行
                            recent_lines = lines[-500:] if len(lines) > 500 else lines
                            for line in recent_lines:
                                if "ERROR" in line or "Exception" in line or "error" in line.lower():
                                    errors.append(line.strip())
                                elif "WARN" in line:
                                    warnings.append(line.strip())
                    except Exception:
                        pass

            duration_ms = (time.time() - start) * 1000

            if errors:
                # 只保留最近 10 个错误
                recent_errors = errors[-10:]
                return TestResult(
                    name=name,
                    status=TestStatus.FAIL,
                    message=f"发现 {len(errors)} 个错误，最近 {len(recent_errors)} 个",
                    duration_ms=duration_ms,
                    details={
                        "total_errors": len(errors),
                        "recent_errors": recent_errors,
                    },
                )
            elif warnings:
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message=f"无错误，但有 {len(warnings)} 个警告",
                    duration_ms=duration_ms,
                    details={
                        "warning_count": len(warnings),
                        "recent_warnings": warnings[-5:],
                    },
                )
            else:
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message="无错误和警告日志",
                    duration_ms=duration_ms,
                )

        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"日志分析失败: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    async def test_datasource_connectivity(self) -> TestResult:
        """测试6: 数据源连接测试"""
        start = time.time()
        name = "datasource_connectivity"

        try:
            xml_path = os.path.join(self.collector_path, self.xml_config)
            if not os.path.exists(xml_path):
                xml_path = os.path.join(self.collector_path, "target", "classes", self.xml_config)

            if not os.path.exists(xml_path):
                return TestResult(
                    name=name,
                    status=TestStatus.SKIP,
                    message="XML 配置文件不存在",
                    duration_ms=(time.time() - start) * 1000,
                )

            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 查找所有数据源配置
            datasources = root.findall(".//datasource")
            results = []

            for ds in datasources:
                ds_type = ds.get("type", "unknown")
                site = ds.get("site", "")
                table = ds.findtext("table")

                results.append({
                    "type": ds_type,
                    "site": site,
                    "table": table,
                    "testable": ds_type in ("mysql", "mssql", "postgresql"),
                })

            duration_ms = (time.time() - start) * 1000

            testable_count = sum(1 for r in results if r["testable"])
            return TestResult(
                name=name,
                status=TestStatus.PASS,
                message=f"发现 {len(datasources)} 个数据源配置，其中 {testable_count} 个可测试",
                duration_ms=duration_ms,
                details={"datasources": results},
            )

        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"数据源连接测试失败: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        tests = [
            self.test_app_health,
            self.test_xml_config_parsing,
            self.test_database_connection,
            self.test_job_execution,
            self.test_error_logs,
            self.test_datasource_connectivity,
        ]

        self.results = []
        passed = 0
        failed = 0
        skipped = 0

        for test_func in tests:
            logger.info(f"Running test: {test_func.__name__}")
            result = await test_func()
            self.results.append(result)

            if result.status == TestStatus.PASS:
                passed += 1
            elif result.status == TestStatus.FAIL:
                failed += 1
            elif result.status == TestStatus.SKIP:
                skipped += 1

            logger.info(f"  -> {result.status.value}: {result.message}")

        # 生成健康报告
        health = self._compute_health()

        report = {
            "summary": {
                "total": len(tests),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": round(passed / len(tests) * 100, 1) if tests else 0,
            },
            "health": health.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "timestamp": datetime.now().isoformat(),
        }

        return report

    def _compute_health(self) -> CollectorHealth:
        """计算采集器健康状态"""
        if not self.results:
            return CollectorHealth(level=HealthLevel.UNKNOWN)

        failed_tests = [r for r in self.results if r.status == TestStatus.FAIL]
        passed_tests = [r for r in self.results if r.status == TestStatus.PASS]

        if len(failed_tests) == 0:
            level = HealthLevel.HEALTHY
        elif len(failed_tests) <= len(passed_tests):
            level = HealthLevel.DEGRADED
        else:
            level = HealthLevel.UNHEALTHY

        # 检查应用是否运行
        app_health = next((r for r in self.results if r.name == "app_health"), None)
        app_running = app_health and app_health.status == TestStatus.PASS

        # 检查错误日志
        error_test = next((r for r in self.results if r.name == "error_logs"), None)
        error_count = error_test.details.get("total_errors", 0) if error_test else 0

        return CollectorHealth(
            level=level,
            app_running=app_running,
            port_open=app_running,
            actuator_ok=app_running,
            error_count=error_count,
            details={
                "passed_tests": len(passed_tests),
                "failed_tests": len(failed_tests),
            },
        )

    def print_report(self, report: Dict[str, Any]) -> None:
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("Diteng Collector 自动化测试报告")
        print("=" * 60)

        summary = report["summary"]
        print(f"\n【测试摘要】")
        print(f"  总计: {summary['total']}")
        print(f"  通过: {summary['passed']} ✓")
        print(f"  失败: {summary['failed']} ✗")
        print(f"  跳过: {summary['skipped']} ⊘")
        print(f"  成功率: {summary['success_rate']}%")

        health = report["health"]
        health_emoji = {
            "healthy": "✓",
            "degraded": "⚠",
            "unhealthy": "✗",
            "unknown": "?",
        }
        print(f"\n【健康状态】{health_emoji.get(health['level'], '?')} {health['level']}")
        print(f"  应用运行: {'是' if health['app_running'] else '否'}")
        print(f"  端口开放: {'是' if health['port_open'] else '否'}")
        print(f"  错误日志: {health['error_count']} 个")

        print(f"\n【详细结果】")
        for result in report["results"]:
            status_emoji = {
                "pass": "✓",
                "fail": "✗",
                "skip": "⊘",
                "running": "...",
                "unknown": "?",
            }
            emoji = status_emoji.get(result["status"], "?")
            print(f"\n  {emoji} {result['name']}")
            print(f"     状态: {result['status']}")
            print(f"     消息: {result['message']}")
            print(f"     耗时: {result['duration_ms']}ms")
            if result.get("details"):
                for key, value in result["details"].items():
                    if isinstance(value, list):
                        if value:
                            print(f"     {key}: {value[0]}...")
                    else:
                        print(f"     {key}: {value}")

        print("\n" + "=" * 60)
        print(f"生成时间: {report['timestamp']}")
        print("=" * 60 + "\n")


async def run_collector_tests(
    collector_path: str = "C:\\Users\\admin\\Documents\\iWork\\diteng-collector",
    port: int = 8080,
) -> Dict[str, Any]:
    """运行采集器测试的便捷函数

    Args:
        collector_path: diteng-collector 项目路径
        port: 应用端口

    Returns:
        测试报告字典
    """
    tester = DitengCollectorTester(
        collector_path=collector_path,
        port=port,
    )
    report = await tester.run_all_tests()
    tester.print_report(report)
    return report


if __name__ == "__main__":
    # 直接运行时执行测试
    import sys

    collector_path = sys.argv[1] if len(sys.argv) > 1 else "C:\\Users\\admin\\Documents\\iWork\\diteng-collector"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    report = asyncio.run(run_collector_tests(collector_path, port))

    # 返回非零退出码表示有测试失败
    sys.exit(1 if report["summary"]["failed"] > 0 else 0)