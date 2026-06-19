"""Shared fixtures & helpers for benchmark tests.

跑法::

    # CI / 无 key（默认排除真实 LLM 测试）
    pytest tests/benchmark/ -v -m "not requires_llm"

    # 真实 LLM 全跑（需 .env 有 ANTHROPIC_API_KEY / MINIMAX_API_KEY 等）
    pytest tests/benchmark/ -v
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Iterable

import pytest

# ===== Paths =========================================================

BENCHMARK_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BENCHMARK_DIR / "fixtures"
RESULTS_DIR = BENCHMARK_DIR / "results"


# ===== LLM key detection ============================================

def _has_real_llm_key() -> bool:
    """返回 True 当且仅当任一真实 provider key 在 env 里（且不是占位符）。"""
    for key in (
        "ANTHROPIC_API_KEY",
        "MINIMAX_API_KEY",
        "OPENAI_API_KEY",
        "QWEN_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        v = os.environ.get(key, "").strip()
        if v and not v.startswith("your-") and "REDACTED" not in v:
            return True
    return False


# ===== Fixtures ======================================================

@pytest.fixture(autouse=True)
def _force_utf8_io():
    """每个 test 自动调一次 force_utf8_io。幂等，无副作用。"""
    from macs_pkg._compat import force_utf8_io

    force_utf8_io()


@pytest.fixture
def real_workflow(real_provider):
    """session-scope 复用的 workflow fixture。

    `real_provider` 已 session-scope，workflow 也跟着 session 复用，
    避免每个 parametrize case 重新建 agent registry + tracer。
    """
    from examples.erp_copilot_multi_agent import _stage_build_workflow

    return _stage_build_workflow(real_provider)


@pytest.fixture(scope="session")
def real_provider():
    """真实 LLM provider fixture。无 key 时自动 skip。"""
    if not _has_real_llm_key():
        pytest.skip("需要真实 LLM API key（设置 ANTHROPIC_API_KEY 等）")
    from macs_pkg.erp.nl2sql import build_default_provider

    return build_default_provider(prefer="claude")


# ===== CSV / Markdown helpers =======================================

def append_csv_row(csv_path: Path, header: list[str], row: Iterable[Any]) -> None:
    """append-only CSV 写一行；首次调用自动写表头。

    强制 ``encoding="utf-8"`` + ``newline=""``（Windows 必须）。
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)
        w.writerow(list(row))


def write_md_summary(md_path: Path, title: str, lines: list[str]) -> None:
    """把 ``["- a: 1", "- b: 2", ...]`` 写到 markdown 文件。"""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(f"# {title}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


# ===== Auto-skip requires_llm tests when no key ======================

def pytest_collection_modifyitems(config, items):
    """无 key 时给所有 marker=requires_llm 的测试加 skip。"""
    if _has_real_llm_key():
        return
    skip_marker = pytest.mark.skip(reason="需要真实 LLM API key")
    for item in items:
        if "requires_llm" in item.keywords:
            item.add_marker(skip_marker)
