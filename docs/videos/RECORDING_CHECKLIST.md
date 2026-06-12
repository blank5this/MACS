# 30 分钟上手检查表 — 录 3 段 60s ERP AI Copilot 演示

> 目标: 在 30 分钟内, 从空白环境到录完 3 段可发布的 mp4.
> 所有命令在 **Windows Git Bash** 下可直接复制粘贴.
> 详细 5 步法见 `docs/RECORDING_GUIDE.md`. 本表是它的"压缩执行版".

---

## Stage 0 — 环境检查 (5 分钟)

> 跑这 4 条, 全绿才进 Stage 1.

```bash
# (1) Python (已确认)
python --version          # 期望: Python 3.11+

# (2) Docker (已确认)
docker --version          # 期望: Docker 29.x 或更新

# (3) 录屏工具二选一 (当前环境 OBS / ffmpeg 未安装, 需先装一个)
where obs                 # 期望: 路径; 没装去 https://obsproject.com 下载 80MB
where ffmpeg              # 期望: 路径; 备用方案: choco install ffmpeg

# (4) 项目目录
ls "E:/MACS/scripts/record_video_"*.py     # 期望: 看到 3 个 .py
ls "E:/MACS/docs/videos/"                  # 期望: 3 个 script.md + 这个文件
```

**环境状态快照 (2026-06-12)**:
- Python 3.14.3 OK
- Docker 29.5.3 OK
- OBS Studio / ffmpeg 未安装 — **必须先装一个**才能录

---

## Stage 1 — Smoke Test 3 个脚本 (5 分钟)

> **必须先跑通过**才能正式录. `--no-delay` 跳过打字机效果, 3-5 秒一个.

| # | 命令 | 依赖 | 状态 |
|---|------|------|------|
| 01 | `cd "E:/MACS" && python scripts/record_video_01.py --no-delay` | Postgres + LLM key | 待 Postgres |
| 02 | `cd "E:/MACS" && python scripts/record_video_02.py --no-delay` | 无 (scripted provider) | OK |
| 03 | `cd "E:/MACS" && python scripts/record_video_03.py --no-delay` | 无 (本地 KB) | OK |

**当前 Smoke Test 结果 (2026-06-12)**:
- Video 01: ❌ **FAIL** — `psycopg_pool.PoolTimeout: pool initialization incomplete after 30.0 sec`
  - 修复: `cd "E:/MACS" && docker compose up -d erp_postgres` 或 `make erp-up`
  - 然后重跑: `python scripts/record_video_01.py --no-delay`
- Video 02: ✅ **PASS** — 完整跑完 4 Agent 接力, 总耗时 ~3 秒
- Video 03: ✅ **PASS** — 完整跑完 3 个问题 RAG 检索, ~150ms/问题

### 各脚本依赖 / 输出 / 关键参数速查

| 脚本 | 依赖 | LLM Provider | DB | 预期输出 (60s) |
|------|------|-------------|-----|---------------|
| `record_video_01.py` | Postgres 16 + ANTHROPIC_API_KEY 或 MINIMAX_API_KEY | 真实 Claude / MiniMax, 无 key 时退化 Mock | 必须 | 1 Agent · 7 Tools · MCP + RAG + NL→SQL 三个演示 |
| `record_video_02.py` | 无 (内置 `_ScriptedProvider` 4 段 JSON) | scripted-demo (无网络) | 不要 (pool=None) | Planner → Analyst → Buyer → Writer 4 段产物 |
| `record_video_03.py` | 无 (本地 `data/erp_kb/` 17 篇 .md) | 无 (纯检索) | 不要 | 3 个问题 · 9 段命中 · char-ngram+BM25+RRF |

**关键 CLI 参数**:
- `--no-delay` — smoke test / 录快版用, 跳过打字机
- `--delay 0.35` (02) / `--delay 0.25` (03) — 调每行打印间隔, 默认值已能塞 60s
- `--output xxx.md` — 同时保存字幕稿到文件

---

## Stage 2 — 起 Postgres + 设 LLM Key (2 分钟, 仅 Video 1)

```bash
# 起 Postgres + 自动 seed
cd "E:/MACS" && make erp-up

# 等 5 秒, 验证
make erp-check           # 期望: "DB pool ready, schema OK"

# 设 LLM key (二选一)
export ANTHROPIC_API_KEY=sk-ant-...
# 或
export MINIMAX_API_KEY=your_key
```

> 没有 LLM key 时 Video 01 也能跑 (退化 Mock), 但 3 个工具调用全是空响应 — **不推荐用于录屏**.

---

## Stage 3 — 录屏 (3 分钟/段, 共 9 分钟)

> 顺序: Video 1 → Video 2 → Video 3. 中间不停, 哪段挂了单独重录.

### 终端准备 (一次性)
1. 打开 **Windows Terminal**, 字体 `Cascadia Code` / 字号 **22pt**, 暗色
2. 窗口拉至 **1280x720**
3. 关 QQ / 微信 / 邮件 / 通知勿扰

### OBS 快捷键 (推荐)
- `Ctrl+F9` — 开始录
- `Ctrl+F10` — 停止录
- 输出格式 mp4, Encoder x264 / NVENC, CRF 23

### 录 Video 1
```bash
# (1) 切到 Windows Terminal
# (2) 按 Ctrl+F9
# (3) 立刻在 terminal 跑:
cd "E:/MACS" && python scripts/record_video_01.py
# (4) 脚本结束 (约 60s) 按 Ctrl+F10
# 输出: OBS 自动存到 ~/Videos/2026-06-12/01.mkv
```

### 录 Video 2
```bash
cd "E:/MACS" && python scripts/record_video_02.py
```

### 录 Video 3
```bash
cd "E:/MACS" && python scripts/record_video_03.py
```

---

## Stage 4 — 转码 mp4 (3 分钟)

> OBS 默认 mkv, 手动转 mp4 (GitHub 友好, 文件小).

```bash
# Video 1
ffmpeg -i ~/Videos/2026-06-12/01.mkv \
       -c:v libx264 -crf 23 -c:a aac \
       "E:/MACS/docs/videos/01_single_agent.mp4"

# Video 2
ffmpeg -i ~/Videos/2026-06-12/02.mkv \
       -c:v libx264 -crf 23 -c:a aac \
       "E:/MACS/docs/videos/02_multi_agent.mp4"

# Video 3
ffmpeg -i ~/Videos/2026-06-12/03.mkv \
       -c:v libx264 -crf 23 -c:a aac \
       "E:/MACS/docs/videos/03_rag.mp4"
```

**CRF 23 = sweet spot**: 60s × 720p ≈ 5-8 MB. 总 3 段 ≈ 15-25 MB.

**验证**:
```bash
ls -lh "E:/MACS/docs/videos/"*.mp4
# 期望: 3 个 mp4, 每个 5-8 MB
```

---

## Stage 5 — 替换 README 视频占位符 (1 分钟)

> 详见 `docs/videos/README_VIDEO_REPLACE.md`.

```bash
# (1) 编辑 E:/MACS/README.md, 第 27-33 行表格中"视频"列
# (2) 把 [录屏脚本](docs/videos/01_single_agent_script.md) 替换成
#     <video src="docs/videos/01_single_agent.mp4" controls width="640"></video>
# (3) 同样处理 Video 2 / Video 3
# (4) 本地预览: 直接在浏览器打开 README.md
```

---

## 完成后总检查

```bash
# 三件事都做完
[ ] docs/videos/01_single_agent.mp4  (5-8 MB)
[ ] docs/videos/02_multi_agent.mp4   (5-8 MB)
[ ] docs/videos/03_rag.mp4           (5-8 MB)
[ ] README.md 第 27-33 行表格已替换为 <video> 标签
[ ] git status 看到 3 个新 mp4 + README 改动
```

> 录完后走 `docs/videos/POST_RECORDING_CHECKLIST.md` 发布.

---

## 故障速查

| 现象 | 原因 | 修复 |
|------|------|------|
| `PoolTimeout` | Postgres 未起 | `make erp-up` 等 5s 再试 |
| 视频里中文乱码 | Windows cmd 默认 GBK | 用 **Windows Terminal** 或 `chcp 65001` |
| OBS 输出 0 字节 | 选了窗口但窗口未激活 | 重选 Window Capture 源 |
| Video 1 卡住无输出 | 无 LLM key + Mock 没生效 | 设 `ANTHROPIC_API_KEY` 或 `MINIMAX_API_KEY` |
| Video 2 报 ImportError | 项目根不在 sys.path | 始终 `cd "E:/MACS"` 后跑 |
| Video 3 命中 0 段 | `~/.macs/erp_rag/` 索引过期 | `python scripts/seed_erp_db.py` 或 `make erp-rag-rebuild` |

---

**生成时间**: 2026-06-12 (由 Claude 自动生成)
**配套文档**: `RECORDING_GUIDE.md` (5 步法详解) · `README_VIDEO_REPLACE.md` (替换指南) · `POST_RECORDING_CHECKLIST.md` (发布清单)