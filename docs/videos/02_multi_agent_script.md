# Video 2 — 多 Agent 协作: 1 个问题, 4 段产物

> 60 秒录屏脚本 — Day 11 交付
> 版本: v1.0.0-erp-copilot
> 录制: `python scripts/record_video_02.py` (60s)
> 主题: 4 个 Agent 协作, 1 个问题, 4 段产物

## 演示目标

用 InventoryRiskWorkflow 跑一次完整的多 Agent 链路, 展示从一句业务问题到结构化报告的全过程。突出"4 个 Agent 协作"的多 Agent 角度, 让观众在 60 秒内看清分阶段产物的差异。

## 录制流程 (timeline)

| 时段 | 屏幕画面 (on-screen text) | 旁白 (voiceover, 中文) |
| --- | --- | --- |
| **0–5s**  | `MACS ERP Copilot v1.0.0` + `Day 11 — 多 Agent 协作` | 一句话问题丢进来, 四个 Agent 接力。 |
| **5–15s** | `Step 1/4  erp_planner` + 日志 `subtasks = 3` | 第一棒, 规划 Agent 拆解成三条子任务。 |
| **15–25s** | `Step 2/4  erp_inventory_analyst` + `low_stock_count: 2` | 第二棒, 库存分析 Agent 锁定 2 个低库存。 |
| **25–40s** | `Step 3/4  erp_purchase_specialist` + 表格 (supplier × qty × cost) | 第三棒, 采购 Agent 给出每条 SKU 的供应商与数量。 |
| **40–50s** | `Step 4/4  erp_report_writer` + Markdown 报告 | 第四棒, 报告 Agent 整合成可读的中文报告。 |
| **50–60s** | 总结卡: `4 Agents · 1 Question · 4 Outputs` + GitHub 链接 | 四个 Agent, 一个问题, 四段产物, 全自动。 |

## 结尾卡片 (50–60s)

```
MACS ERP Copilot
4 Agents · 1 Question · 4 Outputs

github.com/<org>/MACS   v1.0.0-erp-copilot
```

## 旁白全文 (中文, 共 ~180 字)

> 把一句"分析未来 30 天库存风险"丢进系统。
> 规划 Agent 把它拆成三条子任务。
> 库存分析 Agent 跑完, 锁定两个低于安全库存的商品。
> 采购 Agent 接棒, 给每个 SKU 匹配供应商、数量、成本。
> 最后, 报告 Agent 把三段 JSON 整合成一份中文 Markdown 报告。
> 四个 Agent, 一个问题, 四段产物 — 全流程零人工。
> 代码与模板: github.com/<org>/MACS, 当前版本 v1.0.0-erp-copilot。

## 录制命令

```bash
python scripts/record_video_02.py
# 录制 (含 typewriter 延迟, 总时长约 60s):
python scripts/record_video_02.py --no-delay   # 快速自检
python scripts/record_video_02.py --output transcript.md
```

## 关键看点 (剪辑用)

- 0:05  启动 banner — 强调 "v1.0.0-erp-copilot"
- 0:15  planner 输出 JSON 中的 `subtasks`
- 0:25  analyst 输出中的 `risk_level: critical`
- 0:35  buyer 输出中的 `recommended_quantity`
- 0:45  writer 输出的 Markdown 标题
- 0:55  总结卡 + GitHub 链接

