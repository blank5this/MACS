"""自动从 ``data/erp_kb/`` 18 篇中文政策文档生成 RAG 评测题目候选。

跑法::

    cd E:\\MACS
    python tests/benchmark/generate_rag_questions.py

输出::

    tests/benchmark/fixtures/rag_ground_truth_candidates.jsonl   (30 题候选)

**下一步**（用户操作）：

1. 打开 ``rag_ground_truth_candidates.jsonl``
2. 删掉明显不靠谱的 10 题
3. 把筛选后剩余 20 题改名为 ``rag_ground_truth.jsonl``

题目构造规则：
- 每篇文档 1-2 题
- 题型：标题问句（如「如何处理采购退货？」）、关键词查询（如「安全库存公式」）
- ``expected_doc_ids`` 期望命中的文档相对路径列表
- 同类目文档互为备选（用户问题可能匹配多篇）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# 跨平台强制 UTF-8 I/O
from macs_pkg._compat import force_utf8_io

force_utf8_io()


REPO_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = REPO_ROOT / "data" / "erp_kb"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# 标题 → 关键词问题模板（覆盖 18 篇文档）
_QUESTION_TEMPLATES: dict[str, list[str]] = {
    # 01_operations
    "01_订单到现金流程.md":         ["订单到现金的流程是什么？", "OTC 流程"],
    "02_Lead_Time_策略.md":         ["如何缩短采购 lead time？", "Lead Time 优化策略"],
    "03_退货处理流程.md":            ["如何处理客户退货？", "退货审批流程"],
    "04_客户信用管理.md":            ["客户信用如何评估？", "信用额度管理"],
    "05_销售价格管理.md":            ["销售价格审批流程？", "价格折扣管理"],
    "06_订单审批流程.md":            ["订单审批权限如何划分？", "订单审批"],
    # 02_warehouse
    "01_ABC分析法.md":               ["什么是 ABC 分析法？", "ABC 库存分类"],
    "02_循环盘点.md":                 ["循环盘点怎么做？", "盘点频率"],
    "03_安全库存公式.md":             ["安全库存怎么算？", "安全库存公式"],
    "04_过期物料处理.md":             ["过期物料如何处理？", "呆滞料处理"],
    # 03_procurement
    "01_供应商评估.md":               ["供应商怎么评估打分？", "供应商 KPI"],
    "02_RFQ_询报价流程.md":          ["RFQ 流程是怎样的？", "询价单"],
    "03_三方匹配.md":                  ["什么是三方匹配？", "3-way match"],
    "04_付款条款.md":                  ["付款条款有哪些？", "Net 30 付款"],
    "05_紧急采购.md":                  ["紧急采购如何审批？", "加急采购流程"],
    # 04_finance
    "01_库存估值方法.md":             ["库存估值用哪种方法？", "FIFO 移动加权"],
    "02_应计与预提.md":                ["应计与预提有什么区别？", "accrual 预提"],
    "03_期末结账.md":                  ["期末结账流程？", "月结步骤"],
}


def _strip_md_title(filename: str) -> str:
    """``03_安全库存公式.md`` → ``安全库存公式``"""
    return re.sub(r"^\d+_", "", filename).replace(".md", "")


def _build_questions() -> list[dict[str, Any]]:
    """扫描 KB 目录，按模板生成题目候选。"""
    questions: list[dict[str, Any]] = []
    qid = 0
    for category_dir in sorted(KB_ROOT.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name  # e.g. "01_operations"
        for md in sorted(category_dir.glob("*.md")):
            stem = md.name
            templates = _QUESTION_TEMPLATES.get(stem)
            if not templates:
                # 未知文档：跳过（避免生成不靠谱题目）
                continue
            rel_path = f"{category}/{stem}"
            for tmpl in templates:
                qid += 1
                questions.append({
                    "id": f"RAG-{qid:03d}",
                    "question": tmpl,
                    "expected_doc_ids": [rel_path],
                    "category": category,
                    "doc_title": _strip_md_title(stem),
                })
    return questions


def main() -> int:
    questions = _build_questions()
    if len(questions) < 30:
        print(f"[warn] 只生成了 {len(questions)} 题，需要至少 30 题候选")
    out = FIXTURES_DIR / "rag_ground_truth_candidates.jsonl"
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"[ok] wrote {len(questions)} candidate questions -> {out}")
    print(f"     下一步：删掉 10 题不靠谱的，改名为 rag_ground_truth.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
