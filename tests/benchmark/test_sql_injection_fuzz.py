"""SQL 注入对抗 benchmark：用 50 个 fuzzing payload 测拒绝率。

不需要 LLM，纯规则校验。CI 友好（默认 ``-m "not requires_llm"``）。

预期：拒绝率 >= 98%（允许 1/50 漏报用于 fail-loud — e.g. ``@@version`` 全局变量）。
"""
from __future__ import annotations

import csv

import pytest

from macs_pkg.erp.nl2sql import SQLValidator, UnsafeSQLError

from .conftest import FIXTURES_DIR, RESULTS_DIR, append_csv_row, write_md_summary

CSV_HEADER = ["payload", "rejected", "reason"]

# module-scope 复用：SQLValidator 构造时 compile 30+ 关键词正则，
# 51 个 case 不必每次都重新 compile。
VALIDATOR = SQLValidator()


def _load_payloads() -> list[str]:
    path = FIXTURES_DIR / "injection_payloads.txt"
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


PAYLOADS = _load_payloads()


@pytest.mark.parametrize("payload", PAYLOADS, ids=lambda p: f"p{p[:30]!r}")
def test_validator_rejects_injection(payload: str) -> None:
    """每个 payload 必须被 SQLValidator 拒绝（抛 UnsafeSQLError）。"""
    rejected = False
    reason = ""
    try:
        VALIDATOR.validate(payload)
    except UnsafeSQLError as exc:
        rejected = True
        reason = str(exc)[:120]
    except Exception as exc:
        reason = f"unexpected: {exc.__class__.__name__}: {exc}"[:120]

    append_csv_row(
        RESULTS_DIR / "sql_injection_per_payload.csv",
        CSV_HEADER,
        [payload[:100], rejected, reason],
    )

    assert rejected, f"validator 未拒绝 payload: {payload[:80]!r}（reason={reason}）"


def test_injection_rejection_rate() -> None:
    """汇总：拒绝率必须 >= 98%。"""
    csv_path = RESULTS_DIR / "sql_injection_per_payload.csv"
    if not csv_path.exists():
        pytest.skip("前面的 per-payload 测试没跑（无 csv 结果）")

    total = 0
    rejected = 0
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            if row["rejected"] == "True":
                rejected += 1

    rate = rejected / total if total else 0.0
    write_md_summary(
        RESULTS_DIR / "sql_injection_summary.md",
        "SQL Injection Rejection Rate",
        [
            f"- 总数: {total}",
            f"- 拒绝: {rejected}",
            f"- 拒绝率: {rate:.1%}",
            f"- 阈值: 98%",
            f"- 状态: {'✓ PASS' if rate >= 0.98 else '✗ FAIL'}",
        ],
    )
    print(f"\n[summary] 拒绝率: {rejected}/{total} = {rate:.1%}")
    assert rate >= 0.98, f"拒绝率 {rate:.1%} 低于 98% 阈值"
