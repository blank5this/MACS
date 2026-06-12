# Video 1 — 单 Agent 混合工具演示 (60 秒)

## 目标

展示 ERPCopilotAgent 在**单次会话**中, 把 5 个 MCP 工具 + RAG + NL→SQL 三种能力无缝衔接起来, 回答一个跨领域的 ERP 业务问题.

**核心信息**: 一个 Agent + 一行中文问题 = 数据查询 + 知识检索 + SQL 注入, 全自动.

## 旁白脚本 (60s, ~250 字)

| 时间 | 旁白 | 屏幕 |
|------|------|------|
| 0-5s | "传统 ERP 系统, 业务人员要写 SQL、查文档、问同事. 我们的 AI Copilot 把这三件事合并成一个问题." | 终端标题: `ERP AI Copilot — Single Agent Demo` |
| 5-15s | "底层接 PostgreSQL, 17 篇 ERP 制度手册, 6 个 LLM Provider. 今天演示单 Agent 三种能力串联." | 截图: 项目结构树, 标红 `agents/copilot_agent.py` |
| 15-25s | "问个跨领域问题: 哪些商品缺货? 这些商品有什么补货策略?" | 终端输入第一行 |
| 25-40s | "Agent 自动选工具: 1) 调 get_low_stock_products 拉数据; 2) 调 ask_knowledge_base 查 MOQ 政策; 3) 用 LLM 综合成可执行建议." | 终端流式输出, 3 段都标黄 |
| 40-55s | "结果: 4 个低库存商品, 3 段引用源, 1 条建议 (给 SKU-0003 补 80 件, 走供应商 A 优先因 A 类物料)." | 输出报告高亮 |
| 55-60s | "代码 100% 开源, MCP 工具 + RAG + SQL 验证 4 层防护. 链接见 README." | GitHub URL 浮层 |

## 命令

录制时在终端跑:

```bash
cd E:\MACS
python examples/erp_copilot_single_agent.py
```

输出会被 `scripts/record_video_01.py` 自动 pipe 到一个干净的 60s 窗口, 字幕叠在视频下方.

## 录制步骤 (OBS Studio 推荐)

1. **场景**: 一个 1920×1080 终端窗口 + 摄像头 (可选, 解释者头像).
2. **音频**: 旁白预录 (建议用 Audacity 录 .wav, 60s 上下), 导入 OBS.
3. **屏幕源**: `Window Capture` → 选终端, 字体 18pt+ 等宽.
4. **录 60 秒**, 导出 1080p H.264 mp4, 命名 `01_single_agent.mp4`.
5. 放到 `docs/videos/01_single_agent.mp4`.

## 输出验证

- 视频 ≤ 62 秒.
- 三段能力 (MCP / RAG / 综合建议) 都在画面上可读.
- 末尾有 GitHub 链接 (README 里的).
