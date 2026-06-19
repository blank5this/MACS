"""Agent workflow 耗时 benchmark：P50 / P95 / P99。

真实接 LLM（marker = ``requires_llm``），无 key 时自动 skip。

复用 :mod:`test_workflow_success` 跑出的 per-question CSV（需要先跑），
统计耗时分布并写 ``results/latency_summary.md``。

不引入 pytest-benchmark（额外依赖），用标准库 ``statistics.quantiles``。
"""
from __future__ import annotations

import csv
import statistics

import pytest

from .conftest import RESULTS_DIR, write_md_summary

pytestmark = pytest.mark.requires_llm


def test_latency_percentiles() -> None:
    """读 per-question CSV，算 P50/P95/P99。"""
    csv_path = RESULTS_DIR / "workflow_success_per_question.csv"
    if not csv_path.exists():
        pytest.skip("需要先跑 test_workflow_success.py 生成数据")

    latencies: list[float] = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            latencies.append(float(row["elapsed_ms"]))

    if len(latencies) < 5:
        pytest.skip(f"数据不足（{len(latencies)} 条），建议先跑 10 题 workflow")

    # statistics.quantiles 用法：n=100 把数据切 99 等分，返回 99 个边界
    # quantiles[49] = P50, quantiles[94] = P95, quantiles[98] = P99
    qs = statistics.quantiles(latencies, n=100, method="inclusive")
    p50, p95, p99 = qs[49], qs[94], qs[98]
    mean = statistics.mean(latencies)
    stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0
    s = sorted(latencies)
    mn, mx = s[0], s[-1]

    write_md_summary(
        RESULTS_DIR / "latency_summary.md",
        "Workflow Latency Summary",
        [
            f"- 样本数: {len(latencies)}",
            f"- mean: {mean:.0f}ms",
            f"- stdev: {stdev:.0f}ms",
            f"- min: {mn:.0f}ms",
            f"- max: {mx:.0f}ms",
            f"- P50: {p50:.0f}ms",
            f"- P95: {p95:.0f}ms",
            f"- P99: {p99:.0f}ms",
        ],
    )
    print(f"\n[summary] P50={p50:.0f}ms P95={p95:.0f}ms P99={p99:.0f}ms (n={len(latencies)})")
