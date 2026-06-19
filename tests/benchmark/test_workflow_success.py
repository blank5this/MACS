"""Agent workflow 端到端成功率 benchmark。

真实接 LLM（marker = ``requires_llm``），无 key 时自动 skip。

输入：``fixtures/workflow_questions.yaml`` 的 10 个业务问题。
指标：端到端 ``success_rate``、``P50/P95 latency``，写到 ``results/workflow_success.csv``。
"""
from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Any

import pytest
import yaml

from .conftest import FIXTURES_DIR, RESULTS_DIR, append_csv_row, write_md_summary

pytestmark = pytest.mark.requires_llm

CSV_HEADER = ["id", "question", "success", "elapsed_ms", "error"]


def _load_questions() -> list[dict[str, Any]]:
    data = yaml.safe_load((FIXTURES_DIR / "workflow_questions.yaml").read_text(encoding="utf-8"))
    return data.get("questions", [])


QUESTIONS = _load_questions()


@pytest.mark.parametrize("item", QUESTIONS, ids=lambda x: x["id"])
def test_workflow_success(item: dict[str, Any], real_workflow) -> None:
    """每题跑 InventoryRiskWorkflow。workflow / provider 走 session-scope 复用。"""
    result = asyncio.run(real_workflow.run(item["question"]))
    # workflow 失败时仍返回 dict（吞异常），result 总是 dict
    result = result or {}
    success = bool(result.get("success"))
    error = result.get("error", "")
    # workflow 内部已算 elapsed_ms（time.monotonic 基准），与本测试 time.perf_counter
    # 基准不同 — 直接读 result 避免双计时
    elapsed_ms = result.get("elapsed_ms", 0)

    append_csv_row(
        RESULTS_DIR / "workflow_success_per_question.csv",
        CSV_HEADER,
        [item["id"], item["question"][:50], int(success), f"{elapsed_ms:.0f}", str(error)[:120]],
    )

    assert success, f"[{item['id']}] workflow failed: {error}"


def test_workflow_success_summary() -> None:
    """汇总 10 题的成功率 + 平均耗时。"""
    csv_path = RESULTS_DIR / "workflow_success_per_question.csv"
    if not csv_path.exists():
        pytest.skip("前面的 per-question 测试没跑")

    total = succeeded = 0
    latencies: list[float] = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            if row["success"] == "1":
                succeeded += 1
            latencies.append(float(row["elapsed_ms"]))

    rate = succeeded / total if total else 0
    avg_ms = sum(latencies) / len(latencies) if latencies else 0

    write_md_summary(
        RESULTS_DIR / "workflow_success_summary.md",
        "Workflow Success Summary",
        [
            f"- 题数: {total}",
            f"- 成功: {succeeded}",
            f"- 成功率: {rate:.1%}",
            f"- 平均耗时: {avg_ms:.0f}ms",
        ],
    )
    print(f"\n[summary] {succeeded}/{total} = {rate:.1%}, avg={avg_ms:.0f}ms")
