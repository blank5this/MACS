# GitHub Release 操作指南 (v1.0.1-erp-copilot)

> **目的**: 一步步教你如何把 `E:\MACS` 当前代码发布成 GitHub Release v1.0.1-erp-copilot.
> **预计耗时**: 15 分钟 (含本地验证 5 分钟 + GitHub Web 操作 5 分钟 + 复制粘贴 5 分钟).
> **重要**: 本指南**不会**自动执行任何 `git push`, 所有操作需你手动确认.

---

## 前置条件

发布前确认本地有这些东西:

| 类别 | 必需项 | 怎么验证 |
|------|--------|----------|
| **代码** | `E:\MACS` 工作区干净 | `git status` 无 uncommitted changes |
| **数据库** | PostgreSQL 16 (docker) | `docker ps \| grep postgres` |
| **容器** | Docker Desktop 运行中 | `docker info` 成功 |
| **LLM Key** | 任一 provider 的 API key | `echo $ANTHROPIC_API_KEY` 不为空 (或 MiniMax / OpenAI) |
| **依赖** | Python 3.10+ + requirements | `pip install -r requirements.txt` |
| **Git** | GitHub 推送权限 | `git push --dry-run` 无报错 |

**快速检查**:

```bash
# Postgres
docker run -d --name macs-pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=erp_test \
  postgres:16-alpine

# LLM Key (任选一)
export ANTHROPIC_API_KEY=sk-ant-...
# export MINIMAX_API_KEY=...
# export OPENAI_API_KEY=sk-...

# 依赖
cd E:\MACS
pip install -r requirements.txt
```

---

## 5 步发布流程

### Step 1: 验证本地 (5 分钟)

跑全套本地检查, 确保绿色:

```bash
cd E:\MACS

# 1.1 Lint
make erp-lint
# 期望: "All checks passed!"

# 1.2 跑非集成测试 (152 + 16 = 168)
make erp-test
# 期望: "168 passed"

# 1.3 健康检查 (DB + LLM + RAG 3 维)
make erp-check
# 期望: ok: True

# 1.4 一键聚合 (上面 3 个一起)
make erp-ci
# 期望: 全绿

# 1.5 看 git 状态
git status
# 期望: "nothing to commit, working tree clean"
```

**如果任何一个报错, 修完再继续**. 别把 broken release 发出去.

---

### Step 2: 创建 Git Tag (本地, 1 分钟)

```bash
cd E:\MACS

# 2.1 确认在 main 分支
git checkout main
git pull origin main

# 2.2 创建 annotated tag (带 message)
git tag -a v1.0.1-erp-copilot -m "Release v1.0.1-erp-copilot: 2 bug fixes (LLM agent prompt + RuntimeEngine error propagation), 168 tests passing, 100% backward compatible"

# 2.3 验证 tag 创建成功
git tag -l "v1.0.1-erp-copilot"
# 期望: v1.0.1-erp-copilot

git show v1.0.1-erp-copilot --stat
# 期望: 显示 tag message + commit hash + 文件变更统计
```

---

### Step 3: 推送 Tag 到 GitHub (1 分钟)

```bash
cd E:\MACS

# 3.1 推送 tag (不要加 --tags, 只推这一个)
git push origin v1.0.1-erp-copilot
# 期望: "Total 1 (delta 0), reused 0 (delta 0)"
# 期望: 提示 "* [new tag]      v1.0.1-erp-copilot -> v1.0.1-erp-copilot"

# 3.2 在 GitHub 上验证
# 打开 https://github.com/blank5this/MACS/tags
# 期望: v1.0.1-erp-copilot 出现在列表
```

---

### Step 4: 在 GitHub Web 创建 Release (5 分钟)

1. **打开 Releases 页**: https://github.com/blank5this/MACS/releases/new

2. **选 tag**: 下拉框选 `v1.0.1-erp-copilot` (刚刚 push 的那个)

3. **Release title**: 填
   ```
   🚀 ERP AI Copilot v1.0.1 — Bug Fixes + Improved Stability
   ```

4. **Description**: 把 [`.github/RELEASE_TEMPLATE/v1.0.1.md`](.github/RELEASE_TEMPLATE/v1.0.1.md) 的**全部内容**复制粘贴到 "Describe this release" 文本框.

   ```bash
   # 在 E:\MACS 下快速复制:
   cat .github/RELEASE_TEMPLATE/v1.0.1.md | clip
   # (或手动打开文件 Ctrl+A → Ctrl+C)
   ```

5. **勾选项**:
   - [x] **Set as the latest release** (默认勾选)
   - [ ] **Set as a pre-release** (留空, 这是 stable release)

6. **附件** (可选, 上传本地录好的视频文件):
   - 如果有录好的 60s 视频, 拖到 "Attach binaries" 区域
   - 否则先发空, 等录完视频后用 `gh release upload v1.0.1-erp-copilot video_01.mp4` 后补

7. **点 "Publish release"** 按钮.

---

### Step 5: 验证发布成功 (1 分钟)

1. 访问 https://github.com/blank5this/MACS/releases

2. 期望看到:
   - `v1.0.1-erp-copilot` 在列表最上面
   - 标记为 "Latest"
   - 标题是 `🚀 ERP AI Copilot v1.0.1 — Bug Fixes + Improved Stability`
   - Description 包含 168 passed 表 / Mermaid 架构图 / Demo 视频占位符

3. **跑一遍链接**:
   - `RELEASE_NOTES_v1.0.1.md` 链接能否打开 (文件应该在 main 分支)
   - 视频占位符显示 "待录" 字样 (提醒你录完替换)

---

## 常见问题 (Q&A)

### Q1: tag 已经 push 了, 但是忘记改 CHANGELOG, 怎么办?

**答**: 不要删 tag, 直接改 CHANGELOG 然后:
```bash
# 改 CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs: amend v1.0.1 changelog"
git push origin main
# GitHub Release 不会自动更新, 需手动编辑 release description
```

---

### Q2: 把 `v1.0.1-erp-copilot` 拼错了 tag 名, 怎么办?

**答**: 先删本地 + 远端 tag:
```bash
# 删本地
git tag -d v1.0.1-erp-copilot-wrong

# 删远端
git push origin :refs/tags/v1.0.1-erp-copilot-wrong

# 重新打
git tag -a v1.0.1-erp-copilot -m "..."
git push origin v1.0.1-erp-copilot
```

---

### Q3: PyPI publish 要一起发吗?

**答**: v1.0.1 是 patch release, 体积小 (~18 KB), **建议一起发 PyPI**:

```bash
# 本地构建 + 上传 (需要 pypi account + token)
python -m build
twine upload dist/macs_pkg-1.0.1*
```

或者走 GitHub Actions 自动发布 (`.github/workflows/release.yml` 已经在 main).

---

### Q4: Docker Hub 镜像要发吗?

**答**: v1.0.0 / v1.0.1 共享同一个 Docker image, **不需要单独 tag**. 只需要:
```bash
docker pull blank5this/macs:v1.0.1-erp-copilot
# 或
docker pull blank5this/macs:latest
```

---

### Q5: 发完之后 CI 失败了, 怎么办?

**答**: 立刻 revert release:
1. GitHub Releases 页面 → 点 v1.0.1 → Edit → 取消 "Latest" 勾选 (或直接 Delete release)
2. 修 CI 失败的代码 → 重新打 tag `v1.0.1-erp-copilot-fix1`
3. 走完整流程重发

**预防**: Step 1 的 `make erp-ci` 必须全绿再发.

---

## 发布后动作 (Post-Release Checklist)

发布成功后, **立刻做**这 5 件事 (今天内完成):

- [ ] **更新 README**: 把 `docs/videos/0X_*.md` 的链接换成实际录好的视频链接 (如果录完了)
- [ ] **更新 CHANGELOG**: 顶部加 v1.0.1 的发布日期 URL (e.g. `[v1.0.1-erp-copilot] - 2026-06-12 — [release](https://github.com/blank5this/MACS/releases/tag/v1.0.1-erp-copilot)`)
- [ ] **发 Twitter/X**: 用 `docs/marketing/GITHUB_RELEASE_TWEET.md` 的 3 条短帖, 间隔 2-4 小时发
- [ ] **LinkedIn / 知乎 / 掘金**: 各发 1 篇 1000 字短文, 链接到 release
- [ ] **通知**: 在相关 Discord / Slack / 微信群分享 link

---

## 发布后 7 天内 (营销窗口)

- [ ] **录 3 段 60s 视频** (按 `docs/RECORDING_GUIDE.md`), 上传到 B 站 / YouTube, 然后用 `gh release upload` 补到 release page
- [ ] **更新简历 PDF**: 加 1 行 "ERP AI Copilot v1.0.1 — 168 tests, 3 videos, 15 days"
- [ ] **投深圳南山 AI 岗**: Boss 直聘 / 拉勾 / LinkedIn (目标 10-20 个)
- [ ] **写复盘博客**: "15 天独立完成 ERP AI Copilot, 我学到的 5 件事"
- [ ] **收集 feedback**: 在 GitHub Discussions 发 "What's your ERP use case?" 帖, 看用户怎么用

---

## 紧急回滚 (Rollback)

万一发现 v1.0.1 有 critical bug:

```bash
# 1. 在 GitHub Releases 页面 → Edit release → 取消 "Latest"
# 2. 把 tag 改成 v1.0.1-erp-copilot-bad, 别删 (留作历史)
# 3. 重新打 v1.0.2 tag
git tag -a v1.0.2-erp-copilot -m "Hotfix: ..."
git push origin v1.0.2-erp-copilot

# 4. PyPI yank (如果发过)
pip yank macs-pkg==1.0.1
```

---

## 参考链接

- 📋 [CHANGELOG.md](../CHANGELOG.md) — 完整变更日志
- 📑 [RELEASE_NOTES_v1.0.1.md](../RELEASE_NOTES_v1.0.1.md) — 详细 release notes (本指南的姊妹篇)
- 📝 [`.github/RELEASE_TEMPLATE/v1.0.1.md`](../.github/RELEASE_TEMPLATE/v1.0.1.md) — GitHub Release body 模板
- 🐦 [docs/marketing/GITHUB_RELEASE_TWEET.md](marketing/GITHUB_RELEASE_TWEET.md) — 3 条 Twitter 短帖
- 🏠 [README.md](../README.md) — 项目首页

---

> **下一步**: 打开 [`.github/RELEASE_TEMPLATE/v1.0.1.md`](../.github/RELEASE_TEMPLATE/v1.0.1.md) 复制粘贴到 GitHub Release Description!