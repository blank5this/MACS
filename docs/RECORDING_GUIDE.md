# 60s 视频录屏指南

> 录 Video 1/2/3 用的 5 步法. 选 OBS / Windows Terminal 自带 / ffmpeg 任一工具都行.
> 5 分钟学会, 2 小时录完 3 段, 终身复用.

## TL;DR

```bash
# 1. 装 OBS Studio (https://obsproject.com) 或用 Windows Terminal 录屏
# 2. 调整终端字体: 22pt, 宽 14, 暗色背景
# 3. 跑脚本, 同时录屏
# 4. 视频转 mp4, 放 docs/videos/
# 5. README 替换 .mp4 链接
```

---

## 工具选择 (任选 1)

| 工具 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| **OBS Studio** | 免费, 功能强, 直接 mp4 输出 | 学习曲线 | **推荐 — 5 分钟学会** |
| **Windows Terminal + `screenrecord` PS 脚本** | 零安装 | 输出格式麻烦 | 想偷懒 |
| **ffmpeg + gdigrab** | 命令行一条搞定 | Windows 配置稍麻烦 | 命令行党 |
| **QuickTime (macOS)** | 自带 | 只 Mac | 不用我讲 |

---

## 5 步流程

### Step 1: 准备终端 (1 分钟)

打开 **Windows Terminal** (推荐) 或 VS Code 内置终端:
- 字体: `Cascadia Code` 或 `Microsoft YaHei UI` (中英文都漂亮)
- 字号: **22pt** (录屏字号, 16pt 太小)
- 配色: 暗色 (黑底白字) — 屏幕录制时文字清晰
- 窗口: 拉到 1280x720 像素
- 关闭: 通知 / 弹窗 / 任务栏自动隐藏

### Step 2: 起 Postgres + 设 LLM Key (Video 1 必需, 2 分钟)

```bash
# Video 1 必需, Video 2/3 不需要
make erp-up                    # 起 Postgres + seed

# 选一个 LLM provider
export MINIMAX_API_KEY=your_key
# 或
export ANTHROPIC_API_KEY=sk-ant-...
```

### Step 3: 跑脚本 + 录屏 (3-4 分钟)

| 视频 | 命令 | 依赖 | 录屏时长 |
|------|------|------|----------|
| **Video 1** (单 Agent) | `python scripts/record_video_01.py` | LLM + Postgres | ~60s |
| **Video 2** (多 Agent) | `python scripts/record_video_02.py` | Postgres (mock LLM) | ~60s |
| **Video 3** (RAG) | `python scripts/record_video_03.py` | 无 | ~60s |

**录屏同时按录**: OBS 点 "Start Recording", 然后回 terminal 跑命令. 等脚本结束 (大约 60s) 点 "Stop Recording".

> **Smoke test 先**! 不录屏先跑一遍 `--no-delay` (3-5 秒) 确认脚本不挂.

### Step 4: 视频转码 (1 分钟)

OBS 默认输出 `.mkv`. 转 `.mp4` (更小, GitHub 友好):

```bash
# 用 ffmpeg
ffmpeg -i docs/videos/01.mkv -c:v libx264 -crf 23 -c:a aac docs/videos/01_single_agent.mp4

# Video 2
ffmpeg -i docs/videos/02.mkv -c:v libx264 -crf 23 -c:a aac docs/videos/02_multi_agent.mp4

# Video 3
ffmpeg -i docs/videos/03.mkv -c:v libx264 -crf 23 -c:a aac docs/videos/03_rag.mp4
```

> **CRF 23** 是 sweet spot: 画质好 + 文件 < 10MB. 调大 (28) 文件更小画质略差, 调小 (18) 反之.

### Step 5: 替换 README 视频占位符 (1 分钟)

`README.md` 现在用了 GitHub-friendly 的 video 链接占位:

```markdown
<!-- 把这一行替换为实际 mp4 链接 -->
[Video 1](docs/videos/01_single_agent.mp4)
[Video 2](docs/videos/02_multi_agent.mp4)
[Video 3](docs/videos/03_rag.mp4)
```

GitHub 渲染 `<video>` 标签需要 HTML:

```html
<video src="docs/videos/01_single_agent.mp4" controls width="640"></video>
```

---

## OBS Studio 5 分钟配置 (推荐)

1. **下载安装**: https://obsproject.com (免费, 80MB)
2. **新建场景**: 底部 "Scenes" → "+" → 命名 "ERP Demo"
3. **添加源**: "Sources" → "+" → "Window Capture" → 选 Windows Terminal 窗口
4. **设置输出**: "Settings" → "Output" → Recording:
   - Recording Format: **mp4**
   - Encoder: **x264** (CPU) 或 **NVENC** (NVIDIA GPU)
   - Rate Control: CRF
   - CRF: **23**
5. **设置视频**: "Settings" → "Video":
   - Base Resolution: 1920x1080
   - Output Resolution: 1280x720
6. **设置快捷键**: "Settings" → "Hotkeys":
   - Start Recording: `Ctrl+F9`
   - Stop Recording: `Ctrl+F10`
7. **开始**: 切到 terminal, 按 `Ctrl+F9` 跑脚本, 跑完按 `Ctrl+F10`

---

## 常见问题

### Q: 视频里出现个人通知怎么办?

**录制前**:
- 关 QQ / 微信 / 邮箱
- 任务栏设 "自动隐藏"
- 手机静音
- 通知勿扰模式

**录制中** (万一弹窗):
- 录 1 段 70s, 编辑时剪掉前 5s + 后 5s, 留 60s 核心
- 推荐工具: DaVinci Resolve (免费) / Clipchamp (Windows 自带)

### Q: 视频里脚本卡住了 / 报错了?

**重录**:
- 修脚本
- 跑一遍 `--no-delay` smoke
- 重录

**省时间技巧**: 一次性录 3 段, 中间不停. 哪段挂了单独重录那 1 段.

### Q: 录出来画质差 / 模糊?

- 提高 OBS 输出分辨率 (1080p)
- 提高终端字号 (22pt → 24pt)
- 跑 `--no-delay` 录快版, 画面"流"得更快
- 后期: ffmpeg 加 `-crf 18` 重新压

### Q: Video 1 卡在 "启动数据库连接池"?

**没起 Postgres**:
```bash
make erp-up
```

**没 LLM key**: Video 1 设计上需要真实 LLM 才能完整 demo. 没 key 时 mock 也能跑, 但 3 个问题变成 3 个空 tool. 推荐用真实 key 录.

### Q: 视频存哪? 文件多大?

- **位置**: `docs/videos/01_single_agent.mp4` / `02_multi_agent.mp4` / `03_rag.mp4`
- **大小**: 60s × 720p × CRF 23 ≈ 5-8 MB
- **总大小**: 3 段共 15-25 MB, GitHub 仓库单文件 < 100MB 即可

### Q: 想录旁白怎么办?

**A 方案 (推荐)**: 录完视频后用剪映 / iMovie 配音, 文件小效果好.
**B 方案 (高级)**: OBS 设音频源 (麦克风), 边录边说. 60s 中文旁白稿在 `docs/videos/0*_script.md`.

---

## 推荐时间表 (90 分钟录完 3 段)

```
0-5 分钟:   装 OBS + 调终端 + 关通知
5-10 分钟:  make erp-up + 设 LLM key
10-15 分钟: smoke test 3 个脚本 (--no-delay)
15-35 分钟: 录 Video 1 (单 Agent) — 需 LLM, 跑慢
35-50 分钟: 录 Video 2 (多 Agent) — 快, scripted
50-65 分钟: 录 Video 3 (RAG) — 最快, 离线
65-75 分钟: 3 段转码 mp4
75-85 分钟: 编辑 (剪头尾, 加旁白) — 可选
85-90 分钟: 替换 README 视频链接, git commit
```

---

## 录完后的发布动作 (5 分钟)

```bash
# 1. 视频文件已就位, 提交
git add docs/videos/*.mp4
git commit -m "Add 3 demo videos (60s each, 720p, ~5-8MB)"
git push origin main

# 2. 在 GitHub 创建 Release:
#    - 选 tag: v1.0.1-erp-copilot
#    - Title: "v1.0.1 — ERP AI Copilot (3 demo videos)"
#    - Body: 贴 3 个视频的 GitHub 链接
#    - Attach: 3 个 mp4 文件
#    - Publish Release

# 3. 顺手在 LinkedIn / 简历 / B 站发 1 段最炫的 (Video 2)
```

---

## FAQ: "我录的视频不如 GitHub 上那些 star 1k+ 项目漂亮"

**真相**: 90% 的 star 1k+ 项目的 README 视频都是上面这种 "终端录屏" 风格. 关键不是画质, 是**内容**:
- 屏幕清楚显示 "运行命令 → 几秒后输出结构化结果" 即可
- 旁白讲清楚 "为什么这个值得看" 即可
- **不需要特效, 不需要背景音乐, 不需要人脸**

录屏的真实成本是**时间**, 不是技术. 60s 视频, 录 5 遍, 选最好的 1 遍, 这是行业标准.
