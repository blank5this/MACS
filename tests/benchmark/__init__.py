"""Benchmark suite for ERP AI Copilot.

包含 4 类可复现的 benchmark：

- ``test_rag_recall.py``        RAG 召回（20 中文问题，real data/erp_kb）
- ``test_sql_injection_fuzz.py`` SQL 注入对抗（50 payload，拒绝率）
- ``test_workflow_success.py``   Agent workflow 端到端成功率（真实接 LLM）
- ``test_latency.py``            P50/P95/P99 耗时（真实接 LLM）

跑法::

    # CI / 无 key（默认跳过真实 LLM 测试）
    pytest tests/benchmark/ -v -m "not requires_llm"

    # 真实 LLM 全跑
    pytest tests/benchmark/ -v
"""
