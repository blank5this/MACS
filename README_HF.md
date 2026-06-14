---
title: ERP AI Copilot — Live Demo
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
short_description: Ask ERP / procurement / inventory questions in Chinese. RAG over 18 policy docs.
---

# ERP AI Copilot — Live Demo

A working AI assistant for **ERP / inventory / procurement** questions. Built on the
[MACS (Multi-Agent Collaboration Stack)](https://github.com/blank5this/MACS) framework.

> Natural language in → cited answer out (with chunk references).

## What it does

Upload 18 Chinese ERP policy documents → the assistant searches them with **char-ngram + BM25 + RRF hybrid retrieval** → synthesizes a concise answer that **must cite the source chunks**.

## How to use

1. Type a question in Chinese (or English — Chinese gets the best retrieval).
2. Click an example to load a curated question.
3. See the answer on the left, retrieval log on the right.

## Try these questions

| Question | Why it's interesting |
|----------|---------------------|
| 如何处理采购退货？ | Tests retrieval + multi-section citation |
| 库存安全线是什么？如何设置补货策略？ | Tests formula recall (Z × σ × √L) |
| 供应商评级有哪些等级？ | Tests structured policy lookup |
| ABC 分析法是什么？ | Tests cross-document synthesis |
| 采购审批流程是什么？ | Tests 6-step workflow recall |

## Configuration

In **Space Settings → Variables and secrets**:

| Variable | Required? | Notes |
|----------|-----------|-------|
| `MINIMAX_API_KEY` | One of these | Recommended (cheapest) |
| `ANTHROPIC_API_KEY` | or this | Slightly higher quality |

Without a key, the demo still shows the **RAG retrieval log** — useful for debugging retrieval quality without spending tokens.

## Tech

- **Framework**: [MACS](https://github.com/blank5this/MACS) — MIT, 256 tests passing
- **Retrieval**: char-ngram + BM25 + RRF (see ADR-004)
- **Synthesis**: 6 LLM providers, default `MiniMax-M2.7`
- **UI**: Gradio

## Source

🔗 https://github.com/blank5this/MACS

Author: hiring AI engineers — DM via LinkedIn (see repo README).