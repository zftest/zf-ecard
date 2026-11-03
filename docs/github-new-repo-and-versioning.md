# 新建 GitHub 仓库、上传代码与版本控制操作手册

| 文档项 | 内容 |
|---|---|
| 适用项目 | `D:\dev-soff\knowledge-card-generato-main` |
| 日期 | 2026-11-03 |
| 目标 | 从零建立独立 GitHub 仓库、安全上传代码、管理分支、版本 Tag 与发布 |
| 当前状态 | 本地尚未初始化 Git；`.gitignore` 已存在 |
| 关键安全事实 | `config.py` 含真实 DeepSeek Key，已被 `.gitignore` 排除，**绝不能提交** |

> 本手册提供可直接执行的命令，但本次没有替你执行 `git init`、创建远程仓库或 push。请按步骤核对后自行执行，尤其是首次提交前的密钥检查。

## 0. 推荐路线

```text
检查密钥与忽略规则
  → 本地 git init
  → 首次 commit
  → GitHub 创建空私有仓库
  → SSH 或 Git Credential Manager 鉴权
  → push main
  → 功能分支 / PR
  → Tag 与 GitHub Release
```

**鉴权优先级：SSH > Git Credential Manager（浏览器登录）> 细粒度 PAT。**  
不建议把 Token 直接写进远程 URL，也不要把 Token、`config.py` 或 `.env` 提交到仓库。

## 1. 当前项目提交边界

### 1.1 现有 `.gitignore` 已覆盖

检查当前 `.gitignore` 可确认至少包含：

```text
config.py
.venv/
venv/
__pycache__/
output/
.idea/
*.log
```

这意味着：

- `config.py` 的真实 API Key 不会进入 Git。
- `.venv`、缓存和生成海报不会进入 Git。
- `.idea` 不会进入 Git。

### 1.2 建议再补充的忽略项

如果后续会导入教材 PDF、音频或本地数据库，建议在 `.gitignore` 追加：

```gitignore
# 新增学习模块的本地数据
data/
*.sqlite
*.db

# 第三方教材/导入资料与生成音频，避免误传版权文件和大文件
*.pdf
*.mp3
*.wav

# 前端依赖与构建产物
frontend/node_modules/
frontend/dist/
```

> 不要把教材 PDF、商业词库原始文件、整批音频提交到公开仓库。词库和音频应单独存放并在发布时附来源/许可清单。

### 1.3 提交前必须验证

```bash
cd /d/dev-soff/knowledge-card-generato-main
git check-ignore -v config.py .venv output .idea
```

期望看到每个路径被哪条 `.gitignore` 规则忽略。  
如果 `config.py` 没有出现在忽略结果里，**先停下来修复 `.gitignore`，不要 commit**。

另外确认：

```bash
ls -la
```

不要提交：`config.py`、`.venv/`、`output/`、`__pycache__/`、`.idea/`、真实 PDF、音频包、数据库文件。

## 2. 本地初始化与首次提交

### 2.1 配置 Git 身份

只做一次：

```bash
git --version
git config --global user.name "你的 GitHub 显示名"
git config --global user.email "你的 GitHub 验证邮箱"
git config --global init.defaultBranch main
```

检查：

```bash
git config --global --list
```

如果使用公司/学校代理，先确认 `git config --global --get http.proxy` 是否符合本机网络环境；不确定就不要乱设代理。

### 2.2 初始化仓库

```bash
cd /d/dev-soff/knowledge-card-generato-main
git init
```

如果 Git 版本较老，可能默认分支为 `master`，执行：

```bash
git branch -M main
```

### 2.3 预演暂存内容

```bash
git add -n .
```

`-n` 只预览，不真正加入暂存区。确认输出中没有：

- `config.py`
- `.venv/`
- `output/`
- `.idea/`
- 大体积 PDF/音频/数据库

然后：

```bash
git add .
git status --short
```

### 2.4 检查是否误加敏感文件

```bash
git ls-files | grep -E '(^|/)config\.py$'
```

**期望：没有任何输出。**  
如果输出了 `config.py`：

```bash
git rm --cached config.py
git status --short
```

这只会从 Git 索引移除，不删本地文件。随后必须确认 `.gitignore` 已包含 `config.py`。如果该文件之前已经提交过历史，仅 `git rm --cached` 不够，还需要处理历史并轮换 Key，见第 10 节。

### 2.5 首次提交

```bash
git diff --cached --stat
git commit -m "chore: initial import of knowledge card app and UI prototype"
```

提交后验证：

```bash
git log --oneline -1
git status
```

## 3. 在 GitHub 创建新仓库

### 3.1 网页方式（推荐首次使用）

1. 登录 GitHub。
2. 右上角 **+** → **New repository**。
3. 填写：
   - Repository name：`knowledge-card-generator`
   - Description：`初中知识卡与单词默写学习工具`
   - Visibility：**Private**（先私有，确认无敏感内容后再考虑公开）
4. **不要勾选**：
   - Add a README file
   - Add .gitignore
   - Choose a license
5. 点击 **Create repository**。

因为本地已经有代码和 `.gitignore`，远程仓库应为空仓库，避免首次 push 出现 unrelated histories。

### 3.2 复制远程地址

SSH 推荐：

```text
git@github.com:<你的用户名>/knowledge-card-generator.git
```

HTTPS：

```text
https://github.com/<你的用户名>/knowledge-card-generator.git
```

### 3.3 关联远程并首次推送

SSH：

```bash
git remote add origin git@github.com:<你的用户名>/knowledge-card-generator.git
git remote -v
git push -u origin main
```

HTTPS：

```bash
git remote add origin https://github.com/<你的用户名>/knowledge-card-generator.git
git remote -v
git push -u origin main
```

`-u` 会把本地 `main` 与 `origin/main` 建立上游关系，以后直接 `git push` / `git pull` 即可。

### 3.4 可选：GitHub CLI 一条命令建库并推送

安装 GitHub CLI 后：

```bash
winget install --id GitHub.cli
```

重新打开终端，然后：

```bash
gh auth login
cd /d/dev-soff/knowledge-card-generato-main
gh repo create knowledge-card-generator --private --source=. --remote=origin --push
```

前提：

- 本地已经完成 `git init` 和首次 commit。
- 当前目录是 Git 仓库。
- `gh auth login` 已完成浏览器授权。

## 4. 鉴权方式：SSH、Token 与凭据管理器

### 4.1 推荐：SSH Key

生成 Ed25519 Key：

```bash
ssh-keygen -t ed25519 -C "你的 GitHub 邮箱"
```

一路回车可使用默认路径 `~/.ssh/id_ed25519`。如果已有 Key，不要覆盖，按提示使用新文件名。

启动 ssh-agent：

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

复制公钥：

```bash
cat ~/.ssh/id_ed25519.pub
```

到 GitHub：**Settings → SSH and GPG keys → New SSH key**，粘贴公钥（不是私钥）。

测试：

```bash
ssh -T git@github.com
```

首次会询问是否信任 `github.com`，输入 `yes`。成功会看到类似：

```text
Hi <用户名>! You've successfully authenticated...
```

Windows 如果 `ssh-add` 报 agent 未运行，可在管理员 PowerShell 中检查：

```powershell
Get-Service ssh-agent
Set-Service -Name ssh-agent -StartupType Automatic
Start-Service ssh-agent
```

### 4.2 HTTPS + Git Credential Manager

Git for Windows 通常自带 Credential Manager。首次 `git push` 时会在浏览器/弹窗要求登录 GitHub，成功后凭据由系统安全存储。

可显式设置：

```bash
git config --global credential.helper manager
```

不要使用：

```bash
# 不要这样做：Token 会出现在 shell history 和 remote 配置
git remote add origin https://<TOKEN>@github.com/user/repo.git
```

### 4.3 细粒度 Personal Access Token（PAT）

**何时使用：** HTTPS 命令行、脚本或无法使用浏览器登录的环境。  
**不建议：** 把 Token 长期写在项目文件、README、`.env.example` 或远程 URL 中。

创建步骤：

1. GitHub 右上角头像 → **Settings**。
2. 左侧最下 → **Developer settings**。
3. **Personal access tokens → Fine-grained tokens**。
4. **Generate new token**。
5. 设置：
   - Token name：例如 `knowledge-card-local-push`
   - Expiration：30 或 90 天，不建议永久
   - Resource owner：你的账号
   - Repository access：**Only select repositories** → 选择目标仓库
   - Permissions：
     - **Contents: Read and write**（push/pull 代码）
     - **Metadata: Read-only**（通常自动包含）
6. 生成后只显示一次，立即保存到密码管理器。

使用 HTTPS push 时：

- Username：GitHub 用户名
- Password：粘贴 PAT，而不是 GitHub 登录密码

如果只是推送代码，不需要给 Token 授予组织管理、仓库删除等无关权限。  
如果需要用 API 创建仓库，才涉及仓库管理类权限；更简单的做法是先在网页创建空仓库。

### 4.4 三种方式对比

| 方式 | 安全性 | 易用性 | 适合 |
|---|---|---|---|
| SSH Key | 高 | 一次配置长期使用 | 日常开发，推荐 |
| Git Credential Manager | 高（系统凭据库） | 浏览器登录简单 | Windows 本地开发 |
| Fine-grained PAT | 中（需妥善保管） | 可脚本化 | CI、临时环境、无浏览器环境 |
| 账号密码 | 已不支持 | — | 不要使用 |

## 5. 日常版本控制流程

### 5.1 每次开发前

```bash
git status
git pull --rebase
git switch -c feature/vocabulary-ui
```

从最新 `main` 拉取，再创建功能分支。

### 5.2 开发中查看

```bash
git status
git diff
git diff --stat
```

### 5.3 分批暂存

```bash
git add -p
```

按块选择改动，避免把无关文件、调试代码、真实密钥一起提交。

### 5.4 提交

```bash
git diff --cached
git commit -m "feat(vocabulary): add dictation configuration screen"
```

建议提交类型：

| 前缀 | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复缺陷 |
| `docs` | 文档 |
| `refactor` | 重构，不改变行为 |
| `test` | 测试 |
| `chore` | 构建、依赖、杂项 |

### 5.5 推送功能分支

```bash
git push -u origin feature/vocabulary-ui
```

### 5.6 合并到 main

推荐 Pull Request，不直接在 main 上堆开发提交。

使用 GitHub CLI：

```bash
gh pr create --base main --head feature/vocabulary-ui \
  --title "feat: vocabulary dictation UI" \
  --body "补充词库、默写配置、作答反馈与 UI 原型"
```

或在 GitHub 网页点击 **Compare & pull request**。

合并前至少检查：

- CI/本地测试通过。
- 没有 `config.py`、Token、PDF、音频大文件。
- API 契约与旧知识卡回归通过。
- 变更说明和验收结果清楚。

### 5.7 合并后清理

```bash
git switch main
git pull --rebase
git branch -d feature/vocabulary-ui
git push origin --delete feature/vocabulary-ui
```

删除的是已合并分支；如果分支未合并，`-d` 会拒绝，避免误删。

## 6. 分支策略

单人项目不必上复杂的 Git Flow。建议：

```text
main                 稳定可运行版本
feature/<name>       新功能
fix/<name>           缺陷修复
docs/<name>          文档
prototype/<name>     UI/产品原型探索
```

规则：

- `main` 保持可运行，不直接堆半成品。
- 一个分支只解决一个问题，避免超大 PR。
- 功能分支从最新 `main` 创建。
- 合并后删除远端分支。
- 发布从 `main` 打 Tag。
- 重要实验可以用 `prototype/` 分支，避免污染主线。

## 7. 版本号与 GitHub Release

### 7.1 语义化版本

```text
v主版本.次版本.修订号
v0.1.0
```

| 变化 | 版本示例 |
|---|---|
| 不兼容 API/数据结构变化 | `v1.0.0` → `v2.0.0` |
| 向后兼容的新功能 | `v0.1.0` → `v0.2.0` |
| 向后兼容的修复 | `v0.2.0` → `v0.2.1` |
| 尚未稳定的 MVP | 保持 `0.x.y` |

建议里程碑：

- `v0.0.1`：仓库初始化、现有知识卡不动。
- `v0.1.0`：前后端分离骨架 + UI 原型。
- `v0.2.0`：默写 MVP，含词库、配置、作答、结果、错词。
- `v0.3.0`：PDF 导入校对 + 完整题型。
- `v1.0.0`：数据结构与 API 稳定，可长期使用。

### 7.2 打 Tag

轻量 Tag 只用于临时标记；发布用附注 Tag：

```bash
git switch main
git pull --rebase
git tag -a v0.1.0 -m "feat: hybrid architecture and interactive prototype"
git push origin v0.1.0
```

查看：

```bash
git tag --list
git show v0.1.0
```

一次性推送所有 Tag：

```bash
git push origin --tags
```

**注意：** 普通 `git push` 不会自动推送 Tag。

### 7.3 创建 GitHub Release

1. 打开仓库 → **Releases → Draft a new release**。
2. 选择刚推送的 Tag，例如 `v0.1.0`。
3. 填写标题与变更说明。
4. 上传必要附件（不要上传教材 PDF、商业词库或密钥）。
5. 发布。

### 7.4 查看与切换历史版本

```bash
git log --oneline --decorate --graph
git show v0.1.0
git switch --detach v0.1.0
```

查看完回主线：

```bash
git switch main
```

## 8. 差异化比较与回滚

### 8.1 常用 diff

| 目的 | 命令 |
|---|---|
| 工作区 vs 暂存区 | `git diff` |
| 暂存区 vs 上次提交 | `git diff --cached` |
| 两提交之间 | `git diff <old_commit> <new_commit>` |
| 两分支之间 | `git diff main feature/vocabulary-ui` |
| 两版本之间 | `git diff v0.1.0 v0.2.0` |
| 只看文件摘要 | `git diff --stat v0.1.0 v0.2.0` |
| 某次提交详情 | `git show <commit>` |
| 某文件历史 | `git log -p -- path/to/file` |
| 谁改了某一行 | `git blame path/to/file` |

### 8.2 回滚原则

优先使用 `revert`，保留历史：

```bash
git revert <commit_id>
git push
```

临时查看旧版本：

```bash
git switch --detach v0.1.0
```

需要从旧版本修复：

```bash
git switch -c hotfix/from-v0.1.0 v0.1.0
```

**避免**未经确认执行：

```bash
# 高风险：会丢弃本地未提交改动
git reset --hard <commit>
# 高风险：会改写远端历史
git push --force
```

如果确实需要强制推送，必须先备份、确认没有协作者，并优先使用 `--force-with-lease`。

## 9. 大文件与版权文件

- GitHub 单文件通常限制 100MB，仓库长期超过建议体积会影响 clone。
- 不要把 `node_modules`、`.venv`、生成音频整包、教材 PDF 提交。
- 不要用 Git LFS 绕过版权与授权问题；LFS 只解决体积，不解决许可。
- 3000 词音频若需要版本化，建议对象存储 + manifest；Git 只保存 manifest 与生成脚本。
- 测试需要 PDF 时，使用自制或明确许可的小样本，放在 `tests/fixtures/` 并标明来源。

## 10. 如果密钥已经误提交

按顺序处理：

1. **立即到 DeepSeek 控制台吊销并轮换真实 Key。** 这是第一步，不能只删文件。
2. 从当前索引移除：

   ```bash
   git rm --cached config.py
   ```

3. 确认 `.gitignore` 已包含 `config.py`，提交修复。
4. 如果历史提交已经包含密钥，清理历史需要重写：

   ```bash
   # 先备份仓库；团队协作需先通知所有协作者
   git filter-repo --path config.py --invert-paths
   ```

   或在确认备份后使用 BFG Repo-Cleaner。不要在不了解影响时直接执行。
5. 强制推送清理后的历史：

   ```bash
   git push --force-with-lease
   ```

6. GitHub 开启 **Secret scanning / Push protection**。
7. 检查 GitHub Actions、Issue、Release 附件、日志中是否也泄露。

**本项目当前尚未 init Git，最好的策略是首次提交前验证 `config.py` 未进索引，避免进入历史。**

## 11. 常见错误与处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `src refspec main does not match any` | 还没有 commit，或本地分支叫 master | 先 commit；或 `git branch -M main` 后再 push |
| `remote origin already exists` | 已添加过远程 | `git remote -v` 查看；用 `git remote set-url origin <新地址>` |
| `Authentication failed` | 用了账号密码、PAT 过期/权限不足 | 改用 SSH 或 Git Credential Manager；重新生成 PAT |
| `403 Permission denied` | PAT 没有 Contents 写权限或未选仓库 | 检查 Token 资源与仓库权限 |
| `Updates were rejected` / non-fast-forward | 远程有本地没有的提交 | `git pull --rebase` 后解决冲突再 push；不要直接 force |
| `fatal: not a git repository` | 目录不对或未 init | `cd` 到项目根目录检查 `.git` |
| `config.py` 出现在提交列表 | `.gitignore` 未生效或已被跟踪 | `git rm --cached config.py`；检查规则；轮换密钥 |
| 文件名大小写问题 | Windows 不区分大小写 | `git mv` 显式重命名，不要只改大小写 |
| `LF will be replaced by CRLF` | Windows 换行符提示 | 通常可忽略；团队可统一 `.gitattributes` |
| `src refspec vX does not match any` | Tag 未创建 | 先 `git tag -a ...`，再 push |
| 仓库过大/推送失败 | 提交了虚拟环境、音频、PDF、构建产物 | 从索引移除并加入 `.gitignore`；历史清理需备份确认 |

## 12. 仓库设置建议

- **Visibility：** 先 Private；确认无版权、密钥、个人信息后再公开。
- **Branch protection：** 保护 `main`，至少禁止直接 force push；个人项目可要求 PR 自审。
- **Secret scanning：** 开启。
- **Dependabot：** Python/npm 依赖开启安全更新。
- **License：** 代码可考虑 MIT；但词库、教材 PDF、音频数据必须单独标注许可，不能用一个 MIT 覆盖全部内容。
- **README：** 写清启动方式、目录结构、环境变量、旧功能不变、新功能计划。
- **Issues：** 可作为需求/缺陷追踪，标签建议 `feat`、`bug`、`docs`、`content`、`security`。

## 13. 一次完整上线清单

- [ ] `git --version` 正常。
- [ ] `config.py` 有真实 Key，且已确认被忽略。
- [ ] `.venv`、`output`、`.idea` 未进入暂存区。
- [ ] 没有 PDF/音频/数据库大文件。
- [ ] `git add -n .` 输出符合预期。
- [ ] 首次 commit 完成。
- [ ] GitHub 空私有仓库已创建。
- [ ] SSH 测试成功，或 Credential Manager/PAT 可用。
- [ ] `git push -u origin main` 成功。
- [ ] GitHub 页面确认 `config.py` 不存在。
- [ ] 日常使用 feature 分支 + PR。
- [ ] 发布使用附注 Tag 与 GitHub Release。
- [ ] 版本号与变更说明可追溯。
- [ ] 任何密钥泄露时先轮换，再清历史。

## 14. 最常用命令速查

```bash
# 查看
git status
git diff
git diff --stat
git log --oneline --decorate --graph

# 暂存与提交
git add -p
git diff --cached
git commit -m "feat: ..."

# 分支
git switch -c feature/name
git switch main
git branch -a
git push -u origin feature/name

# 同步
git pull --rebase
git push

# 版本
git tag -a v0.2.0 -m "release: vocabulary MVP"
git push origin v0.2.0
git show v0.2.0

# 比较
git diff main feature/name
git diff v0.1.0 v0.2.0
```

## 15. 参考

1. GitHub 细粒度 Personal Access Token 管理  
   https://docs.github.com/zh/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
2. GitHub SSH 连接  
   https://docs.github.com/zh/authentication/connecting-to-github-with-ssh
3. GitHub CLI `gh repo create`  
   https://cli.github.com/manual/gh_repo_create
4. Git Credential Manager  
   https://github.com/git-ecosystem/git-credential-manager
5. Git 官方文档  
   https://git-scm.com/doc

> 执行前请备份重要数据，尤其是涉及历史重写、强制推送或大批量文件操作时。版本管理的第一步不是 push，而是确保不该上传的东西没有进入暂存区。
