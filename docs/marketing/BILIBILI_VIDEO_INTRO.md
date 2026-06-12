---
title: 我用 15 天, 把 Java 工程师变成了 AI 应用工程师 (ERP AI Copilot)
platform: B 站
target_audience: 想转 AI 的 Java/后端工程师, AI 应用工程师求职者, 对 Agent / RAG 感兴趣的开发者
posting_priority: high
status: draft
---

# 我用 15 天, 把 Java 工程师变成了 AI 应用工程师 (ERP AI Copilot)

## 钩子 (前 3 行)

23 岁, Java 工程师, 月薪 8K.  
15 天, 做了 22 个新文件, 168 个测试, 3 段 60 秒视频.  
今天带你看看, 我是怎么从一个只会写 CRUD 的 Java 仔, 做出一个能投 AI 岗简历的项目.

---

## 视频内容

### 🎬 视频 1: 单 Agent 跑通 7 工具混合调用 (60s)

用户问"哪些商品库存低于安全线?", 一个 Agent, 7 个工具 (5 个 MCP + RAG + NL→SQL), LLM 自动选. 看 7 个工具怎么协同, 怎么避免 prompt 膨胀.

### 🎬 视频 2: 多 Agent 协作做库存风险报告 (60s)

用户问"分析未来 30 天库存风险并给出采购建议". 4 个 Agent 接力: Planner 拆任务 → Inventory Analyst 跑库存 → Purchase Specialist 跑采购 → Report Writer 写报告, 落盘 Markdown. 单 Agent 70% 成功率 → 多 Agent 95%, 数字是真的.

### 🎬 视频 3: RAG 知识库混合检索 (60s)

18 篇中文 ERP 文档, 用户问"如何处理采购退货?". 不调 Embedding, 用 char-ngram + BM25 + RRF 三件套, top_k=3 默认, 200ms 端到端. CI 也能跑, 0 token 成本.

---

## 时间戳 (建议)

```
00:00 介绍 (我是谁 / 为什么做 / 项目能干嘛)
00:30 视频 1: 单 Agent + 7 工具混合
02:30 视频 2: 多 Agent 协作 + 库存风险报告
04:30 视频 3: RAG 混合检索 + 知识库问答
06:30 总结: 怎么从 Java 转 AI 应用工程师
07:30 简历怎么写 / GitHub 怎么放
08:00 结尾
```

---

## 为什么做这个项目

- 我在深圳南山, 想冲 AI 应用工程师岗 (15-25K)
- 简历上需要一个能讲清楚的 AI 项目, 不是又一个 "Agent hello world"
- ERP 业务我能理解, 选了这个场景切入
- 15 天交付: 数据层 → MCP → NL→SQL → RAG → 单 Agent → 多 Agent → Web UI → CI → 视频

---

## 项目地址

👉 GitHub: https://github.com/blank5this/MACS

包含完整代码、3 段视频脚本、4 CI jobs、5 张 ERP 表、168 测试, MIT 协议, 直接 clone 就能跑.

---

## 一键三连 + 关注

如果视频对你有用, 求 **点赞 + 投币 + 收藏**, 这是我继续做下去的最大动力.  
关注我, 下期讲: 怎么用这个项目面试 AI 应用工程师岗 (高频 5 题答案 + 套路).

有问题评论区见, 我会一条一条回.

---

## 相关 Tag

`#AI工程师` `#转行AI` `#多Agent` `#RAG` `#ERP` `#FastAPI` `#Python` `#Java转AI` `#大模型应用` `#求职`

---

## 自检清单

- [ ] 开头 1 行钩子包含"15 天"+"Java 工程师"+"AI", 抓眼球
- [ ] 3 段视频各有 1 行口语化介绍, 不剧透太多
- [ ] 时间戳覆盖介绍 / 单 Agent / 多 Agent / RAG / 总结 / 结尾 6 段
- [ ] 有明确的"一键三连 + 关注"引导
- [ ] GitHub 链接出现在视频简介中部和结尾
- [ ] 5 个相关 tag, 中文为主, 含 `#AI工程师` `#多Agent` `#RAG`
- [ ] 语气口语化, 像在跟朋友聊天, 不像念稿
- [ ] 字数在 200-400 字之间 (不含时间戳 / tag)
- [ ] 视频占位说明 (录制后替换) 清晰
- [ ] 结尾有"下期预告", 引导关注