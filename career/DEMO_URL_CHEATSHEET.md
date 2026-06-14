# Demo URL Cheat Sheet — pick the right URL for the right audience

> You have **3 demo entry points** and **4 audiences**. This one-pager tells
> you exactly which to send to whom, and what to do when something is down.

---

## Quick picker

| Audience | URL | Why |
|---|---|---|
| **面试官** (技术向) | https://macs-erp-copilot.onrender.com + 1 个 ADR 链接 | 30s 看效果，5min 看 ADR |
| **HR / 招聘** | https://huggingface.co/spaces/gkf123/macs-erp-copilot | 全球可访问，HF 品牌认知 |
| **同行 AI 工程师** | GitHub repo + `python -m macs_pkg.erp.web` | 看代码，30s 本地起 |
| **潜在客户 (非技术)** | 3min 录屏视频 | 不用动手，看演示 |

---

## 1. 面试官 (技术向) — Render URL

**发送内容**:
```
[Live demo]  https://macs-erp-copilot.onrender.com
[看 ADR]     https://github.com/blank5this/MACS/tree/main/docs/architecture
[看代码]     https://github.com/blank5this/MACS
```

**预期问题预案**:
- "URL 打不开怎么办?" → 见 § 故障恢复
- "为什么选 SQLite/Postgres?" → ADR-007 (read-only default) + ADR-004 (hybrid retrieval)
- "为什么不用 LangGraph/AutoGen?" → README 顶部 "Why MACS" 章节
- "能本地跑吗?" → `python -m macs_pkg.erp.web` (5s 起)

**关键话术** (60 秒):
> "MACS 是一个生产级多智能体框架, 跑着 ERP AI Copilot. 6 个 LLM provider, 5 个协作模式, 4 层 SQL 安全护栏, 8 个 ADR. 326 个测试. 你打开那个 URL, 问一句'哪些商品低于安全库存', 看一遍 ADR-003 和 ADR-007, 我等你."

---

## 2. HR / 招聘 — HF Spaces URL

**发送内容**:
```
[Live demo]  https://huggingface.co/spaces/gkf123/macs-erp-copilot
[项目页]    https://github.com/blank5this/MACS
[1 页摘要]  https://github.com/blank5this/MACS/blob/main/PROJECT_PITCH.md
```

**为什么不用 Render**:
- HF Spaces 在国内有时访问不稳 (Render 反而稳定)
- HR 不会点 1 个点不开的链接, HF 加载快
- HF 品牌对 AI/ML 圈认知度高

**关键话术** (30 秒):
> "我做了一个开源多智能体框架 + ERP AI Copilot. 1 页摘要在这里, live demo 在 HF 上, 1 个 URL 就能玩. 不需要 API key, 数据是种子数据. 你看 1 分钟, 有兴趣我们再聊细节."

---

## 3. 同行 AI 工程师 — GitHub + 本地

**发送内容**:
```
[Repo]     https://github.com/blank5this/MACS
[Quickstart]  README.md
[架构图]     docs/architecture/ARCHITECTURE_DIAGRAM.md
[ADR index]   docs/architecture/ADR_INDEX.md
```

**为什么这样发**:
- 工程师看 repo 头部一眼判断水平, 不需要 live demo
- README 顶部 "Why MACS" 6 维度对比表是关键
- ADR 是讨论起点, 8 篇可挑 1-2 篇精读

**关键话术**:
> "我做了 MACS, 多智能体框架 + ERP AI Copilot. 326 测试, 8 个 ADR. 你看 README 顶部 Why MACS 章节, 我想听你对我们 4 层 SQL 护栏的看法, 那是我最想讨论的."

---

## 4. 潜在客户 (非技术) — 录屏视频

**发送内容**:
```
[3 分钟演示]  (录屏 MP4, 邮件附件或网盘)
```

**录屏清单** (`scripts/record_demo_3min.py`):
1. 0:00 — 打开 http://127.0.0.1:7860
2. 0:10 — 问 "哪些商品库存低于安全库存?" → 5 个商品按缺口排序
3. 0:40 — 切到 KB tab, 问 "采购退货流程" → 引用 3 段政策
4. 1:20 — 切到 Text2SQL tab, 问 "本月销售总额" → 返 ¥8,250
5. 1:50 — 展示 /docs Swagger UI
6. 2:30 — 展示 /healthz (degraded/ok)
7. 2:50 — 结语 + GitHub

**为什么用视频**:
- 客户不会动手 → 录屏比 URL 高 5x 转化
- 你控制叙事节奏, 不会被随机问题打断

---

## 故障恢复 (5 分钟内救回)

### Render 404 / 503
```powershell
# 1. 看 dashboard 状态
start https://dashboard.render.com/

# 2. 如果是 Suspended, 点 Resume → 等 60s → 自动 deploy
# 3. 如果是 Crashed, 看 Logs → 改 env → 手动 Deploy
```

### HF Spaces sleep
```powershell
# Space 进入 sleep (48h 无访问)
# 解决: 任何用户访问 URL 即可唤醒, 等 30s
# 永久方案: 升级到付费 tier 或加定时 ping
```

### 本地起不来
```bash
# 99% 是这个错
ModuleNotFoundError: No module named 'fastapi'

# 解决
pip install fastapi 'uvicorn[standard]'

# 然后
MINIMAX_API_KEY=sk-... python -m macs_pkg.erp.web
```

### 工具返 500 (DB 不通)
```
GET /healthz → 看 db_backend 字段
- "postgres": 跑 `make erp-up` 起 docker
- "sqlite":   默认 fallback, 应该不会出错
- null:       检查 get_db_pool 日志
```

### LLM 返 503
```
GET /healthz → 看 llm_available
- false: 缺 API key, export MINIMAX_API_KEY=sk-... 重启
- true:  但还是 503 → 看 provider 是不是 MiniMaxProvider 用错 model name
         (注意: model 是 "MiniMax-M2.7" 不是 "M2.7" 或 "m27")
```

---

## 快速对照表

| 场景 | Render | HF Spaces | 本地 |
|---|---|---|---|
| 国内访问速度 | ✓✓✓ | ✓ | — |
| 国际访问速度 | ✓ | ✓✓✓ | — |
| 永久在线 (无人推) | ✗ (易睡) | ✗ (48h sleep) | ✓ |
| 真实 Postgres | ✓ | ✗ (SQLite only) | 看配置 |
| 多用户并发 | ✓ | ✓ | ✗ (单进程) |
| **首选用途** | **面试官** | **HR / 招聘** | **自己调试** |

---

## 测试清单 (投递前 5 分钟跑一遍)

```bash
# 1. Render 通
curl -I https://macs-erp-copilot.onrender.com/         # → 200

# 2. HF 通
curl -I https://huggingface.co/spaces/gkf123/macs-erp-copilot  # → 200

# 3. 本地通
python -m macs_pkg.erp.web  # → http://127.0.0.1:7860

# 4. 3 个 scenario 跑通
python examples/scenario_01_low_stock.py
python examples/scenario_02_purchase_return.py
python examples/scenario_03_text2sql.py
python examples/scenario_04_supplier_perf.py
```

任何一个 fail → 别发 URL, 先修.

---

**TL;DR**: 默认发 Render URL, HR 发 HF URL, 工程师发 GitHub, 客户发视频.
