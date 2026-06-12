# 录后发布检查清单 (Post-Recording Checklist)

> 3 段 60s mp4 已录完 + 转码 + README 已替换. 接下来 30 分钟内做完这 4 件事, 视频就正式"发布"了.
> 目标: 录屏 + 发布 + 简历同步一气呵成, 当天就有投出去的资本.

---

## 1. Git Commit & Push (5 分钟)

### 文件预检

```bash
cd "E:/MACS"

# 确认 3 个 mp4 都在
ls -lh docs/videos/*.mp4
# 期望: 01_single_agent.mp4 / 02_multi_agent.mp4 / 03_rag.mp4, 各 5-8 MB

# 确认 README 改了
git diff README.md | head -50
# 期望: 看到 <video> 标签替换 [录屏脚本]

# 确认 .gitignore 没拦 mp4
git check-ignore docs/videos/*.mp4
# 期望: 无输出 (表示 mp4 不会被 .gitignore 跳过)
# 如果有输出, 编辑 .gitignore, 去掉 *.mp4 这一行
```

### Commit 模板 (直接复制)

```bash
git add docs/videos/01_single_agent.mp4 \
        docs/videos/02_multi_agent.mp4 \
        docs/videos/03_rag.mp4 \
        README.md \
        docs/videos/RECORDING_CHECKLIST.md \
        docs/videos/README_VIDEO_REPLACE.md \
        docs/videos/POST_RECORDING_CHECKLIST.md

git commit -m "feat(erp-copilot): add 3 demo videos (60s each, 720p, CRF 23)

- 01_single_agent.mp4: 1 agent, 7 tools (MCP + RAG + NL->SQL)
- 02_multi_agent.mp4: 4 agents collaborate (Planner/Analyst/Buyer/Writer)
- 03_rag.mp4: 17 docs, char-ngram + BM25 + RRF hybrid retrieval

Each ~5-8MB, total ~20MB. README video column updated to inline <video>."

git push origin main
```

### 验证 Push 成功

```bash
# GitHub 仓库页打开 docs/videos/, 看到 3 个 mp4
# README 表格里看到 3 个可播放的视频框
```

---

## 2. GitHub Release (10 分钟)

### 创建 Release (网页操作)

1. 打开 GitHub 仓库 → **Releases** → **Draft a new release**
2. **Choose a tag**: 输入 `v1.0.1-erp-copilot` → 选 "Create new tag on publish"
3. **Release title**: `v1.0.1 — ERP AI Copilot (3 demo videos)`
4. **Description** (模板, 直接复制粘贴):

```markdown
## ERP AI Copilot v1.0.1 — 3 Demo Videos

3 段 60s 终端录屏, 演示 MACS 框架在 ERP 场景的能力.

### Video 1 — 单 Agent 混合工具 (1 Agent · 7 Tools)

<video src="https://github.com/blank5this/MACS/raw/main/docs/videos/01_single_agent.mp4" controls width="640"></video>

7 工具自动选择: MCP 低库存查询 + RAG 制度问答 + NL→SQL Top 3 销量.

### Video 2 — 多 Agent 协作 (4 Agents)

<video src="https://github.com/blank5this/MACS/raw/main/docs/videos/02_multi_agent.mp4" controls width="640"></video>

Planner → Inventory Analyst → Purchase Specialist → Report Writer. 1 个问题, 4 段结构化产物.

### Video 3 — RAG 知识库 (17 中文文档)

<video src="https://github.com/blank5this/MACS/raw/main/docs/videos/03_rag.mp4" controls width="640"></video>

char-ngram embedding + BM25 + RRF 混合检索. 3 个问题命中 9 段引用.

---

**升级**: 无代码改动, 仅添加演示视频.
**总下载**: ~20 MB (3 mp4)
**目标用户**: 正在评估 ERP AI 落地的开发者 / 架构师 / 产品经理.
```

5. **Attach binaries**: 把这 3 个 mp4 直接拖进上传区
   - `01_single_agent.mp4`
   - `02_multi_agent.mp4`
   - `03_rag.mp4`
6. 点 **Publish Release**

### 验证

- Release 页面能看到 3 个视频内嵌播放
- mp4 文件可以单独下载
- Release tag 在 GitHub 主页显示

---

## 3. 简历同步 (10 分钟)

### 简历项目描述 (一段话模板, 直接复制)

```
MACS — Multi-Agent Collaboration Stack (Python / FastAPI / PostgreSQL / MCP / RAG)
2026.05 - 2026.06  ·  github.com/blank5this/MACS  ·  ★ PyPI 已发布

基于自研 MACS 框架构建 ERP AI Copilot, 把自然语言映射到库存/销售/采购/知识库,
端到端跑通 PostgreSQL + MCP + RAG + 多 Agent 协作.

核心能力:
  - 单 Agent 7 工具自动选择 (MCP / RAG / NL→SQL)
  - 多 Agent 协作 (Planner → Analyst → Buyer → Writer)
  - RAG 知识库 (17 篇中文文档, char-ngram + BM25 + RRF 混合检索)
  - FastAPI Web UI (3 Tab 浏览器演示)

数据: 152 单元测试通过, 3 段 60s 录屏演示, 端到端 LLM 调用延迟 < 5s.
```

### 简历附件 — 视频二维码 (推荐)

为 3 段 mp4 生成可扫码的二维码 (放在简历 PDF 上):

```bash
# 用 qrencode (需先 choco install qrencode 或类似工具)
qrencode -o video1_qr.png "https://github.com/blank5this/MACS/blob/main/docs/videos/01_single_agent.mp4"
qrencode -o video2_qr.png "https://github.com/blank5this/MACS/blob/main/docs/videos/02_multi_agent.mp4"
qrencode -o video3_qr.png "https://github.com/blank5this/MACS/blob/main/docs/videos/03_rag.mp4"
```

> 没装 qrencode 的话, 直接贴 GitHub URL 也行 (招聘官会自己点).

### 简历投递版本建议

针对深圳南山 AI 岗 20k+ 简历, 强调 3 点:
1. **自研框架** (MACS) — 不是调 API, 是从 0 搭框架
2. **端到端可演示** (3 段视频) — 招聘官 60s 看完就知道你能干嘛
3. **完整工程实践** (测试 + CI + Docker + 文档) — 不是 demo 项目, 是生产级

---

## 4. LinkedIn / B 站 / 知乎 同步 (10 分钟)

### LinkedIn 帖子模板 (英文, 适合海归招聘官)

```
🚀 Just shipped: ERP AI Copilot — 3 demo videos (60s each)

Built on top of my open-source MACS framework (Multi-Agent Collaboration Stack).
3 self-contained terminals recording, no fancy edits:

📹 Video 1 — Single agent with 7 tools (MCP + RAG + NL→SQL)
📹 Video 2 — 4 agents collaborate: Planner → Analyst → Buyer → Writer
📹 Video 3 — RAG over 17 Chinese docs (char-ngram + BM25 + RRF)

PyPI: https://pypi.org/project/macs_pkg/
GitHub: https://github.com/blank5this/MACS
3 demo videos: https://github.com/blank5this/MACS/tree/main/docs/videos

#AI #LLM #RAG #MCP #MultiAgent #ERP #OpenSource
```

### B 站视频标题模板 (中文, 适合国内技术圈)

```
【60s 演示】我用自研多 Agent 框架做了一个 ERP AI Copilot
```

3 段视频分别传:
1. `60s ERP AI Copilot 演示 1 — 单 Agent + 7 工具自动选`
2. `60s ERP AI Copilot 演示 2 — 4 Agent 接力: Planner→Analyst→Buyer→Writer`
3. `60s ERP AI Copilot 演示 3 — 中文 RAG: char-ngram+BM25+RRF 混合检索`

每个视频简介:
```
开源 ERP AI Copilot, 基于自研 MACS 多 Agent 框架.
代码: github.com/blank5this/MACS
PyPI: pypi.org/project/macs_pkg
文档: 见仓库 docs/videos/
```

### 知乎回答模板 (适合在 AI/ERP 问题下引流)

在"如何用 LLM 做企业 ERP" 或 "Multi-Agent 框架对比" 问题下, 答:

```
我做了一个开源项目, 端到端演示了 LLM + 多 Agent + RAG 在 ERP 场景的落地:
github.com/blank5this/MACS

3 段 60s 视频在仓库 docs/videos/, 核心思路:
1. 单 Agent 7 工具 (MCP + RAG + NL→SQL)
2. 多 Agent 4 段接力
3. 中文混合检索 (char-ngram + BM25 + RRF)

有兴趣可以看 README 里的视频, 60s 看完就知道能不能用.
```

---

## 总检查 (4 件事都做完才算发布完)

```bash
# 1. GitHub 上能看到 3 个 mp4 在 docs/videos/
# 2. README 表格里 3 个 <video> 标签能播放
# 3. v1.0.1-erp-copilot Release 已发布
# 4. 简历 / LinkedIn / B 站 / 知乎 至少更新 1 处

[ ] git push 完成
[ ] GitHub Release v1.0.1 已 publish
[ ] 简历项目描述已加 "3 段 60s 演示视频" 字样
[ ] LinkedIn 帖子已发 + tag 3-5 个
```

---

## 后续 7 天动作 (可选, 不阻塞)

| Day | 动作 | 预期收益 |
|-----|------|----------|
| Day 1 | 把 3 段 mp4 上传到 B 站 | 国内流量 +1 |
| Day 2 | 在掘金发技术文章 + 视频嵌入 | 开发者社区曝光 |
| Day 3 | 知乎回答 3-5 个相关问题引流 | 长尾 SEO |
| Day 4 | Twitter 发英文版 (LinkedIn 同款) | 海外机会 |
| Day 5 | 把 3 段视频合并剪 1 段 3min "完整版" | B 站长视频流量 |
| Day 6 | 在 V2EX / NodeSeek 发贴 | 国内技术社区 |
| Day 7 | 复盘数据: 简历下载量 / GitHub star 增量 / 私信数 | 决定是否继续投入 |

---

**生成时间**: 2026-06-12
**前置条件**: `docs/videos/0*_*.mp4` 已存在 + `README.md` 已替换
**配套**: `RECORDING_CHECKLIST.md` (录制前) · `README_VIDEO_REPLACE.md` (替换)