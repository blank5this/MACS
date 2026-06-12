# Video 3 — RAG 知识库: 18 篇文档, 3 个问题, 9 个命中片段

> 60 秒录屏脚本 — Day 14 交付
> 版本: v1.0.0-erp-copilot
> 录制: `python scripts/record_video_03.py` (60s)
> 主题: 中文 char-ngram + BM25 + RRF 混合检索, 命中 ERP 制度文档

## 演示目标

把 MACS 内置的 RAG 引擎直接暴露给终端用户: 展示 18 篇 ERP 中文制度文档如何被一个**混合检索 (字粒度 embedding + BM25 关键词 + RRF 融合)** 命中, 输出 top-3 片段、相关度分数、文档路径, 让观众看清"知识库问答"在 60 秒内是怎么发生的。

## 录制流程 (timeline)

| 时段 | 屏幕画面 (on-screen text) | 旁白 (voiceover, 中文) |
| --- | --- | --- |
| **0–5s**  | `MACS ERP Copilot v1.0.0` + `Day 14 — RAG 知识库` | 18 篇 ERP 制度文档, 一个混合检索引擎, 三个真实问题。 |
| **5–12s** | KB 统计: 18 篇, 按 4 类 (operations 6 / warehouse 4 / procurement 5 / finance 3) | 知识库覆盖订单、仓储、采购、财务四个子域。 |
| **12–25s** | `Q1: 如何处理采购退货?` + 3 个 chunk 卡片 (score / 标题 / 分类 / 路径) | 第一个问题, 退货流程命中三段: 总览、流程、风险分级。 |
| **25–40s** | `Q2: MOQ 政策是什么? 起订量怎么定?` + 3 个 chunk 卡片 (其中 1 来自 ABC 分析) | 第二个问题, MOQ 自动跨文档命中 ABC 分析和 Lead Time 策略。 |
| **40–55s** | `Q3: ABC 分析法如何使用?` + 3 个 chunk 卡片 (来自 02_warehouse/01) | 第三个问题, ABC 分析法直接定位到源头文档, 引用可追溯。 |
| **55–60s** | 总结卡: `18 docs · 3 queries · 9 hits · 100% RRF` + GitHub 链接 | 十八篇文档, 三个问题, 九个命中片段, 端到端可追溯。 |

## 结尾卡片 (55–60s)

```
MACS ERP Copilot
18 docs · 3 queries · 9 hits · 100% RRF

github.com/<org>/MACS   v1.0.0-erp-copilot
```

## 旁白全文 (中文, 共 ~180 字)

> 十八篇 ERP 制度文档, 一个混合检索引擎, 三个真实业务问题。
> 知识库覆盖订单、仓储、采购、财务四个子域。
> 第一个问题, "如何处理采购退货", 命中三段: 退货总览、流程、风险分级。
> 第二个问题, "MOQ 政策是什么", 自动跨文档命中 ABC 分析和 Lead Time 策略。
> 第三个问题, "ABC 分析法如何使用", 直接定位到源头文档, 引用可追溯。
> 中文 char-ngram 嵌入、BM25 关键词评分、RRF 倒数秩融合 — 全栈自研。
> 十八篇文档, 三个问题, 九个命中, 端到端可追溯。
> 代码与文档: github.com/<org>/MACS, 当前版本 v1.0.0-erp-copilot。

## 关键脚本参数

```bash
# 完整 60s 演示 (含打字机延迟)
python scripts/record_video_03.py

# 快速冒烟 (无延迟)
python scripts/record_video_03.py --no-delay

# 录制并保存脚本
python scripts/record_video_03.py --output docs/videos/03_rag_transcript.md
```

## 与 Video 1/2 的对比

| 维度 | Video 1 (单 Agent) | Video 2 (多 Agent) | **Video 3 (RAG)** |
|------|---------------------|---------------------|--------------------|
| 入口 | 7 工具 | 4 Agent 工作流 | **18 篇 KB** |
| 主路径 | ToolAgent think/act | RuntimeEngine Hierarchical | **RRF 混合检索** |
| 产物 | 1 个 tool result | 4 段结构化报告 | **9 个 chunk** |
| LLM | 真实 MiniMax / Claude | 真实 MiniMax / Claude | **无需 LLM** |
| 演示时长 | 60s | 60s | **60s** |
| 文件 | `record_video_01.py` | `record_video_02.py` | **`record_video_03.py`** |

> 关键差异: Video 3 **不需要 LLM**, 完全离线可跑, 是 RAG 引擎独立性的最佳证明。
