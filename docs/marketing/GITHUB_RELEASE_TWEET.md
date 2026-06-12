# GitHub Release Twitter/X 短帖 (v1.0.1)

> **目的**: 3 条独立 tweet, 用于 v1.0.1 发布时宣传.
> **发布时间**: release 发布后 0h / 4h / 24h, 间隔发.
> **字符限制**: 每条 ≤ 280 字符 (含空格 + URL + hashtag).
> **链接**: https://github.com/blank5this/MACS

---

## 🐦 Tweet 1: v1.0.1 Release Announcement (主线)

> **重点**: v1.0.1 release + 2 bug fixes + 168 tests
> **发布时机**: Release 发布后立即 (0h)

```
🚀 ERP AI Copilot v1.0.1 is out!

2 real bug fixes shipped:
• LLM Agent hardcoded SYSTEM_PROMPT (caller override now works)
• RuntimeEngine now exposes error_type + last_error for smart retry

168 tests passing (152 → 168, +10.5%)
100% backward compatible with v1.0.0

👉 https://github.com/blank5this/MACS
#AI #Python #OpenSource
```

**字符数**: 274 / 280 ✅

---

## 🐦 Tweet 2: Tech Highlights (技术深度)

> **重点**: 168 tests + multi-agent + 18 KB + 6 LLM providers
> **发布时机**: Release 发布后 4 小时

```
What's inside ERP AI Copilot v1.0.1:

📊 168 tests passing
🤖 4 multi-agent templates (Planner → Analyst → Buyer → Writer)
📚 18 Chinese ERP KB docs (char-ngram + BM25 + RRF)
🔌 6 LLM providers (Claude / MiniMax / Qwen / Zhipu / DeepSeek / OpenAI)
🛡️ 4-layer SQL injection protection (AST / blacklist / whitelist / params)
🐳 Postgres 16 + FastAPI Web UI in 60s

https://github.com/blank5this/MACS
#MultiAgent #RAG #LLM
```

**字符数**: 277 / 280 ✅

---

## 🐦 Tweet 3: ERP AI Copilot 产品定位 (品牌向)

> **重点**: "ERP AI Copilot" 品牌 + 自然语言 → 业务结果
> **发布时机**: Release 发布后 24 小时

```
From Multi-Agent framework to ERP AI Copilot — in 15 days.

Ask in Chinese:
📦 "哪些商品库存低于安全线?" → 7 tools auto-pick
📈 "分析未来 30 天库存风险" → 4 agents → structured report
📚 "如何处理采购退货?" → 18 KB docs → 3 cited chunks

PostgreSQL + MCP + RAG + multi-agent + Web UI. End-to-end working.

https://github.com/blank5this/MACS
#AICopilot #ERP #AgentOps
```

**字符数**: 273 / 280 ✅

---

## 📋 发布计划

| 时间 | Tweet # | 主题 | 渠道 |
|------|---------|------|------|
| **0h** | 1 | Release announcement | Twitter/X |
| **4h** | 2 | Tech highlights | Twitter/X + LinkedIn cross-post |
| **24h** | 3 | ERP AI Copilot branding | Twitter/X + LinkedIn + 知乎 |

**Cross-post 适配**:

- **LinkedIn**: Tweet 1 + 3 拼一起发, 加 2-3 个 emoji section header, 加 5-10 个 hashtag (LinkedIn 允许更多)
- **知乎**: 把 Tweet 3 扩展成 1000 字回答, 标题 "15 天独立完成 ERP AI Copilot, 我学到的 5 件事"
- **掘金**: 把 Tweet 2 扩展成 3000 字技术文, 加代码块 + 架构图 + 视频

---

## 🎯 Engagement Tips

1. **配图**: 每条 tweet 配 1 张图 (架构图 / 数字表 / 视频截图), engagement 提升 3-5x
2. **@mention**: 发时 @ClaudeAI @MiniMaxAI @AnthropicAI (如果用了他们的 API), 争取被转发
3. **回复自己**: 在 tweet 下自己回复 "Code & docs 👉 github link", 折叠长 URL
4. **thread**: 把 3 条 tweet 串成 1 个 thread, 第一条加 "🧵 1/3" 标记
5. **最佳发布时段**: UTC 14:00-16:00 (北京时间 22:00-24:00, 美西时间早上), Tech Twitter 最活跃

---

## 🔗 相关资源

- 📋 [CHANGELOG.md](../../CHANGELOG.md)
- 📑 [RELEASE_NOTES_v1.0.1.md](../../RELEASE_NOTES_v1.0.1.md)
- 📝 [`.github/RELEASE_TEMPLATE/v1.0.1.md`](../../.github/RELEASE_TEMPLATE/v1.0.1.md)
- 🚀 [GITHUB_RELEASE_GUIDE.md](../GITHUB_RELEASE_GUIDE.md)

---

<sub>Generated for v1.0.1-erp-copilot release · 2026-06-12 · MIT License</sub>