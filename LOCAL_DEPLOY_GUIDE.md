# 本地一键部署到阿里云指南

## 服务器信息
- **IP地址**: 120.27.159.14
- **操作系统**: Ubuntu 22.04 64位
- **用户**: root
- **密码**: Yi2013405%

---

## 第一步：配置安全组（重要！）

在开始部署前，**必须先配置安全组规则**，否则无法访问应用。

1. 登录阿里云控制台: https://ecs.console.aliyun.com
2. 点击左侧菜单"网络与安全" → "安全组"
3. 找到你的服务器关联的安全组，点击"配置规则"
4. 点击"入方向" → "快速添加"
5. 添加以下规则：

| 端口范围 | 授权对象 | 描述 |
|---------|---------|------|
| 22/22 | 0.0.0.0/0 | SSH远程登录 |
| 8001/8001 | 0.0.0.0/0 | 应用访问端口 |

6. 点击"确定"保存

---

## 第二步：本地上传代码

在你的**本地Mac终端**执行以下命令：

```bash
# 1. 进入项目目录
cd /Users/pm/Documents/期权交易策略/option_tracker

# 2. 上传代码到服务器（会提示输入密码：Yi2013405%）
scp -r * root@120.27.159.14:/root/option-tracker/
```

**注意**: 输入密码时不会显示任何字符，这是正常的。直接输入完按回车即可。

---

## 第三步：SSH连接到服务器

在**本地Mac终端**执行：

```bash
ssh root@120.27.159.14
```

输入密码：`Yi2013405%`

---

## 第四步：在服务器上安装Docker（复制粘贴执行）

连接到服务器后，**复制以下整段命令**，粘贴到终端执行：

```bash
# 更新系统
sudo apt-get update

# 安装依赖
sudo apt-get install -y ca-certificates curl gnupg

# 添加Docker GPG密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加Docker仓库
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

看到Docker版本号输出说明安装成功！

---

## 第五步：配置环境变量

在服务器终端执行：

```bash
cd /root/option-tracker
nano .env.production
```

修改以下内容（**重点修改UQER_TOKEN**）：

```env
# 数据库配置
DATABASE_URL=sqlite:///./data/option_tracker.db

# 优矿API Token (必填 - 替换成你的真实token)
UQER_TOKEN=你的优矿token

# AI配置 (选填)
GEMINI_API_KEY=
GEMINI_BASE_URL=https://www.apillm.online/v1

# 应用配置
DEBUG=False
LOG_LEVEL=INFO
PORT=8001

# CORS配置
ALLOWED_ORIGINS=*

# 性能配置
WORKERS=2
MAX_CONNECTIONS=100
```

编辑完成后：
- 按 `Ctrl + O` 保存
- 按 `Enter` 确认
- 按 `Ctrl + X` 退出

---

## 第六步：启动应用

在服务器终端执行：

```bash
cd /root/option-tracker
docker compose -f docker-compose.prod.yml up -d --build
```

等待构建完成（首次构建需要5-10分钟）...

---

## 第七步：查看运行状态

```bash
# 查看容器状态
docker ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

看到类似输出说明成功：
```
option-tracker  | INFO:     Uvicorn running on http://0.0.0.0:8001
option-tracker  | INFO:     Application startup complete.
```

按 `Ctrl + C` 退出日志查看

---

## 第八步：访问应用

在浏览器中打开：

```
http://120.27.159.14:8001/frontend.html
```

🎉 **部署成功！**

---

## 常用管理命令

### 查看日志
```bash
docker compose -f docker-compose.prod.yml logs -f
```

### 重启应用
```bash
docker compose -f docker-compose.prod.yml restart
```

### 停止应用
```bash
docker compose -f docker-compose.prod.yml stop
```

### 启动应用
```bash
docker compose -f docker-compose.prod.yml start
```

### 更新代码
```bash
# 本地上传新代码
scp -r * root@120.27.159.14:/root/option-tracker/

# 服务器上重新构建
cd /root/option-tracker
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 遇到问题？

### 问题1: 无法访问8001端口
**解决**: 检查阿里云安全组是否已开放8001端口

### 问题2: 容器启动失败
```bash
# 查看详细错误
docker compose -f docker-compose.prod.yml logs

# 清理后重试
docker system prune -a
docker compose -f docker-compose.prod.yml up -d --build
```

### 问题3: 忘记密码
**解决**: 在阿里云控制台重置root密码

---

**预计总时间**: 30-40分钟
**预计费用**: ¥50-100/月
