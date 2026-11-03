# 小学知识卡系统 — 部署到腾讯云教程

> 本教程面向零基础用户，每一步都有操作演示和原理说明。学完你能独立部署任何 Flask 项目。

---

## 阶段一：本地 Git 仓库初始化

> **为什么要用 Git？** Git 是版本控制工具，能记录代码的每次修改，还能把代码同步到服务器。没有 Git，部署就是手动传文件，容易出错且无法回滚。

### 步骤 1.1：初始化本地仓库

打开 PowerShell，进入项目目录：

```bash
cd c:\Users\addmin\WorkBuddy\automation-20260329161737\poster-generator
git init
```

**执行效果：**
```
Initialized empty Git repository in C:/Users/addmin/WorkBuddy/.../poster-generator/.git/
```

**原理说明：** `git init` 会在项目根目录创建一个 `.git` 文件夹，里面存放所有版本历史。一开始是空的。

---

### 步骤 1.2：添加 .gitignore（已帮你创建）

`.gitignore` 的作用是告诉 Git「这些文件不用管」——比如生成的图片、缓存文件、密码文件。

```bash
# 检查 .gitignore 是否生效（output 目录应该被忽略）
cat .gitignore
```

---

### 步骤 1.3：添加到暂存区并查看状态

```bash
git add -A          # -A = add all，把所有文件加入暂存区
git status          # 查看暂存状态
```

**你会看到类似输出：**

```
A  .gitignore
A  app.py
A  config.py
A  prompts/chinese.txt
...
```

> ⚠️ 如果看到 `output/` 目录也在里面，说明 .gitignore 没有生效，需要重新检查文件。

---

### 步骤 1.4：移除已误添加的文件

如果 output 被添加了，执行：

```bash
git rm -r --cached output/
```

`--cached` 表示只从 Git 索引中移除，不删除实际文件。

---

### 步骤 1.5：首次提交

```bash
git commit -m "feat: 小学知识卡生成系统 v1.0"
```

`-m` 后面是提交说明，格式：`类型: 简短描述`。常见类型：
- `feat` — 新功能
- `fix` — 修复 bug
- `docs` — 文档更新

---

## 阶段二：GitHub 仓库创建与关联

> **为什么要 GitHub？** GitHub 是代码的「云端仓库」，相当于网盘。你把代码 push 上去，服务器从上面 pull 下来，实现代码同步。

### 步骤 2.1：创建 GitHub 仓库

1. 打开 https://github.com 并登录
2. 点击右上角 **+** → **New repository**
3. 填写：
   - **Repository name**：`knowledge-card-generator`
   - **Description**：`小学知识卡海报生成系统`
   - **Private / Public**：Private（私有）
   - ✅ **不要勾选** Add a README（因为本地已有）
4. 点击 **Create repository**

---

### 步骤 2.2：复制仓库地址

创建成功后，GitHub 会显示你的仓库地址，格式类似：

```
https://github.com/你的用户名/knowledge-card-generator.git
```

复制这个地址，后面要用。

---

### 步骤 2.3：本地仓库关联远程

```bash
git remote add origin https://github.com/你的用户名/knowledge-card-generator.git
```

- `origin` 是远程仓库的默认别名，你可以理解为一个快捷方式

---

### 步骤 2.4：首次推送到 GitHub

```bash
git branch -M main              # 确保分支名为 main
git push -u origin main         # -u 设置上游分支，以后直接 git push 即可
```

**执行效果：**
```
Enumerating objects: 12, done.
Counting objects: 100%
To https://github.com/你的用户名/knowledge-card-generator.git
 * [new branch]     main -> main
Branch 'main' set up to track remote 'main' from 'origin'.
```

---

## 阶段三：腾讯云服务器准备

> **服务器是什么？** 服务器就是一台永远开机的电脑，24 小时运行你的网站。你本地电脑关了网站就停了，服务器不会。

### 步骤 3.1：连接服务器

在 PowerShell 中：

```bash
ssh root@你的服务器IP
```

**示例：**
```bash
ssh root@1.2.3.4
```

第一次连接会提示：
```
Are you sure you want to continue connecting (yes/no)?
```
输入 `yes` 回车。

然后输入密码（输入时屏幕不显示字符，正常现象）。

---

### 步骤 3.2：更新系统软件包

```bash
yum update -y          # CentOS/RHEL 系统
# 如果是 Ubuntu 系统，用：
# apt update && apt upgrade -y
```

**原理：** 服务器镜像可能是几个月前的，系统软件有安全漏洞，更新到最新版本。

---

### 步骤 3.3：安装 Python 3

```bash
# 安装 Python（腾讯云 CentOS 默认没有）
yum install -y python3 python3-pip
```

验证安装：
```bash
python3 --version
# 应该显示：Python 3.x.x
```

---

### 步骤 3.4：安装 Git

```bash
yum install -y git
```

---

### 步骤 3.5：安装依赖

```bash
# 安装 Flask 等 Python 库
pip3 install flask requests pillow
```

> 💡 **进阶：** 以后依赖多了，用 `requirements.txt` 管理：
> ```bash
> pip3 install -r requirements.txt
> ```

---

## 阶段四：从 GitHub 拉取代码到服务器

### 步骤 4.1：在服务器创建项目目录

```bash
mkdir -p /www/knowledge-card
cd /www/knowledge-card
```

---

### 步骤 4.2：从 GitHub 拉取代码

```bash
git clone https://github.com/你的用户名/knowledge-card-generator.git .
```

`.` 表示「把代码放到当前目录」，不额外创建子文件夹。

---

### 步骤 4.3：创建配置文件

> ⚠️ **重要安全原则：** GitHub 上永远不会存 Token。Token 只存在于你的本地电脑和服务器上。

```bash
cd /www/knowledge-card
# 从模板复制一份配置
cp config.example.py config.py
# 编辑配置文件，填入你的 DeepSeek Token
nano config.py
```

将 `config.py` 中的 `sk-your-api-key-here` 替换为你的真实 DeepSeek API Key：

```python
DEEPSEEK_API_KEY = "sk-你真实的Token粘贴在这里"
```

**保存退出：** `Ctrl + X` → `Y` → `回车`

---

## 阶段五：启动服务

### 方式一：直接运行（开发测试用）

```bash
cd /www/knowledge-card
python3 app.py
```

如果看到：
```
* Running on http://0.0.0.0:5000
```
说明启动成功，浏览器访问 `http://你的服务器IP:5000` 即可。

---

### 方式二：Gunicorn + Supervisor（生产环境推荐）

> **为什么要用 Gunicorn？** 直接运行 `python3 app.py` 在服务器上是「前台运行」，关掉终端程序就停了。Gunicorn 让 Flask 在后台运行，稳定性高。Supervisor 是一个进程管理工具，开机自启、崩溃自动重启。

**安装 Gunicorn：**
```bash
pip3 install gunicorn
```

**安装 Supervisor：**
```bash
yum install -y supervisor
systemctl enable supervisord
```

**配置 Supervisor：**
```bash
nano /etc/supervisord.d/knowledge-card.ini
```

写入：
```ini
[program:knowledge-card]
directory=/www/knowledge-card
command=gunicorn -w 2 -b 0.0.0.0:5000 app:app
autostart=true
autorestart=true
stderr_logfile=/var/log/knowledge-card.err.log
stdout_logfile=/var/log/knowledge-card.out.log
```

启动：
```bash
supervisorctl reread
supervisorctl update
supervisorctl start knowledge-card
```

查看状态：
```bash
supervisorctl status
```

---

## 阶段六：开放防火墙端口

> ⚠️ **重要：** 腾讯云有「安全组」概念，必须手动开放端口，否则外网无法访问！

### 在腾讯云控制台操作：

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 找到「云服务器 CVM」→「实例」
3. 点击你的服务器 → **安全组** 标签
4. 点击安全组名称 → **入站规则** → **添加规则**

| 方向 | 类型 | 来源 | 端口 | 策略 |
|------|------|------|------|------|
| 入站 | 自定义 | 0.0.0.0/0 | 5000 | 允许 |

5. 保存

---

## 阶段七：域名解析（可选）

如果有域名，可以绑定到服务器 IP，省去记 IP 地址：

1. 在域名服务商（如阿里云、腾讯云）添加 DNS 记录
2. 记录类型：`A`
3. 主机记录：`@`（或 `www`）
4. 记录值：服务器 IP
5. 等待生效（5 分钟 ~ 24 小时）

解析生效后，访问 `http://你的域名:5000` 即可。

---

## 阶段八：代码更新流程

以后修改代码后，更新服务器的流程：

```bash
# 1. 本地修改代码
# 2. Git 提交
git add -A
git commit -m "fix: 修复按钮状态恢复问题"

# 3. 推送到 GitHub
git push origin main

# 4. 服务器上拉取更新
cd /www/knowledge-card
git pull origin main

# 5. 如果用了 Supervisor，重启服务
supervisorctl restart knowledge-card
```

---

## 故障排查

| 问题 | 解决方法 |
|------|---------|
| 页面打不开 | 检查安全组是否开放 5000 端口 |
| 502 Bad Gateway | 检查 Gunicorn 是否在运行：`supervisorctl status` |
| 生成海报失败 | 检查服务器能访问 DeepSeek API：`curl https://api.deepseek.com` |
| 中文字体不显示 | 服务器安装中文字体，或使用 CDN 字体链接 |

---

## 安全原则：永远不要把 Token 提交到 GitHub

```
.gitignore 已配置 config.py 不上传
GitHub 只有 config.example.py（模板，无 Token）
Token 只存在于本地电脑和腾讯云服务器
```

**为什么重要？**
- GitHub 代码是公开的（或对 collaborators 可见）
- 如果 Token 泄露，任何人可以用你的 DeepSeek 额度，直到你吊销它
- 正确做法：`.gitignore` 排除 + `.example.py` 模板参考

**GitHub 的「Secrets」功能（进阶）：**
如果未来要做自动化部署，可以用 GitHub Secrets 功能存储 Token，
服务器通过环境变量读取，完全不需要在代码或磁盘上存放明文密码。

---

有任何步骤卡住了，随时告诉我哪一步出问题！
