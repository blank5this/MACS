"""RAG 召回 benchmark：20 个中文问题 × 真实 ``data/erp_kb/`` 语料。

不需要 LLM（纯检索）。CI 友好。

数据源（自动 fallback）：

1. ``fixtures/rag_ground_truth.jsonl``        — 用户筛过的正式集（优先）
2. ``fixtures/rag_ground_truth_candidates.jsonl`` — 自动生成 30 题（取前 20）

指标：``recall@1`` / ``recall@3`` / ``recall@5`` / ``MRR`` → ``results/rag_recall_summary.md``。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from macs_pkg.erp.rag.query import ask_kb

from .conftest import FIXTURES_DIR, RESULTS_DIR, append_csv_row, write_md_summary

CSV_HEADER = ["id", "question", "expected", "retrieved", "r@1", "r@3", "r@5", "rr"]


def _pick_ground_truth_source() -> tuple[Path, int | None]:
    """决定读哪个 jsonl + 限制条数。"""
    official = FIXTURES_DIR / "rag_ground_truth.jsonl"
    if official.exists():
        return official, None
    candidates = FIXTURES_DIR / "rag_ground_truth_candidates.jsonl"
    if not candidates.exists():
        pytest.skip("RAG 题库不存在。先跑：python tests/benchmark/generate_rag_questions.py")
    return candidates, 20


def _load_ground_truth() -> list[dict[str, Any]]:
    src, limit = _pick_ground_truth_source()
    items: list[dict[str, Any]] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
        if limit and len(items) >= limit:
            break
    return items


GROUND_TRUTH = _load_ground_truth()


@pytest.mark.parametrize("item", GROUND_TRUTH, ids=lambda x: x["id"])
@pytest.mark.asyncio
async def test_rag_recall_per_question(item: dict[str, Any]) -> None:
    """每个 query 跑 top-5 检索。module-level engine cache 跨 case 复用。"""
    question = item["question"]
    expected = set(item["expected_doc_ids"])

    result = await ask_kb(question, top_k=5)
    # Windows 下 Path.relative_to 返回 \\，归一化到 /
    retrieved = [c.rel_path.replace("\\", "/").lstrip("/") for c in result.chunks]

    hit_at_k = {1: False, 3: False, 5: False}
    for k in (1, 3, 5):
        if expected & set(retrieved[:k]):
            hit_at_k[k] = True
    reciprocal_rank = 0.0
    for i, doc in enumerate(retrieved, start=1):
        if doc in expected:
            reciprocal_rank = 1.0 / i
            break

    append_csv_row(
        RESULTS_DIR / "rag_recall_per_question.csv",
        CSV_HEADER,
        [
            item["id"],
            question[:60],
            ";".join(sorted(expected)),
            ";".join(retrieved),
            int(hit_at_k[1]),
            int(hit_at_k[3]),
            int(hit_at_k[5]),
            f"{reciprocal_rank:.3f}",
        ],
    )

    # 不 hard assert：题库可能含个别召回不到的题（e.g. 用户筛题时 query 与
    # 文档标题不完全匹配）。这些 case 仍写到 CSV，让 aggregate test 报告。
    # aggregate test 期望 recall@5 >= 90%，个别题 miss 不影响通过。


def test_rag_recall_aggregate() -> None:
    """汇总：recall@1/3/5 + MRR。"""
    csv_path = RESULTS_DIR / "rag_recall_per_question.csv"
    if not csv_path.exists():
        pytest.skip("前面的 per-question 测试没跑")

    total = 0
    sum_r1 = sum_r3 = sum_r5 = sum_rr = 0.0
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            sum_r1 += int(row["r@1"])
            sum_r3 += int(row["r@3"])
            sum_r5 += int(row["r@5"])
            sum_rr += float(row["rr"])

    r1 = sum_r1 / total if total else 0
    r3 = sum_r3 / total if total else 0
    r5 = sum_r5 / total if total else 0
    mrr = sum_rr / total if total else 0

    write_md_summary(
        RESULTS_DIR / "rag_recall_summary.md",
        "RAG Recall Summary",
        [
            f"- 题数: {total}",
            f"- recall@1: {r1:.1%}",
            f"- recall@3: {r3:.1%}",
            f"- recall@5: {r5:.1%}",
            f"- MRR: {mrr:.3f}",
        ],
    )
    print(f"\n[summary] {total} 题 | R@1={r1:.1%} R@3={r3:.1%} R@5={r5:.1%} MRR={mrr:.3f}")
    # recall@5 至少 90%（用户筛过的正式集应该召回率高）
    assert r5 >= 0.9, f"recall@5 = {r5:.1%} 低于 90%，RAG 索引可能有问题或题库太偏"
