# README 视频替换指南

> 录完 3 段 mp4 后, 把 `README.md` 第 27-33 行的"录屏脚本"链接替换成真正的 `<video>` 标签, 让 GitHub 直接内嵌播放.
> 共 3 段视频, 每段一次复制粘贴, 5 分钟搞定.

---

## 第一步: 找哪里

### 找法 A — grep 命令定位

```bash
grep -n "录屏脚本\|\.mp4\|<video" "E:/MACS/README.md"
```

期望输出 (行号可能略有差异):
```
31:| 1 | **单 Agent 混合工具** — 7 工具自动选择 | [录屏脚本](docs/videos/01_single_agent_script.md) | [script](docs/videos/01_single_agent_script.md) |
32:| 2 | **多 Agent 协作** — 4 Agent 接力, 4 段产物 | [录屏脚本](docs/videos/02_multi_agent_script.md) | [script](docs/videos/02_multi_agent_script.md) |
33:| 3 | **RAG 知识库** — 18 篇中文文档混合检索 | [录屏脚本](docs/videos/03_rag_script.md) | [script](docs/videos/03_rag_script.md) |
```

### 找法 B — 手动定位
打开 `E:/MACS/README.md`, 搜字符串 **`3 段 60s 视频`**, 下面的 Markdown 表格就是要改的地方.

### 上下文 (改之前长这样, README.md L27-33)

```markdown
**3 段 60s 视频** (按顺序看效果最佳):

| # | 主题 | 视频 | 旁白稿 |
|---|------|------|--------|
| 1 | **单 Agent 混合工具** — 7 工具自动选择 | [录屏脚本](docs/videos/01_single_agent_script.md) | [script](docs/videos/01_single_agent_script.md) |
| 2 | **多 Agent 协作** — 4 Agent 接力, 4 段产物 | [录屏脚本](docs/videos/02_multi_agent_script.md) | [script](docs/videos/02_multi_agent_script.md) |
| 3 | **RAG 知识库** — 18 篇中文文档混合检索 | [录屏脚本](docs/videos/03_rag_script.md) | [script](docs/videos/03_rag_script.md) |
```

**注意**: 当前"视频"列放的是**录屏脚本链接**, 不是真视频. 这是占位符.

---

## 第二步: 改什么

### 替换方案 — 方案 A (推荐): 用 HTML `<video>` 标签内嵌

GitHub Markdown **不**渲染 `<video>`, 但 HTML 内嵌能. 所以要把这一列从 Markdown 单元格改成纯 HTML.

**Video 1 行** (把 `[录屏脚本](docs/videos/01_single_agent_script.md)` 整段换成):
```html
<video src="docs/videos/01_single_agent.mp4" controls width="640"></video>
```

**Video 2 行**:
```html
<video src="docs/videos/02_multi_agent.mp4" controls width="640"></video>
```

**Video 3 行**:
```html
<video src="docs/videos/03_rag.mp4" controls width="640"></video>
```

### 替换方案 — 方案 B (备选): 用 Markdown 图片语法

如果你的环境不支持 HTML, 可以用 `<img>` 指向视频第一帧 (需 ffmpeg 先抽帧), 复杂度高, **不推荐**.

### 替换方案 — 方案 C (最简): 直接链接到 mp4

适合"想内嵌但不想被 GitHub 自动播放"场景:
```markdown
[▶ 播放 Video 1 (60s)](docs/videos/01_single_agent.mp4)
```

---

## 第三步: 改后长啥样

### 改之后 (README.md L27-34)

```markdown
**3 段 60s 视频** (按顺序看效果最佳):

| # | 主题 | 视频 | 旁白稿 |
|---|------|------|--------|
| 1 | **单 Agent 混合工具** — 7 工具自动选择 | <video src="docs/videos/01_single_agent.mp4" controls width="640"></video> | [script](docs/videos/01_single_agent_script.md) |
| 2 | **多 Agent 协作** — 4 Agent 接力, 4 段产物 | <video src="docs/videos/02_multi_agent.mp4" controls width="640"></video> | [script](docs/videos/02_multi_agent_script.md) |
| 3 | **RAG 知识库** — 18 篇中文文档混合检索 | <video src="docs/videos/03_rag.mp4" controls width="640"></video> | [script](docs/videos/03_rag_script.md) |
```

### 改完之后, 顺手做这 3 件事

#### 1. 在 GitHub 上强制刷新

GitHub 会缓存 README, **改完之后不一定立刻看到**. 解决:
- 浏览器按 `Ctrl+Shift+R` 强刷
- 或在 URL 后加 `?v=2` 绕过缓存

#### 2. 验证 mp4 文件确实在仓库里

```bash
ls -lh "E:/MACS/docs/videos/"*.mp4
# 期望: 看到 01_single_agent.mp4 / 02_multi_agent.mp4 / 03_rag.mp4
# 每个 5-8 MB
```

如果 `git status` 没看到, 说明 `gitignore` 把视频挡了:
```bash
cat "E:/MACS/.gitignore" | grep -i "mp4\|video"
# 如果 *.mp4 被忽略, 改 .gitignore 去掉这一行, 或加 docs/videos/*.mp4 例外
```

#### 3. 本地预览

```bash
# (1) 浏览器打开 file://E:/MACS/README.md
# (2) 找到表格, 看到 3 个视频框 + 播放按钮
# (3) 点播放验证 mp4 能加载
```

### GitHub 渲染常见问题

| 现象 | 原因 | 修复 |
|------|------|------|
| 看不到视频框 | Markdown 单元格不解析 HTML | 确认表格里那列用的是 `<video>` 标签, 不是 `[录屏脚本]` |
| 视频框显示但黑屏 | mp4 没 commit / 路径错 | `git ls-files docs/videos/*.mp4` 验证 |
| 视频卡顿 / 不加载 | mp4 太大 (GitHub 单文件限 100MB) | 重压: `ffmpeg -i in.mp4 -crf 28 out.mp4` |
| 手机不显示 | GitHub 移动端对 `<video>` 支持弱 | 这是 GitHub 已知限制, 无解 |

---

## 一键替换脚本 (PowerShell, 可选)

如果想自动化批量替换 (高级用户):

```powershell
# 在 E:/MACS/ 下
(Get-Content README.md) -replace `
  '\[录屏脚本\]\(docs/videos/01_single_agent_script\.md\)', `
  '<video src="docs/videos/01_single_agent.mp4" controls width="640"></video>' `
  | Set-Content README.md
# 同样处理 02 / 03
```

> 替换前 `git commit` 当前 README, 万一改坏了能 `git checkout README.md` 还原.

---

**生成时间**: 2026-06-12
**前置条件**: `docs/videos/0*_*.mp4` 已存在 (见 `RECORDING_CHECKLIST.md` Stage 4)
**下一步**: `docs/videos/POST_RECORDING_CHECKLIST.md` 发布